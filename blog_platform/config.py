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
    
    # OpenRouter API Configuration (Primary)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable must be set in .env file.")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus-preview:free")
    
    # Backward compatibility - map OPENROUTER to MEGALLM names
    MEGALLM_API_KEY = OPENROUTER_API_KEY
    MEGALLM_BASE_URL = OPENROUTER_BASE_URL
    MEGALLM_MODEL = OPENROUTER_MODEL
    
    # Blog Generation Config
    BLOG_WORD_COUNT_MIN = 500
    BLOG_WORD_COUNT_MAX = 800
    BLOG_TEMPERATURE = 0.65
    BLOG_MAX_TOKENS = 2000
    
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
            "name": "Performance & Speed",
            "description": "How MegaLLM improves latency and throughput with intelligent routing, parallel processing, and performance optimization",
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
        {"id": "account_5", "name": "TokensAndTakes", "description": "Specialized topics"},
    ]
