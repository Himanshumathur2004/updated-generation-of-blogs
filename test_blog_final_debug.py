import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "blog_platform"))

from blog_platform.blog_generator import BlogGenerator
from blog_platform.config import Config
from workflow_common import bootstrap_env
import logging
import time

bootstrap_env(__file__)

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s - %(message)s')
logger = logging.getLogger(__name__)

print("\n" + "=" * 90)
print("🧪 BLOGGENERATE DEBUG TEST - COMPREHENSIVE ANALYSIS")
print("=" * 90)

print("\n📋 Configuration:")
print(f"   API Key: {Config.MEGALLM_API_KEY[:30]}...")
print(f"   Base URL: {Config.MEGALLM_BASE_URL}")
print(f"   Model: {Config.MODEL}")

# Create generator
generator = BlogGenerator(
    api_key=Config.MEGALLM_API_KEY,
    base_url=Config.MEGALLM_BASE_URL,
    model=Config.MODEL
)

print("\n🚀 Calling generate_blog() with debugging...")
print("   (Watch the detailed logs below)\n")

start = time.time()

blog_data = generator.generate_blog(
    topic="AI Cost Optimization",
    topic_description="How to reduce LLM costs through smart model routing and optimization",
    keywords=["cost", "optimization", "AI", "models"]
)

elapsed = time.time() - start

print("\n" + "=" * 90)
print("📊 RESULT")
print("=" * 90)
print(f"\nElapsed time: {elapsed:.1f} seconds")
print(f"Returned value: {blog_data}")

if blog_data:
    print(f"\n✅ SUCCESS!")
    print(f"   Title: {blog_data['title']}")
    print(f"   Body length: {len(blog_data['body'])} characters")
else:
    print(f"\n❌ FAILED - Returned None")
    print("\n🔍 Analysis:")
    print("   The function returned None, which means an error occurred.")
    print("   Check the DEBUG logs above for details on what went wrong.")
    print("\n   Common causes:")
    print("   1. API is overloaded (HTTP 503)")
    print("   2. API timeout (30s limit)")
    print("   3. Malformed JSON response")
    print("   4. Authentication error")
