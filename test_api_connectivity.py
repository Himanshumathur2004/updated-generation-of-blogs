import requests
import json
from workflow_common import bootstrap_env
import os

bootstrap_env(__file__)

api_key = os.getenv("MEGALLM_API_KEY")
base_url = os.getenv("MEGALLM_BASE_URL", "https://beta.megallm.io/v1")
model = os.getenv("MODEL", "claude-opus-4-6")

print("=" * 80)
print("🧪 TESTING MEGALLM API CONNECTIVITY")
print("=" * 80)
print(f"\n📋 Configuration:")
print(f"   Base URL: {base_url}")
print(f"   Model: {model}")
print(f"   API Key (first 20 chars): {api_key[:20]}...")

url = f"{base_url}/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "Write a short 2-sentence paragraph about AI."
        }
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

print(f"\n📤 Sending API request...")
print(f"   URL: {url}")
print(f"   Timeout: 15 seconds")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    
    print(f"\n✅ GOT RESPONSE!")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response Headers:")
    for key, value in response.headers.items():
        print(f"      {key}: {value[:100] if len(str(value)) > 100 else value}")
    
    print(f"\n📄 Response Body:")
    try:
        data = response.json()
        print(json.dumps(data, indent=2)[:1000])
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "")
            print(f"\n🎯 Generated Content:")
            print(f"   {content}")
    except:
        print(f"   {response.text[:1000]}")
        
except requests.exceptions.Timeout:
    print(f"\n❌ TIMEOUT! Request exceeded 15 seconds")
    print(f"   The API is not responding within reasonable time")
    
except requests.exceptions.ConnectionError as e:
    print(f"\n❌ CONNECTION ERROR!")
    print(f"   {str(e)}")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"   {str(e)}")
