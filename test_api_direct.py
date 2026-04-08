import requests
import json
from blog_platform.config import Config

url = "https://beta.megallm.io/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {Config.MEGALLM_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": Config.MODEL,
    "messages": [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Say hello in 2 words"}
    ],
    "temperature": 0.7,
    "max_tokens": 50
}

print(f"Testing API at {url}")
print(f"Model: {Config.MODEL}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nSending request...")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    if response.status_code == 200:
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        print(f"\n✅ API Working!")
        print(f"Generated: {message}")
    else:
        print(f"\n❌ API Error: {response.status_code}")
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
