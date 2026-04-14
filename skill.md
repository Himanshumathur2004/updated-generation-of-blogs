# MegaLLM Blog Generation Platform

## Project Overview

A Flask-based multi-platform blog generation system that automatically creates SEO-optimized content for Blogger, Medium, Dev.to, Tumblr, and Quora. The platform uses LLM APIs with a robust multi-model fallback system for resilience.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS)                        │
│                    templates/index.html + analytics.html         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Backend (app.py)                       │
│  - REST API endpoints for blog CRUD operations                   │
│  - Generation endpoints per account                              │
│  - Analytics endpoints                                           │
└─────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐  ┌────────────────┐  ┌────────────────────┐
│   blog_generator  │  │    Database    │  │  scrape_to_mongo   │
│                   │  │  (MongoDB/     │  │                    │
│  Multi-model API  │  │   In-Memory)   │  │  RSS Feed Scanner  │
│  with fallbacks   │  │                │  │                    │
└───────────────────┘  └────────────────┘  └────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API Fallback Chain                             │
│  MegaLLM (glm-4.7) → gemma-4-26b → claude-opus-4-6              │
│       → gpt-4o → Chutes AI (deepseek-ai/DeepSeek-V3.1-TEE)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Configuration (`blog_platform/config.py`)

**Environment Variables Required:**
```env
# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DB=megallm_blog_platform

# Primary API (MegaLLM)
MEGALLM_API_KEY=sk-mega-...
MEGALLM_BASE_URL=https://beta.megallm.io/v1
MODEL=glm-4.7

# Fallback Models
MEGALLM_FALLBACK_MODEL_1=google-gemma-4-26b
MEGALLM_FALLBACK_MODEL_2=claude-opus-4-6
MEGALLM_FALLBACK_MODEL_3=gpt-4o

# Secondary Fallback (Chutes AI)
CHUTES_API_TOKEN=cpk_...
CHUTES_BASE_URL=https://llm.chutes.ai/v1
CHUTES_MODEL=deepseek-ai/DeepSeek-V3.1-TEE
```

**Topics Configuration:**
- `cost_optimization` - Cost reduction through intelligent routing
- `performance` - Latency and throughput optimization
- `reliability` - Failover and uptime strategies
- `infrastructure` - Compliance and data residency

### 2. Database Layer (`blog_platform/database.py`)

**Two Modes:**
1. **MongoDB** (production) - Full persistence with Atlas support
2. **In-Memory** (fallback) - When MongoDB unavailable, data lost on restart

**Collections:**
- `accounts` - Publishing account metadata
- `blogs` - Generated blog content
- `generation_history` - Audit trail of generations
- `articles` - Scraped RSS content (for article-based generation)

### 3. Blog Generator (`blog_platform/blog_generator.py`)

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `generate_blog()` | Generate from topic |
| `generate_blog_from_article()` | Generate from scraped article |
| `generate_blog_variants()` | Create multiple versions for different accounts |
| `package_*_post()` | Format for specific platforms |

**Fallback System:**
```python
# Fallback order
FALLBACK_PROVIDERS = [
    {"name": "megallm", "models": ["glm-4.7", "gemma-4-26b", "claude-opus-4-6", "gpt-4o"]},
    {"name": "chutes", "models": ["deepseek-ai/DeepSeek-V3.1-TEE"]}
]

# Automatic fallback triggers:
# - HTTP errors (401, 402, 404, 429, 500, 502, 503, 504)
# - Connection timeouts
# - Invalid response structure (missing choices/content)
```

### 4. Article Scraping (`scrape_to_mongo.py`)

**RSS Feeds Monitored:**
- TechCrunch (AI, Startups)
- Medium (AI Agents, LLMs)
- Hacker News Best
- Quora (AI, ML, OpenAI topics)
- Dev.to (ai, llm, machinelearning tags)

---

## Account System

| Account ID | Platform | Description |
|------------|----------|-------------|
| account_1 | Blogger | SEO-optimized tech content |
| account_3 | AGIorBust | Backup content |
| account_4 | Quora | Q&A format answers |
| account_5 | Medium | Long-form articles |
| account_6 | Dev.to | Developer-first content |
| account_7 | Tumblr | Casual, witty AI takes |

---

## API Endpoints

### Blog Operations
```
GET    /api/blogs?account_id=<id>&status=<draft|posted>
GET    /api/blogs/<blog_id>
POST   /api/blogs/generate          # Generate new blogs
POST   /api/blogs/generate-from-articles
DELETE /api/blogs/<blog_id>
PUT    /api/blogs/<blog_id>/mark-posted
GET    /api/blogs/<blog_id>/copy    # Get sanitized copy content
```

### Account Operations
```
GET /api/accounts
GET /api/accounts/<account_id>
GET /api/dashboard/<account_id>
GET /api/generation-history/<account_id>
```

