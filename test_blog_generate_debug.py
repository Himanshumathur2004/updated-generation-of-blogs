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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 80)
print("🧪 TESTING BLOGGENERATE FUNCTION")
print("=" * 80)
print(f"\nConfig:")
print(f"   API Key (first 20 chars): {Config.MEGALLM_API_KEY[:20]}...")
print(f"   Base URL: {Config.MEGALLM_BASE_URL}")
print(f"   Model: {Config.MODEL}\n")

# Create generator
generator = BlogGenerator(
    api_key=Config.MEGALLM_API_KEY,
    base_url=Config.MEGALLM_BASE_URL,
    model=Config.MODEL
)

print("🚀 Calling generate_blog()...")
start = time.time()

try:
    blog_data = generator.generate_blog(
        topic="AI Cost Optimization",
        topic_description="How to reduce LLM costs through smart model routing and optimization",
        keywords=["cost", "optimization", "AI", "models"]
    )
    
    elapsed = time.time() - start
    print(f"\n✅ SUCCESS! Took {elapsed:.1f} seconds")
    
    if blog_data:
        print(f"\n📝 Generated Blog:")
        print(f"   Title ({len(blog_data['title'])} chars): {blog_data['title']}")
        print(f"   Body ({len(blog_data['body'])} chars):")
        print(f"   {blog_data['body'][:800]}...")
    else:
        print(f"\n❌ Returned None despite no error being raised")
        
except TimeoutError as e:
    print(f"\n⏱️ TIMEOUT ERROR after {time.time() - start:.1f}s: {e}")
    
except Exception as e:
    print(f"\n❌ ERROR after {time.time() - start:.1f}s: {type(e).__name__}")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
