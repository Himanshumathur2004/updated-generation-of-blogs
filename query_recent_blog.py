from pymongo import MongoClient
import os
from workflow_common import bootstrap_env

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm_blog_platform")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]
blogs = db.blogs

# Find most recent blog
recent = blogs.find_one(sort=[("created_at", -1)])

if recent:
    print("=" * 80)
    print("📝 MOST RECENT BLOG")
    print("=" * 80)
    print(f"\n📌 Title: {recent.get('title')}")
    print(f"   Length: {len(recent.get('title', ''))} chars")
    print(f"\n📄 Body ({len(recent.get('body', ''))} chars):")
    print(f"{recent.get('body', '')[:2000]}")
    print(f"\n...⏸️ [Truncated to 2000 chars]")
    print(f"\n📅 Created: {recent.get('created_at')}")
    print(f"📊 Topic: {recent.get('topic')}")
    print(f"🏢 Account: {recent.get('account_id')}")
else:
    print("No blogs found")