### Analytics
```
GET /analytics                    # Analytics dashboard
GET /api/analytics/global
GET /api/analytics/trends?days=30
GET /api/analytics/accounts?days=7
GET /api/analytics/recent?limit=20
```

### Bulk Operations
```
POST /api/bulk-generate          # One-click multi-account generation
```

---

## Platform-Specific Formatting

### Blogger (`package_blogger_post`)
- HTML format with proper paragraph tags
- SEO-optimized meta description
- Backlink to MegaLLM
- Author attribution

### Medium (`package_medium_post`)
- Markdown format
- Author handle and Twitter mention
- Hero image support
- Publication slug integration

### Dev.to (`package_devto_post`)
- Developer-focused markdown
- Canonical URL support
- Code block formatting
- Tag extraction

### Tumblr (`package_tumblr_post`)
- Casual, witty tone
- Short-form content (200-300 words)
- HTML with minimal formatting
- Blog name integration

### Quora (`package_quora_post`)
- Q&A format with structured answer
- Question-asker attribution
- App deep linking metadata
- Site-specific Open Graph tags

---

## Content Quality Controls

### Title Sanitization
- Removes clickbait words ("killing", "shocking", "secret")
- Bans parenthetical marketing "(And How MegaLLM...)"
- Enforces professional tone

### Body Requirements
- Minimum 400 words, target 450-650
- Must contain "megallm" at least once
- Simple, concise language for non-expert readers
- Point-wise key takeaways section

### Anti-Pattern Filters
- No corporate jargon ("leverage", "utilize", "paradigm")
- No formal conclusions ("In summary", "To conclude")
- Limited em-dashes (max 1-2 per piece)
- No standalone single-sentence paragraphs

---

## Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file
cp .env.example .env

# Run Flask app
python blog_platform/app.py
# or
python wsgi.py
```

### Production (Render)
- Uses `wsgi.py` entry point
- MongoDB Atlas for persistence
- Environment variables set in Render dashboard
- Gunicorn WSGI server

---

## Error Handling

### Fallback Triggers
1. **HTTP Errors** - Auto-switch to next model
2. **Timeouts** - Retry with exponential backoff, then fallback
3. **Invalid Response** - Validate structure, fallback if malformed
4. **Rate Limits** - Switch to alternative provider

### Graceful Degradation
- MongoDB unavailable → In-memory database
- All API failures → Return original draft without humanization
- Scraping failures → Fall back to topic-based generation

---

## File Structure

```
├── .env                          # Secrets (not committed)
├── .gitignore
├── requirements.txt
├── wsgi.py                       # WSGI entry point
├── app.py                        # Root app (legacy)
├── scrape_to_mongo.py            # RSS feed scraper
├── skill.md                      # This file
│
├── blog_platform/
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   ├── database.py               # MongoDB/In-memory DB
│   ├── blog_generator.py         # Core generation logic
│   ├── app.py                    # Flask backend
│   ├── insight_scheduler.py      # Scheduled generation
│   └── templates/
│       ├── index.html            # Main dashboard
│       └── analytics.html        # Analytics dashboard
│
└── (test files)
    ├── test_api.py
    ├── test_models.py
    └── ... (various test scripts)
```

---

## Recent Changes

### Multi-Model Fallback System (v2)
- Added unified `_make_api_call_with_fallback()` method
- Response structure validation before returning
- Automatic provider/model switching on failure
- All API calls now use fallback mechanism

### Supported Models
| Provider | Model | Notes |
|----------|-------|-------|
| MegaLLM | glm-4.7 | Primary |
| MegaLLM | google-gemma-4-26b | Fallback 1 |
| MegaLLM | claude-opus-4-6 | Fallback 2 |
| MegaLLM | gpt-4o | Fallback 3 |
| Chutes AI | deepseek-ai/DeepSeek-V3.1-TEE | Secondary provider |

---

## Troubleshooting

### Common Issues

**1. "All fallback providers exhausted"**
- All APIs failed or timed out
- Check API keys in .env
- Verify network connectivity
- Check API status pages

**2. "No content in message"**
- Model returned unexpected format
- Fallback should auto-trigger
- Check model compatibility

**3. MongoDB connection fails**
- Auto-falls back to in-memory
- Check MONGODB_URI format
- Verify Atlas IP whitelist

**4. 429 Rate Limit from Chutes AI**
- Infrastructure at capacity
- Wait and retry
- Primary MegaLLM should handle load

---

## Development Commands

```bash
# Test API connectivity
python test_api.py

# Test specific models
python test_models.py

# Run Flask dev server
python blog_platform/app.py

# Run production WSGI
gunicorn wsgi:app
```

---

## Contact & Maintenance

- **Repository**: https://github.com/Himanshumathur2004/updated-generation-of-blogs
- **Primary Stack**: Python, Flask, MongoDB, LLM APIs
- **Deployment**: Render.com
