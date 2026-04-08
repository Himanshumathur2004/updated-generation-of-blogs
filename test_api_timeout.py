import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "blog_platform"))

from blog_platform.blog_generator import BlogGenerator
from blog_platform.config import Config
from workflow_common import bootstrap_env
import logging
import time
import requests

bootstrap_env(__file__)

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 80)
print("🧪 TESTING API RESPONSE TIME")
print("=" * 80)

# Test the API response time with a simple request
api_key = Config.MEGALLM_API_KEY
base_url = Config.MEGALLM_BASE_URL
model = Config.MODEL

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

test_payload = {
    "model": model,
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant. Respond with exactly 100 words about AI."
        }
    ],
    "temperature": 0.8,
    "max_tokens": 150
}

print(f"\nTesting with 60-second timeout...")
print(f"URL: {base_url}/chat/completions")
print(f"Model: {model}\n")

start = time.time()

try:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=test_payload,
        timeout=60  # 60 second timeout
    )
    
    elapsed = time.time() - start
    
    print(f"✅ Request completed in {elapsed:.1f} seconds")
    print(f"Status Code: {response.status_code}")
    print(f"Response size: {len(response.text)} characters")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📝 Response received:")
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0].get('message', {}).get('content', 'N/A')
            print(f"   Content: {content[:500]}...")
    else:
        print(f"❌ Error response: {response.text[:500]}")
        
except requests.exceptions.Timeout as e:
    elapsed = time.time() - start
    print(f"⏱️ TIMEOUT after {elapsed:.1f}s: {e}")
    
except Exception as e:
    elapsed = time.time() - start
    print(f"❌ ERROR after {elapsed:.1f}s: {type(e).__name__}")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
