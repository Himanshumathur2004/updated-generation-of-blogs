"""Configuration for Blog Generation Platform."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Base configuration."""
    
    # MongoDB - Use MONGODB_URI from .env (Atlas)
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        print("\n❌ CRITICAL: MONGODB_URI not set in environment!")
        print("   On Render: Set MONGODB_URI in environment variables")
        print("   Locally: Set in .env file")
        raise ValueError("MONGODB_URI environment variable must be set")
    MONGODB_DB = os.getenv("MONGODB_DB", "megallm_blog_platform")
    
    # MegaLLM API Configuration (Primary)
    MEGALLM_API_KEY = os.getenv("MEGALLM_API_KEY")
    MEGALLM_BASE_URL = os.getenv("MEGALLM_BASE_URL", "https://beta.megallm.io/v1")
    MEGALLM_MODEL_CONTENT = os.getenv("MEGALLM_MODEL_CONTENT", "claude-opus-4-6")
    MEGALLM_MODEL_FAST = os.getenv("MEGALLM_MODEL_FAST", "claude-opus-4-6")
    MEGALLM_MODEL_ANALYSIS = os.getenv("MEGALLM_MODEL_ANALYSIS", "claude-opus-4-6")
    MODEL = os.getenv("MODEL", "claude-opus-4-6")
    MEGALLM_BACKLINK_URL = os.getenv("MEGALLM_BACKLINK_URL", "https://beta.megallm.io")

    # Dev.to account configuration (only this account generates dev.to-ready posts)
    DEVTO_ACCOUNT_ID = os.getenv("DEVTO_ACCOUNT_ID", "account_6")
    DEVTO_AUTHOR_NAME = os.getenv("DEVTO_AUTHOR_NAME", "MegaLLM Editorial Team")
    DEVTO_AUTHOR_USERNAME = os.getenv("DEVTO_AUTHOR_USERNAME", "megallm")
    DEVTO_CANONICAL_BASE_URL = os.getenv("DEVTO_CANONICAL_BASE_URL", "https://dev.to/megallm")

    # Medium account configuration (only this account generates Medium-ready posts)
    MEDIUM_ACCOUNT_ID = os.getenv("MEDIUM_ACCOUNT_ID", "account_5")
    MEDIUM_PUBLICATION_SLUG = os.getenv("MEDIUM_PUBLICATION_SLUG", "")
    MEDIUM_AUTHOR_NAME = os.getenv("MEDIUM_AUTHOR_NAME", "MegaLLM Editorial Team")
    MEDIUM_AUTHOR_HANDLE = os.getenv("MEDIUM_AUTHOR_HANDLE", "megallm")
    MEDIUM_AUTHOR_TWITTER = os.getenv("MEDIUM_AUTHOR_TWITTER", "@megallm")
    MEDIUM_HERO_IMAGE_URL = os.getenv(
        "MEDIUM_HERO_IMAGE_URL",
        "https://miro.medium.com/v2/resize:fit:1200/1*m-R_BkNf1Qjr1YbyOIJY2w.png",
    )

    # Quora account configuration (only this account generates Quora-ready posts)
    QUORA_ACCOUNT_ID = os.getenv("QUORA_ACCOUNT_ID", "account_4")
    QUORA_SITE_NAME = os.getenv("QUORA_SITE_NAME", "Quora")
    QUORA_TWITTER_HANDLE = os.getenv("QUORA_TWITTER_HANDLE", "@Quora")
    QUORA_FB_APP_ID = os.getenv("QUORA_FB_APP_ID", "111614425571516")
    QUORA_BASE_URL = os.getenv("QUORA_BASE_URL", "https://www.quora.com")
    QUORA_IOS_APP_STORE_ID = os.getenv("QUORA_IOS_APP_STORE_ID", "456034437")
    QUORA_IOS_APP_NAME = os.getenv("QUORA_IOS_APP_NAME", "Quora")
    QUORA_ANDROID_PACKAGE = os.getenv("QUORA_ANDROID_PACKAGE", "com.quora.android")
    QUORA_ANDROID_APP_NAME = os.getenv("QUORA_ANDROID_APP_NAME", "Quora")
    QUORA_APP_DEEP_LINK_PATH = os.getenv("QUORA_APP_DEEP_LINK_PATH", "")
    QUORA_AUTHOR_NAME = os.getenv("QUORA_AUTHOR_NAME", "MegaLLM Editorial Team")
    QUORA_AUTHOR_HANDLE = os.getenv("QUORA_AUTHOR_HANDLE", "megallm")
    QUORA_AUTHOR_SLUG = os.getenv("QUORA_AUTHOR_SLUG", "MegaLLM-Editorial-Team")
    QUORA_AUTHOR_PROFILE_URL = os.getenv(
        "QUORA_AUTHOR_PROFILE_URL",
        "https://www.quora.com/profile/MegaLLM-Editorial-Team",
    )
    QUORA_QUESTION_ASKER_NAME = os.getenv("QUORA_QUESTION_ASKER_NAME", "Anonymous")
    QUORA_IMAGE_URL = os.getenv(
        "QUORA_IMAGE_URL",
        "https://qph.cf2.quoracdn.net/main-qimg-example.jpeg",
    )
    

    # Blog Generation Config
    BLOG_WORD_COUNT_MIN = 1000
    BLOG_WORD_COUNT_MAX = 1400
    BLOG_TEMPERATURE = 0.65
    BLOG_MAX_TOKENS = 3200
    
    # Schedule Config
    BLOGS_PER_24_HOURS = 12  # 3 per topic × 4 topics
    GENERATION_INTERVAL_MINUTES = 120  # Generate 12 blogs every 24 hours means 1 every 2 hours
    
    # Topics (4 CTO-focused topics for MegaLLM)
    TOPICS = {
        "cost_optimization": {
            "name": "Cost Optimization",
            "description": "How MegaLLM reduces LLM inference costs through intelligent model routing, token optimization, and smart caching strategies",
            "keywords": ["cost", "pricing", "budget", "optimization", "tokens per dollar", "model routing", "fallback strategies"],
            "megallm_focus": "Model selection and cost reduction",
            "blogs_per_cycle": 3
        },
        "performance": {
            "name": "AI Speed and Latency",
            "description": "How MegaLLM improves response speed through smarter model routing, batching, and token optimization — without increasing infrastructure cost",
            "keywords": ["latency", "speed", "throughput", "performance", "tokens per second", "response time", "optimization"],
            "megallm_focus": "Speed and efficiency improvements",
            "blogs_per_cycle": 3
        },
        "reliability": {
            "name": "Reliability & Uptime",
            "description": "How MegaLLM ensures production stability through automatic failover, load balancing, and multi-model redundancy",
            "keywords": ["reliability", "uptime", "failover", "SLA", "monitoring", "availability", "fault tolerance"],
            "megallm_focus": "System stability and failover handling",
            "blogs_per_cycle": 3
        },
        "infrastructure": {
            "name": "Infrastructure & Compliance",
            "description": "How MegaLLM helps manage data residency, compliance requirements, and secure regional deployment for enterprise LLM applications",
            "keywords": ["compliance", "GDPR", "data residency", "infrastructure", "security", "privacy", "regional deployment"],
            "megallm_focus": "Compliance and secure deployment",
            "blogs_per_cycle": 3
        }
    }
    
    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Accounts (predefined)
    ACCOUNTS = [
        {"id": "account_1", "name": "ShipAIFast", "description": "Main content account"},
        {"id": "account_2", "name": "InferenceDaily", "description": "Secondary publication"},
        {"id": "account_3", "name": "AGIorBust", "description": "Backup content"},
        {"id": "account_4", "name": "TokenAIz", "description": "Regional focus"},
        {
            "id": "account_5",
            "name": "TokensAndTakes",
            "description": "Medium-only publishing account",
            "medium_only": True,
        },
        {
            "id": "account_6",
            "name": "DevPulseAI",
            "description": "Dev.to publishing account — developer-first content",
            "devto_only": True,
        },
    ]
