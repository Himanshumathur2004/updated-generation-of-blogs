# Blog Generation Pipeline

A complete, streamlined blog generation platform that combines **web scraping → content analysis → blog generation** into one focused folder.

## 🎯 What This Platform Does

1. **Scrapes** articles from RSS feeds (TechCrunch, Medium, HackerNews)
2. **Analyzes** content (with optional WF1 integration)
3. **Generates** SEO-optimized blog posts for 5 accounts
4. **Serves** a modern web dashboard for managing generated content

**All files needed are in this single folder** — nothing required from the parent directory.

---

## 📁 Folder Structure

```
blog_generation_pipeline/
├── blog_platform/              # Flask web app
│   ├── app.py                  # REST API server
│   ├── config.py               # Configuration settings
│   ├── database.py             # MongoDB models (with fallback)
│   ├── blog_generator.py       # MegaLLM blog generation
│   ├── insight_scheduler.py    # Insight-driven generation (stub)
│   └── templates/
│       └── index.html          # Web dashboard
├── scrape_to_mongo.py          # RSS feed scraper
├── wf1.py                      # Content analysis (simplified)
├── workflow_common.py          # Shared utilities
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in:
# - MONGODB_URI (local or MongoDB Atlas)
# - MEGALLM_API_KEY (get from https://beta.megallm.io)
```

### 3. Run the Server
```bash
python blog_platform/app.py
```

Open **http://localhost:5000** in your browser

---

## 🔧 Configuration

Edit `.env` with your settings:

```env
# MongoDB Connection (Required)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=megallm_blog_platform

# MegaLLM API Key (Required for blog generation)
MEGALLM_API_KEY=sk-mega-YOUR_KEY_HERE
MODEL=claude-opus-4-6
```

### Get Required Credentials

**MongoDB:**
- **Local:** Install MongoDB and run `mongod`
- **Cloud:** Free tier at https://mongodb.com/cloud/atlas

**MegaLLM API:**
- Sign up at https://beta.megallm.io
- Use claude-opus-4-6 model

---

## 🛠️ How to Use

### Via Web Dashboard
1. Select an account (Account 1-5)
2. Click **🚀 Generate Blogs Now**
3. Blogs appear in real-time as they're generated
4. Mark blogs as "Posted" when shared
5. Delete drafts with 🗑️

### Via Command Line (Scraping)

```bash
# Scrape new articles from RSS feeds
python scrape_to_mongo.py --limit 50

# Result: Articles saved to MongoDB articles collection
```

### Via Python (Blog Generation)

```python
from blog_platform.blog_generator import BlogGenerator
from blog_platform.config import Config

gen = BlogGenerator(
    api_key=Config.MEGALLM_API_KEY,
    base_url=Config.MEGALLM_BASE_URL,
    model=Config.MODEL
)

blog = gen.generate_blog(
    topic="Cost Optimization",
    topic_description="How to reduce LLM inference costs",
    keywords=["cost", "optimization", "tokens"]
)

print(blog["title"])
print(blog["body"])
```

---

## 📊 Architecture

```
RSS Feeds (TechCrunch, Medium, HN)
    ↓
scrape_to_mongo.py → Articles in MongoDB
    ↓
wf1.py (optional) → Content Analysis
    ↓
BlogGenerator (MegaLLM API)
    ↓
Flask API (/api/blogs/generate)
    ↓
MongoDB: blogs collection
    ↓
Web Dashboard (http://localhost:5000)
```

---

## 🎓 Key Components

### 1. **scrape_to_mongo.py**
Pulls articles from RSS feeds and stores them in MongoDB. Prevents duplicates using guid/link.

### 2. **wf1.py**
Content analysis stub. In production, would use MegaLLM to analyze articles for marketing angles.

### 3. **blog_platform/blog_generator.py**
Calls MegaLLM API to generate blog posts. Takes topic + keywords → returns title + body.

### 4. **blog_platform/app.py**
Flask REST API with routes:
- `GET /api/accounts` - List accounts
- `GET /api/blogs?account_id=...` - List blogs
- `POST /api/blogs/generate` - Generate new blogs
- `PUT /api/blogs/<id>/mark-posted` - Mark as published
- `DELETE /api/blogs/<id>` - Delete draft blog

### 5. **blog_platform/database.py**
MongoDB abstraction layer with **fallback to in-memory database** if MongoDB is unavailable.

### 6. **blog_platform/templates/index.html**
Modern responsive dashboard with:
- Account selection
- Blog statistics (total, draft, posted)
- Blog library with filtering
- Real-time generation feedback

---

## 📚 Topics & Accounts

