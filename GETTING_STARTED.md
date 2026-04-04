# 🚀 Getting Started - 5 Minute Quick Start

This folder contains a **complete, self-contained blog generation platform**. Everything you need is here.

## ⚡ 1-Minute Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env - add your credentials:
# - MONGODB_URI (local or Atlas)
# - OPENROUTER_API_KEY (free from openrouter.ai)

# Install dependencies
pip install -r requirements.txt

# Run quality check
python QUICK_START.py

# Start server
python blog_platform/app.py
```

Then open: **http://localhost:5000**

---

## 📋 What You Need

### 1. MongoDB (Choose One)
- **Local**: `mongod` (install MongoDB locally)
- **Cloud**: Free tier at https://mongodb.com/cloud/atlas

### 2. OpenRouter API Key
- Sign up: https://openrouter.ai (free)
- The Qwen model is free

---

## 🎯 Key Files

| File | Purpose |
|------|---------|
| `blog_platform/app.py` | Flask web server (runs on :5000) |
| `blog_platform/blog_generator.py` | Generates blogs via OpenRouter |
| `scrape_to_mongo.py` | Scrapes RSS feeds for articles |
| `blog_platform/templates/index.html` | Dashboard UI |
| `requirements.txt` | Python dependencies |
| `.env.example` | Configuration template |

---

## 📖 Usage

### Via Web Dashboard
1. Go to http://localhost:5000
2. Select account (Account 1-5)
3. Click "Generate Blogs Now"
4. Blogs appear as they're created

### Via Command Line
```bash
# Scrape articles
python scrape_to_mongo.py

# Generate blogs
curl -X POST http://localhost:5000/api/blogs/generate \
  -H "Content-Type: application/json" \
  -d '{"account_id": "account_1"}'
```

---

## 🔧 Configuration

Edit `.env` with:
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=megallm_blog_platform
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY
OPENROUTER_MODEL=qwen/qwen3.6-plus-preview:free
```

---

## 🎓 Architecture

```
1. Scraping (RSS feeds) → 2. Analysis (WF1) → 3. Blog Gen (OpenRouter)
   ↓                         ↓                  ↓
   articles           content_insights        blogs
   in MongoDB         in MongoDB              in MongoDB
                                                 ↓
                                          Web Dashboard
                                          (localhost:5000)
```

---

## 🆘 Troubleshooting

**MongoDB won't connect?**
- Ensure `mongod` is running, or check MongoDB Atlas URI

**API key not working?**
- Verify key at https://openrouter.ai
- Check free tier is available (Qwen model)

**Blogs not generating?**
- Check dashboard for errors
- Verify both MongoDB and API key are configured

---

## 📚 Learn More

See **README.md** for full documentation, API endpoints, and examples.

---

## 💡 Quick Tips

- ✅ **No external dependencies** - everything in this folder
- ✅ **Free to use** - OpenRouter free tier + MongoDB free tier
- ✅ **Fallback mode** - uses in-memory database if MongoDB unavailable
- ✅ **Ready to scale** - runs on Python/Flask, deploys anywhere

**Happy blogging!** 📝✨
