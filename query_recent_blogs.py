from pymongo import MongoClient
import os
from workflow_common import bootstrap_env

bootstrap_env(__file__)

mongodb_uri = os.getenv("MONGODB_URI")
mongodb_db = os.getenv("MONGODB_DB", "megallm_blog_platform")

client = MongoClient(mongodb_uri)
db = client[mongodb_db]
blogs = db.blogs

# Find 5 most recent blogs
recent_blogs = list(blogs.find().sort("created_at", -1).limit(5))

print("=" * 80)
print("📊 ANALYSIS OF 5 MOST RECENT BLOGS")
print("=" * 80)

for i, blog in enumerate(recent_blogs, 1):
    title = blog.get('title', 'N/A')
    body = blog.get('body', '')
    created = blog.get('created_at', 'N/A')
    topic = blog.get('topic', 'N/A')
    account = blog.get('account_id', 'N/A')
    
    print(f"\n[{i}] Created: {str(created)[:19]}")
    print(f"    Title: {title[:70]}")
    print(f"    Body Length: {len(body)} chars")
    print(f"    Topic: {topic}, Account: {account}")
    print(f"    Content preview: {body[:150]}...")
    
print("\n" + "=" * 80)
print("STATISTICS:")
body_lengths = [len(b.get('body', '')) for b in recent_blogs]
print(f"Average body length: {sum(body_lengths) / len(body_lengths):.0f} chars")
print(f"Min body length: {min(body_lengths)} chars")
print(f"Max body length: {max(body_lengths)} chars")
