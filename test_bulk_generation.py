#!/usr/bin/env python3
"""Test the bulk generation endpoint - one click to generate for all 5 accounts."""

import requests
import time

endpoint = "http://localhost:5000/api/bulk-generate"

print("="*80)
print("BULK GENERATION TEST - One Click Workflow")
print("="*80)
print(f"\n🚀 Calling: POST {endpoint}")
print("\nThis will:")
print("  1. Fetch recent articles from RSS feeds")
print("  2. Generate insights from those articles")
print("  3. Create 5 unique variants per insight (one for each account)")
print("  4. Save all variants to the database")
print("\nProcessing...\n")

try:
    start_time = time.time()
    response = requests.post(endpoint, timeout=1800)  # 30 minute timeout
    elapsed = time.time() - start_time
    
    result = response.json()
    
    print(f"\n✅ SUCCESS (completed in {elapsed:.1f} seconds)")
    print(f"\nResults:")
    print(f"  Status: {result.get('status')}")
    print(f"  Articles scraped: {result.get('articles_scraped', 0)}")
    print(f"  Blog insights generated: {result.get('blog_insights_generated', 0)}")
    print(f"  Total variants created: {result.get('total_variants_created', 0)}")
    
    print(f"\n📊 Variants per account:")
    variants_dict = result.get('variants_per_account', {})
    for account_id, count in variants_dict.items():
        print(f"     {account_id}: {count} blogs")
    
    print(f"\n💬 Message: {result.get('message')}")
    
except requests.exceptions.Timeout:
    print("❌ Request timeout - generation is taking longer than expected")
    print("   The process may still be running in the background")
except requests.exceptions.ConnectionError:
    print("❌ Could not connect to Flask server at http://localhost:5000")
    print("   Make sure Flask is running: python blog_platform/app.py")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
