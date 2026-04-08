import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "blog_platform"))

from blog_platform.blog_generator import BlogGenerator
from blog_platform.config import Config
from pymongo import MongoClient
import os
from workflow_common import bootstrap_env

bootstrap_env(__file__)

# Create blog generator
generator = BlogGenerator(
    api_key=Config.MEGALLM_API_KEY,
    base_url=Config.MEGALLM_BASE_URL,
    model=Config.MODEL
)

# Try to generate 1 blog
print("🚀 Attempting to generate a blog with MegaLLM API...")
print(f"API Key (first 30 chars): {Config.MEGALLM_API_KEY[:30]}...")
print(f"Base URL: {Config.MEGALLM_BASE_URL}")
print(f"Model: {Config.MODEL}\n")

blog_data = generator.generate_blog(
    topic="Cost Optimization",
    topic_description="How MegaLLM reduces LLM inference costs through intelligent model routing and token optimization",
    keywords=["cost", "optimization", "routing"]
)

if blog_data:
    print("✅ Blog generated successfully!")
    print(f"\n📝 Title ({len(blog_data['title'])} chars):")
    print(f"   {blog_data['title']}\n")
    print(f"📄 Body ({len(blog_data['body'])} chars):")
    print(f"   {blog_data['body'][:1500]}...")
else:
    print("❌ Blog generation failed - returned None")
