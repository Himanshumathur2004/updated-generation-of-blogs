#!/usr/bin/env python3
"""Test MegaLLM API for variant generation."""

import os
import sys
import json
import time
import requests
from workflow_common import bootstrap_env

bootstrap_env(__file__)

api_key = os.getenv("MEGALLM_API_KEY")
base_url = os.getenv("MEGALLM_BASE_URL", "https://beta.megallm.io/v1").rstrip('/')
model = os.getenv("MEGALLM_MODEL", "gpt-4-turbo")

print(f"\n🔧 MegaLLM API Test for Variant Generation")
print(f"=" * 60)
print(f"Base URL: {base_url}")
print(f"Model: {model}")
print(f"API Key: {'✓ Set' if api_key else '✗ MISSING'}")

if not api_key:
    print("\n❌ ERROR: MEGALLM_API_KEY not set in .env")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Test 1: Simple connectivity test
print(f"\n📡 Test 1: Simple API Connectivity")
print("-" * 60)

simple_payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Say hello in one word."}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

try:
    print(f"Sending request to {base_url}/chat/completions...")
    start = time.time()
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=simple_payload,
        timeout=30
    )
    elapsed = time.time() - start
    
    print(f"✓ Response received in {elapsed:.1f}s")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response Size: {len(response.text)} bytes")
    
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(f"  Content: {content}")
        print(f"✓ Simple test PASSED")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        
except requests.exceptions.Timeout:
    print(f"✗ TIMEOUT after 30 seconds")
except requests.exceptions.ConnectionError as e:
    print(f"✗ Connection error: {e}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")

# Test 2: Variant generation test (smaller version)
print(f"\n🎨 Test 2: Variant Generation (Smaller Prompt)")
print("-" * 60)

variant_payload = {
    "model": model,
    "messages": [
        {
            "role": "system",
            "content": "You are a content strategist. Create 2 unique variants (NOT 5!) of a blog post about AI."
        },
        {
            "role": "user",
            "content": """Create 2 variants of this brief blog:
TITLE: How AI is Changing Everything

CONTENT: AI is transforming industries. Businesses are adopting AI for efficiency. MegaLLM helps orchestrate multiple models.

CREATE 2 VARIANTS:
1. First: Focus on cost optimization with MegaLLM
2. Second: Focus on performance with MegaLLM

Return ONLY valid JSON array:
[
  {"title": "Variant 1 title", "body": "..."},
  {"title": "Variant 2 title", "body": "..."}
]"""
        }
    ],
    "temperature": 0.8,
    "max_tokens": 1500
}

try:
    print(f"Sending variant request (2 variants, ~1500 tokens max)...")
    start = time.time()
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=variant_payload,
        timeout=60
    )
    elapsed = time.time() - start
    
    print(f"✓ Response received in {elapsed:.1f}s")
    print(f"  Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(f"  Response snippet: {content[:150]}...")
        
        # Try to parse as JSON
        cleaned = content.replace("```json", "").replace("```", "").strip()
        start_idx = cleaned.find('[')
        end_idx = cleaned.rfind(']')
        
        if start_idx != -1 and end_idx != -1:
            json_str = cleaned[start_idx:end_idx+1]
            variants = json.loads(json_str)
            print(f"✓ Parsed {len(variants)} variants successfully")
            for i, v in enumerate(variants):
                print(f"  - Variant {i+1}: {v.get('title', 'N/A')[:40]}...")
        else:
            print(f"  Response is not valid JSON array")
            print(f"  Raw response: {content[:300]}")
            
        print(f"✓ Variant test PASSED")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  Response: {response.text[:300]}")
        
except requests.exceptions.Timeout:
    print(f"✗ TIMEOUT after 60 seconds - API is too slow for variant generation")
except requests.exceptions.ConnectionError as e:
    print(f"✗ Connection error: {e}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")

print(f"\n" + "=" * 60)
print(f"Test complete. Check results above.")
