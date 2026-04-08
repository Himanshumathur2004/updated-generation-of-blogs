import requests
import json
import os
from workflow_common import bootstrap_env

bootstrap_env(__file__)

api_key = os.getenv('MEGALLM_API_KEY')
url = 'https://beta.megallm.io/v1/chat/completions'

if not api_key:
    raise ValueError('MEGALLM_API_KEY is not set')

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

payload = {
    'model': 'claude-opus-4-6',
    'messages': [
        {'role': 'user', 'content': 'Say hello in one word'}
    ],
    'max_tokens': 10
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        print('✓ API Key is WORKING')
        content = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No content')
        print(f'Response: {content}')
    else:
        print('✗ API Key ERROR')
        print(response.text[:300])
except Exception as e:
    print(f'✗ Connection Error: {e}')
