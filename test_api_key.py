import requests
import json
import os
from workflow_common import bootstrap_env

bootstrap_env(__file__)

api_key = os.getenv("MEGALLM_API_KEY")
base_url = "https://beta.megallm.io/v1"
model = "claude-opus-4-6"

if not api_key:
    raise ValueError("MEGALLM_API_KEY is not set")

url = f"{base_url}/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Say hello in 2 words"}
    ],
    "temperature": 0.7,
    "max_tokens": 50
}

print(f"Testing API key...")
print(f"Endpoint: {url}")
print(f"Model: {model}\n")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        print(f"\n✅ API KEY WORKING!")
        print(f"Response: {message}")
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text[:300]}")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