### 4 Topics (CTO-focused):
1. **Cost Optimization** - LLM inference cost reduction
2. **Performance & Speed** - Latency and throughput
3. **Reliability & Uptime** - Failover and SLA
4. **Infrastructure & Compliance** - Security and data residency

### 5 Accounts:
- Account 1: ShipAIFast
- Account 2: InferenceDaily
- Account 3: AGIorBust
- Account 4: TokenAIz
- Account 5: TokensAndTakes

**Default:** 3 blogs per topic = 12 blogs per account per day

---

## 🔌 API Endpoints

### GET Requests
```bash
# Get all accounts
curl http://localhost:5000/api/accounts

# Get blogs for an account
curl "http://localhost:5000/api/blogs?account_id=account_1"

# Get dashboard stats
curl http://localhost:5000/api/dashboard/account_1

# Get blog details
curl http://localhost:5000/api/blogs/{blog_id}

# Get generation history
curl http://localhost:5000/api/generation-history/account_1
```

### POST Requests
```bash
# Generate blogs
curl -X POST http://localhost:5000/api/blogs/generate \
  -H "Content-Type: application/json" \
  -d '{"account_id": "account_1"}'
```

### PUT Requests
```bash
# Mark blog as posted
curl -X PUT http://localhost:5000/api/blogs/{blog_id}/mark-posted
```

### DELETE Requests
```bash
# Delete a blog
curl -X DELETE http://localhost:5000/api/blogs/{blog_id}
```

---

## 🗄️ Database Schema

### accounts
```json
{
  "account_id": "account_1",
  "name": "ShipAIFast",
  "description": "Main content account",
  "created_at": "2025-01-01T00:00:00Z",
  "blog_count": 12,
  "posted_count": 8,
  "last_generation": "2025-01-04T12:00:00Z"
}
```

### blogs
```json
{
  "_id": ObjectId(),
  "account_id": "account_1",
  "title": "How to Reduce LLM Costs by 60%",
  "body": "Full blog post content...",
  "topic": "cost_optimization",
  "status": "draft",  // or "posted"
  "created_at": "2025-01-04T12:00:00Z",
  "posted_at": null
}
```

### articles (from scraping)
```json
{
  "_id": ObjectId(),
  "title": "OpenAI Releases GPT-5",
  "link": "https://techcrunch.com/...",
  "content": "Article body...",
  "source": "techcrunch",
  "scrape_run_id": "uuid",
  "status": "pending"
}
```

---

## 🚀 Deployment

### Local Development
```bash
cd blog_generation_pipeline
python blog_platform/app.py
```

### Production (Heroku)
```bash
# Set MongoDB URI and API key
heroku config:set MONGODB_URI="mongodb+srv://..."
heroku config:set MEGALLM_API_KEY="sk-mega-..."

# Deploy
git push heroku main
```

### Docker (Optional)
```bash
docker build -t blog-gen .
docker run -p 5000:5000 -e MONGODB_URI=... -e MEGALLM_API_KEY=... blog-gen
```

---

## 🐛 Troubleshooting

### MongoDB Connection Fails
- **Local:** Ensure MongoDB is running (`mongod`)
- **Atlas:** Check connection string in `.env`
- **Fallback:** App uses in-memory database automatically

### API Key Not Working
- Verify `MEGALLM_API_KEY` is set in `.env`
- Check key is active at https://beta.megallm.io
- Ensure free tier is available (Qwen model)

### Blogs Not Generating
- Check error in dashboard
- Verify API key in `.env`
- Check MongoDB connection
- View logs: `tail -f *.log`

---

## 📖 Examples

### Generate blog for account_1
```bash
curl -X POST http://localhost:5000/api/blogs/generate \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "account_1",
    "topics": {
      "cost_optimization": 2,
      "performance": 1
    }
  }'
```

### Mark blog as posted
```bash
curl -X PUT http://localhost:5000/api/blogs/507f1f77bcf86cd799439011/mark-posted
```

### Get dashboard data
```bash
curl http://localhost:5000/api/dashboard/account_1 | jq .
```

---

## 💡 Tips

1. **MegaLLM Pipeline:** Uses claude-opus-4-6 model for high-quality content generation
2. **Batch Generation:** Generate multiple blogs per topic for variety
3. **Scheduling:** Set up cron job calling `/api/blogs/generate` every 2 hours
4. **Scraping:** Run scraper daily to keep article pool fresh
5. **Monitoring:** Check generation history for performance analysis

---

## 📝 License

This is a self-contained blog generation platform. All files needed are in this folder.

---

## 🤝 Support

- Check `.env.example` for required configuration
- Ensure MongoDB is accessible
- Verify MegaLLM API key is valid
- Review logs in Flask console for errors

**Happy blogging!** 📝✨
