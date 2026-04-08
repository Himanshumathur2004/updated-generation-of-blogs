import sys
sys.path.insert(0, r'c:\Users\himan\Desktop\blog_generation_pipeline')

import logging
from blog_platform.config import Config
from blog_platform.blog_generator import BlogGenerator

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

generator = BlogGenerator(
    Config.MEGALLM_API_KEY,
    Config.MEGALLM_BASE_URL,
    Config.MODEL,
    max_retries=3
)

print("Generating blog with retry logic enabled...")
result = generator.generate_blog(
    topic="Cost Optimization in AI",
    topic_description="Guide to reducing costs in AI deployments",
    keywords=["cost", "optimization", "AI", "budget"]
)

if result:
    print(f"\n✅ SUCCESS!")
    print(f"Title: {result['title']}")
    print(f"Body length: {len(result['body'])} characters")
    print(f"Body preview: {result['body'][:300]}...")
else:
    print("\n❌ FAILED - No blog generated")
