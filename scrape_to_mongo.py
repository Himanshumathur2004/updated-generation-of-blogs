#!/usr/bin/env python3
"""Scrape RSS feeds and insert new articles into MongoDB for WF1."""

from __future__ import annotations

import uuid
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests
from pymongo import MongoClient
from workflow_common import bootstrap_env


FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://techcrunch.com/category/startups/feed/",
    "https://medium.com/feed/tag/ai-agent",
    "https://medium.com/feed/tag/large-language-models",
    "https://hnrss.org/best",
]


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    if not html:
        return ""
    
    # Remove script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text[:5000]  # Limit to 5000 chars


def _fetch_full_content(url: str, timeout: int = 10) -> str:
    """Fetch full article content from URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        
        # Extract text content from HTML
        text = _extract_text_from_html(response.text)
        return text if text else ""
        
    except Exception as e:
        print(f"[WARN] Could not fetch full content from {url}: {e}")
        return ""


def _text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    val = node.text.strip()
    return val if val else None


def _first(node: ET.Element, tags: list[str]) -> str | None:
    for tag in tags:
        found = node.find(tag)
        value = _text(found)
        if value:
            return value
    return None


def _categories(item: ET.Element) -> list[str]:
    values = []
    for c in item.findall("category"):
        txt = _text(c)
        if txt:
            values.append(txt)
    return values


def _iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _source_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "techcrunch" in host:
        return "techcrunch"
    if "medium" in host:
        return "medium"
    if "hnrss" in host:
        return "hn"
    return host or "rss"


def parse_feed(url: str, fetch_full_content: bool = False) -> list[dict]:
    """Parse RSS feed and optionally fetch full article content.
    
    Args:
        url: RSS feed URL
        fetch_full_content: If True, fetch full HTML content from each article link
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall(".//item")

    now = datetime.now(timezone.utc).isoformat()
    source = _source_from_url(url)
    docs: list[dict] = []

    for item in items:
        title = _first(item, ["title"])
        link = _first(item, ["link"])
        guid = _first(item, ["guid"]) or link
        pub_date = _first(item, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])
        creator = _first(item, ["creator", "{http://purl.org/dc/elements/1.1/}creator"])
        description = _first(item, ["description", "content:encoded", "{http://purl.org/rss/1.0/modules/content/}encoded"])

        if not link and not guid:
            continue

        # Fetch full content if requested
        full_content = description or ""
        if fetch_full_content and link:
            print(f"  Fetching full content from: {link[:60]}...")
            time.sleep(1)  # Rate limiting - be respectful
            fetched = _fetch_full_content(link)
            if fetched and len(fetched) > len(full_content):
                full_content = fetched

        docs.append(
            {
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "creator": creator,
                "content": full_content,  # Use full content if fetched, otherwise RSS description
                "contentSnippet": description,  # Keep original RSS snippet
                "guid": guid,
                "categories": _categories(item),
                "isoDate": _iso_date(pub_date),
                "source": source,
                "createdAt": now,
                "status": "pending",
                "fetchedFrom": url,
                "fetchedFullContent": fetch_full_content and (len(full_content) > len(description or ""))  # Track if we enhanced content
            }
        )

    return docs


def scrape_new_articles(limit: int = 0, fetch_full_content: bool = False) -> dict:
    """Scrape feeds and insert only unseen articles; tag inserts with a scrape run id.
    
    Args:
        limit: Maximum number of articles to insert (0 = no limit)
        fetch_full_content: If True, fetch full HTML content from each article link
    """
    bootstrap_env(__file__)
    
    # Use environment variables for MongoDB connection
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db = os.getenv("MONGODB_DB", "megallm")
    
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    articles = db.articles
    scrape_run_id = str(uuid.uuid4())

    inserted = 0
    skipped = 0
    all_docs = []

    # Collect all docs from all feeds
    for feed in FEEDS:
        try:
            print(f"Scraping feed: {feed[:60]}...")
            docs = parse_feed(feed, fetch_full_content=fetch_full_content)
            all_docs.extend(docs)
        except Exception as exc:
            print(f"[WARN] feed failed: {feed} -> {exc}")
            continue

    # Sort all docs by isoDate descending (most recent first)
    all_docs.sort(key=lambda d: d.get("isoDate") or "", reverse=True)

    for doc in all_docs:
        # Stop if limit reached
        if limit > 0 and inserted >= limit:
            break
            
        dedup_key = doc.get("guid") or doc.get("link")
        if not dedup_key:
            skipped += 1
            continue

        exists = articles.find_one({"$or": [{"guid": dedup_key}, {"link": doc.get("link")}]}, {"_id": 1})
        if exists:
            skipped += 1
            continue

        doc["scrape_run_id"] = scrape_run_id
        articles.insert_one(doc)
        inserted += 1

    return {"inserted": inserted, "skipped": skipped, "scrape_run_id": scrape_run_id}


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape articles from RSS feeds into MongoDB")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of articles to scrape (0 = no limit, default: 0)"
    )
    parser.add_argument(
        "--fetch-full-content",
        action="store_true",
        help="Fetch full HTML content from each article (slower but more detailed)"
    )
    args = parser.parse_args()
    
    summary = scrape_new_articles(limit=args.limit, fetch_full_content=args.fetch_full_content)
    mode = "with full content" if args.fetch_full_content else "RSS snippets only"
    print(f"Scrape Summary ({mode}): Inserted={summary['inserted']}, Skipped={summary['skipped']}, RunID={summary['scrape_run_id']}")


if __name__ == "__main__":
    main()
