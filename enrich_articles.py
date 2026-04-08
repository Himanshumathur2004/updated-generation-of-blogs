#!/usr/bin/env python3
"""Enrich existing articles with full HTML content fetched from their URLs."""

import os
import re
import time
import requests
from pymongo import MongoClient
from workflow_common import bootstrap_env
from datetime import datetime, timezone


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
        print(f"  [ERROR] Could not fetch: {e}")
        return ""


def enrich_articles(limit: int = 50, min_content_length: int = 200) -> dict:
    """Enrich articles with full content from their URLs.
    
    Args:
        limit: Maximum number of articles to enrich
        min_content_length: Only update if fetched content is longer than this
    """
    bootstrap_env(__file__)
    
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db = os.getenv("MONGODB_DB", "megallm")
    
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    articles = db.articles
    
    # Find articles with short content or no content
    query = {
        "$or": [
            {"content": {"$exists": False}},
            {"content": ""},
            {"content": {"$regex": "^.{0,200}$"}}  # Less than 200 chars
        ]
    }
    
    candidates = list(articles.find(query).limit(limit))
    print(f"Found {len(candidates)} articles with insufficient content")
    
    enriched = 0
    failed = 0
    skipped = 0
    
    for i, article in enumerate(candidates, 1):
        url = article.get("link")
        if not url:
            skipped += 1
            continue
        
        article_id = article.get("_id")
        title = article.get("title", "Unknown")[:50]
        current_length = len(article.get("content") or "")
        
        print(f"[{i}/{len(candidates)}] Fetching: {title}...")
        time.sleep(1)  # Rate limiting
        
        full_content = _fetch_full_content(url)
        
        if full_content and len(full_content) > min_content_length and len(full_content) > current_length:
            # Update article with full content
            articles.update_one(
                {"_id": article_id},
                {
                    "$set": {
                        "content": full_content,
                        "enrichedAt": datetime.now(timezone.utc).isoformat(),
                        "contentLength": len(full_content)
                    }
                }
            )
            enriched += 1
            print(f"  ✓ Enriched: {len(full_content)} chars")
        else:
            failed += 1
            print(f"  ✗ Failed or too short: {len(full_content)} chars")
    
    return {
        "enriched": enriched,
        "failed": failed,
        "skipped": skipped,
        "total_processed": len(candidates)
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich articles with full content from URLs")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of articles to enrich (default: 50)"
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=200,
        help="Minimum content length required (default: 200)"
    )
    args = parser.parse_args()
    
    print(f"🔄 Starting article enrichment...")
    print(f"   Limit: {args.limit} articles")
    print(f"   Min content length: {args.min_length} chars\n")
    
    result = enrich_articles(limit=args.limit, min_content_length=args.min_length)
    
    print(f"\n📊 Enrichment Summary:")
    print(f"   ✓ Enriched: {result['enriched']}")
    print(f"   ✗ Failed: {result['failed']}")
    print(f"   ⊘ Skipped: {result['skipped']}")
    print(f"   Total processed: {result['total_processed']}")


if __name__ == "__main__":
    main()
