#!/usr/bin/env python3
"""
Quick Start Guide for Blog Generation Pipeline
Run this to test basic functionality
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from workflow_common import bootstrap_env
bootstrap_env(__file__)

def check_requirements():
    """Check if all requirements are met."""
    print("\n" + "="*60)
    print("BLOG GENERATION PIPELINE - QUICK START CHECK")
    print("="*60)
    
    # Check .env exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found")
        print("   → Copy .env.example to .env and fill in your credentials")
        return False
    
    print("✓ .env file found")
    
    # Check MongoDB URI
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not set in .env")
        print("   → Set MONGODB_URI=mongodb://localhost:27017 or your Atlas URI")
        return False
    
    print(f"✓ MongoDB URI configured")
    
    # Check OpenRouter API Key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set in .env")
        print("   → Get free key from https://openrouter.ai")
        return False
    
    print(f"✓ OpenRouter API Key configured")
    
    # Try to import dependencies
    try:
        import flask
        import pymongo
        import requests
        print("✓ All Python dependencies installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   → Run: pip install -r requirements.txt")
        return False
    
    return True


def test_mongodb():
    """Test MongoDB connection."""
    print("\n" + "="*60)
    print("TESTING MONGODB CONNECTION")
    print("="*60)
    
    try:
        from pymongo import MongoClient
        uri = os.getenv("MONGODB_URI")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✓ MongoDB connected successfully")
        
        db_name = os.getenv("MONGODB_DB", "megallm_blog_platform")
        db = client[db_name]
        print(f"✓ Database '{db_name}' accessible")
        
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("   → Ensure MongoDB is running or check your Atlas connection string")
        return False


def test_api_key():
    """Test OpenRouter API key."""
    print("\n" + "="*60)
    print("TESTING OPENROUTER API KEY")
    print("="*60)
    
    try:
        import requests
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen/qwen3.6-plus-preview:free",
                "messages": [{"role": "user", "content": "Say 'OK'"}],
                "max_tokens": 10
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print("✓ OpenRouter API key is valid")
            return True
        else:
            print(f"❌ API returned status {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        print("   → Check your API key at https://openrouter.ai")
        return False


def print_next_steps():
    """Print next steps."""
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("\n1. Start the Flask server:")
    print("   python blog_platform/app.py")
    print("\n2. Open in browser:")
    print("   http://localhost:5000")
    print("\n3. Or scrape articles and generate blogs:")
    print("   python scrape_to_mongo.py")
    print("   (This requires MongoDB to be set up)")
    print("\n4. Read the full README.md for detailed documentation")
    print("")


if __name__ == "__main__":
    success = True
    
    # Run all checks
    success &= check_requirements()
    success &= test_mongodb()
    success &= test_api_key()
    
    if success:
        print("\n" + "="*60)
        print("✓ ALL CHECKS PASSED - READY TO USE!")
        print("="*60)
        print_next_steps()
    else:
        print("\n" + "="*60)
        print("❌ SOME CHECKS FAILED - SEE MESSAGES ABOVE")
        print("="*60)
        sys.exit(1)
