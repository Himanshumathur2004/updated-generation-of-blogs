#!/usr/bin/env python3
"""Verify that bulk generated blogs have unique titles per account."""

from pymongo import MongoClient
from workflow_common import bootstrap_env
import os

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

print("="*80)
print("VERIFYING BULK GENERATED BLOGS")
print("="*80)

# Get the recently generated blogs (by bulk_generated source type)
blogs = db.blogs
bulk_blogs = list(blogs.find({"source_type": "bulk_generated"}).sort("_id", -1).limit(20))

print(f"\nTotal bulk-generated blogs found: {len(bulk_blogs)}\n")

# Group by account
by_account = {}
for blog in bulk_blogs:
    account_id = blog.get("account_id")
    if account_id not in by_account:
        by_account[account_id] = []
    by_account[account_id].append({
        "title": blog.get("title"),
        "variant_of": blog.get("variant_of"),
        "created_at": blog.get("created_at")
    })

# Display results
for account_id in sorted(by_account.keys()):
    blogs_for_account = by_account[account_id]
    print(f"📝 {account_id}: {len(blogs_for_account)} blogs")
    for i, blog in enumerate(blogs_for_account, 1):
        print(f"   {i}. Title: {blog['title'][:70]}")
        print(f"      Variant of: {blog['variant_of'][:60]}")
    print()

# Check for title uniqueness
print("="*80)
print("UNIQUENESS CHECK")
print("="*80)

all_titles = [blog.get("title") for blog in bulk_blogs]
unique_titles = set(all_titles)

print(f"\nTotal blogs: {len(all_titles)}")
print(f"Unique titles: {len(unique_titles)}")

if len(all_titles) == len(unique_titles):
    print("✅ Perfect! All titles are UNIQUE - no repetition")
else:
    print(f"⚠️  Warning: {len(all_titles) - len(unique_titles)} duplicate titles found")
    
    # Show duplicates
    from collections import Counter
    title_counts = Counter(all_titles)
    for title, count in title_counts.items():
        if count > 1:
            print(f"   - '{title[:50]}...': appears {count} times")

# Show variant grouping
print(f"\n{'='*80}")
print("VARIANT GROUPING")
print("="*80)

by_source = {}
for blog in bulk_blogs:
    source = blog.get("variant_of", "Unknown")
    if source not in by_source:
        by_source[source] = []
    by_source[source].append(blog.get("title"))

for source, titles in sorted(by_source.items()):
    print(f"\n🎨 Variants of: {source[:60]}")
    print(f"   Total variants: {len(titles)}")
    unique_variant_titles = len(set(titles))
    print(f"   Unique titles: {unique_variant_titles}")
    
    for i, title in enumerate(titles, 1):
        accounts = blogs.find_one({"title": title}, {"account_id": 1})
        acc_id = accounts.get("account_id") if accounts else "?"
        print(f"      {i}. [{acc_id}] {title[:60]}")
