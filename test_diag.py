import sys
sys.path.insert(0, r'c:\Users\himan\Desktop\blog_generation_pipeline')

import logging
from blog_platform.config import Config
from blog_platform.blog_generator import BlogGenerator
import time

# Set up logging to see retry behavior
logging.basicConfig(level=logging.INFO, format='%(levelname)-8s - %(message)s')

print("\n" + "="*80)
print("BlogGenerator Retry Logic Test")
print("="*80)

generator = BlogGenerator(
    Config.MEGALLM_API_KEY,
    Config.MEGALLM_BASE_URL,
    Config.MODEL,
    max_retries=3
)

print("\n📝 Starting blog generation with retry logic...")
print("   Topic: Cost Optimization in AI")
print("   Description: Guide to reducing costs in AI deployments")
print("   Max Retries: 3")
print("   Keywords: ['cost', 'optimization', 'AI', 'budget']")

start_time = time.time()

try:
    result = generator.generate_blog(
        topic="Cost Optimization in AI",
        topic_description="Guide to reducing costs in AI deployments",
        keywords=["cost", "optimization", "AI", "budget"]
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n⏱️  Elapsed time: {elapsed:.1f}s")
    
    if result:
        print(f"\n✅ SUCCESS - Blog generated!")
        print(f"   Title: {result['title']}")
        print(f"   Body length: {len(result['body'])} characters")
        print(f"   Preview: {result['body'][:200]}...")
    else:
        print(f"\n❌ FAILED - No result returned (None)")
        
except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n❌ Exception occurred (after {elapsed:.1f}s):")
    print(f"   {type(e).__name__}: {e}")
    
print("\n" + "="*80)
