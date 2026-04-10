"""Flask backend API for blog platform."""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import wraps
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add parent directory to path so we can import root-level modules
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add blog_platform to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from database import Database
from blog_generator import BlogGenerator

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get template folder path
template_dir = Path(__file__).parent / "templates"

# Initialize Flask app
app = Flask(__name__, template_folder=str(template_dir))
app.config.from_object(Config)
CORS(app)

# Validate configuration
def validate_config():
    """Validate required configuration."""
    # API key is now hardcoded in config
    if not Config.MEGALLM_API_KEY:
        logger.error("ERROR: MegaLLM API key not configured!")
        return False
    return True

# Initialize database and generator
db = None
blog_generator = None

try:
    if not validate_config():
        raise ValueError("Configuration validation failed")
    
    db = Database(Config.MONGODB_URI, Config.MONGODB_DB)
    blog_generator = BlogGenerator(Config.MEGALLM_API_KEY, Config.MEGALLM_BASE_URL, Config.MODEL)
    logger.info("✓ App initialized")
    
except Exception as e:
    logger.error(f"Initialization error: {e}")
    
# Ensure we have a database instance (either MongoDB or in-memory)
if db is None:
    try:
        from database import InMemoryDatabase
        db = InMemoryDatabase()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

# Initialize accounts on startup
def init_accounts():
    """Create accounts if they don't exist, update if names changed, delete if removed from config."""
    created = 0
    updated = 0
    deleted = 0

    config_ids = {account["id"] for account in Config.ACCOUNTS}

    # Remove accounts that are no longer in the config
    if not db.is_memory:
        try:
            all_existing = db.get_all_accounts()
            for existing in all_existing:
                if existing.get("account_id") not in config_ids:
                    db.db.accounts.delete_one({"account_id": existing["account_id"]})
                    deleted += 1
        except Exception as e:
            logger.warning(f"Account cleanup failed: {e}")

    for account in Config.ACCOUNTS:
        existing_account = db.get_account(account["id"])
        if existing_account:
            if existing_account.get("name") != account["name"] or existing_account.get("description") != account["description"]:
                db.update_account(account["id"], account["name"], account["description"])
                updated += 1
        else:
            if db.create_account(account["id"], account["name"], account["description"]):
                created += 1

    if created > 0 or updated > 0 or deleted > 0:
        logger.info(f"Accounts: {created} created, {updated} updated, {deleted} deleted")

init_accounts()


def get_medium_settings() -> dict:
    """Return Medium metadata defaults for the dedicated Medium account."""
    return {
        "author_name": Config.MEDIUM_AUTHOR_NAME,
        "author_handle": Config.MEDIUM_AUTHOR_HANDLE,
        "author_twitter": Config.MEDIUM_AUTHOR_TWITTER,
        "publication_slug": Config.MEDIUM_PUBLICATION_SLUG,
        "hero_image_url": Config.MEDIUM_HERO_IMAGE_URL,
        "hero_image_alt": "MegaLLM deep-dive article cover",
        "backlink_url": Config.MEGALLM_BACKLINK_URL,
    }


def get_devto_settings() -> dict:
    """Return dev.to metadata defaults for the dedicated dev.to account."""
    return {
        "author_name": getattr(Config, "DEVTO_AUTHOR_NAME", "MegaLLM Editorial Team"),
        "author_username": getattr(Config, "DEVTO_AUTHOR_USERNAME", "megallm"),
        "canonical_base_url": getattr(Config, "DEVTO_CANONICAL_BASE_URL", "https://dev.to/megallm"),
        "backlink_url": getattr(Config, "MEGALLM_BACKLINK_URL", "https://beta.megallm.io"),
    }


def get_tumblr_settings() -> dict:
    """Return Tumblr metadata defaults for the dedicated Tumblr account."""
    return {
        "blog_name": getattr(Config, "TUMBLR_BLOG_NAME", "megallm"),
        "author_name": getattr(Config, "TUMBLR_AUTHOR_NAME", "MegaLLM"),
        "base_url": getattr(Config, "TUMBLR_BASE_URL", "https://megallm.tumblr.com"),
    }


def get_blogger_settings() -> dict:
    """Return Blogger metadata defaults for the dedicated Blogger account."""
    return {
        "blog_name": getattr(Config, "BLOGGER_BLOG_NAME", "MegaLLM Insights"),
        "author_name": getattr(Config, "BLOGGER_AUTHOR_NAME", "MegaLLM Editorial Team"),
        "base_url": getattr(Config, "BLOGGER_BASE_URL", "https://megallm.blogspot.com"),
    }


def get_quora_settings() -> dict:
    """Return Quora metadata defaults for the dedicated Quora account."""
    return {
        "site_name": Config.QUORA_SITE_NAME,
        "twitter_handle": Config.QUORA_TWITTER_HANDLE,
        "fb_app_id": Config.QUORA_FB_APP_ID,
        "base_url": Config.QUORA_BASE_URL,
        "ios_app_store_id": Config.QUORA_IOS_APP_STORE_ID,
        "ios_app_name": Config.QUORA_IOS_APP_NAME,
        "android_package": Config.QUORA_ANDROID_PACKAGE,
        "android_app_name": Config.QUORA_ANDROID_APP_NAME,
        "app_deep_link_path": Config.QUORA_APP_DEEP_LINK_PATH,
        "author_name": Config.QUORA_AUTHOR_NAME,
        "author_slug": Config.QUORA_AUTHOR_SLUG,
        "author_profile_url": Config.QUORA_AUTHOR_PROFILE_URL,
        "question_asker_name": Config.QUORA_QUESTION_ASKER_NAME,
        "image_url": Config.QUORA_IMAGE_URL,
        "image_alt": "Quora-style question and answer cover",
        "locale": "en_US",
    }


# ============================================================================
# STATIC & TEMPLATE ROUTES
# ============================================================================

@app.route("/", methods=["GET"])
def index():
    """Serve the main dashboard HTML."""
    return render_template("index.html")


# ============================================================================
# ACCOUNT ROUTES
# ============================================================================

@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    """Get all accounts."""
    accounts = db.get_all_accounts()
    return jsonify({"accounts": accounts}), 200


@app.route("/api/accounts/<account_id>", methods=["GET"])
def get_account(account_id):
    """Get single account details."""
    account = db.get_account(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    return jsonify(account), 200


# ============================================================================
# BLOG ROUTES
# ============================================================================

@app.route("/api/blogs", methods=["GET"])
def get_blogs():
    """Get blogs for an account."""
    account_id = request.args.get("account_id")
    status = request.args.get("status")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    
    if not account_id:
        return jsonify({"error": "Missing account_id"}), 400
    
    blogs = db.get_blogs_by_account(account_id, status=status, limit=limit, offset=offset)
    
    for blog in blogs:
        if "_id" in blog:
            blog["_id"] = str(blog["_id"])
    
    return jsonify({
        "account_id": account_id,
        "blogs": blogs,
        "count": len(blogs)
    }), 200


@app.route("/api/blogs/<blog_id>", methods=["GET"])
def get_blog(blog_id):
    """Get single blog details."""
    blog = db.get_blog_by_id(blog_id)
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    return jsonify(blog), 200


@app.route("/api/blogs/<blog_id>/mark-posted", methods=["PUT"])
def mark_blog_posted(blog_id):
    """Mark a blog as posted."""
    success = db.mark_blog_posted(blog_id)
    
    if not success:
        return jsonify({"error": "Blog not found or could not be updated"}), 404
    
    blog = db.get_blog_by_id(blog_id)
    return jsonify({
        "message": "Blog marked as posted",
        "blog": blog
    }), 200


@app.route("/api/blogs/<blog_id>/copy", methods=["GET"])
def copy_blog_content(blog_id):
    """Get blog content for copying."""
    blog = db.get_blog_by_id(blog_id)
    
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    
    return jsonify({
        "blog_id": blog_id,
        "title": blog.get("title", ""),
        "body": blog.get("body", ""),
        "topic": blog.get("topic", ""),
    }), 200


@app.route("/api/blogs/<blog_id>", methods=["DELETE"])
def delete_blog(blog_id):
    """Delete a blog (draft only)."""
    blog = db.get_blog_by_id(blog_id)
    
    if not blog:
        return jsonify({"error": "Blog not found"}), 404
    
    if blog.get("status") != "draft":
        return jsonify({"error": "Can only delete draft blogs"}), 400
    
    success = db.delete_blog(blog_id)
    
    if not success:
        return jsonify({"error": "Could not delete blog"}), 500
    
    return jsonify({"message": "Blog deleted successfully"}), 200


@app.route("/api/dashboard/<account_id>", methods=["GET"])
def dashboard(account_id):
    """Get dashboard summary for an account."""
    summary = db.get_dashboard_summary(account_id)
    if not summary:
        return jsonify({"error": "Account not found"}), 404
    return jsonify(summary), 200


@app.route("/api/generation-history/<account_id>", methods=["GET"])
def generation_history(account_id):
    """Get generation history for an account."""
    history = db.get_generation_history(account_id)
    return jsonify({"history": history}), 200


@app.route("/api/blogs/generate", methods=["POST"])
def generate_blogs():
    """Generate new blogs for an account."""
    logger.info("[ENDPOINT] /api/blogs/generate POST request received")
    if not blog_generator or not db:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration"
        }), 500
    
    data = request.get_json() or {}
    account_id = data.get("account_id")
    topics_to_generate = data.get("topics")
    
    if not account_id:
        return jsonify({"error": "Missing account_id"}), 400
    
    account = db.get_account(account_id)
    if not account:
        return jsonify({"error": f"Account {account_id} not found"}), 404
    
    # Ensure topics_to_generate is a dict
    if not topics_to_generate:
        topics_to_generate = {topic_id: 3 for topic_id in Config.TOPICS.keys()}
    elif isinstance(topics_to_generate, str):
        # If a single topic ID is provided as string, generate 3 blogs for it
        topics_to_generate = {topics_to_generate: 3}
    
    generated_count = 0
    error = None
    devto_account_id = getattr(Config, "DEVTO_ACCOUNT_ID", "account_6")
    tumblr_account_id = getattr(Config, "TUMBLR_ACCOUNT_ID", "account_7")
    blogger_account_id = getattr(Config, "BLOGGER_ACCOUNT_ID", "account_1")

    # For Quora/Medium/Dev.to/Tumblr/Blogger accounts: scrape fresh articles first, use them as content source
    articles_pool = []
    if account_id in {Config.QUORA_ACCOUNT_ID, Config.MEDIUM_ACCOUNT_ID, devto_account_id, tumblr_account_id, blogger_account_id} and not db.is_memory:
        try:
            from scrape_to_mongo import scrape_new_articles
            total_needed = sum(topics_to_generate.values())
            scrape_result = scrape_new_articles(limit=max(5, total_needed))
            logger.info(f"[SCRAPE] Inserted {scrape_result.get('inserted', 0)} new articles before generation")
            raw_pool = list(db.db.articles.find({"status": "pending"}).sort("isoDate", -1).limit(total_needed * 10))
            # Deduplicate by title — keep only the first occurrence per title
            seen_titles = set()
            articles_pool = []
            for a in raw_pool:
                t = (a.get("title") or "").strip()
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    articles_pool.append(a)
                    if len(articles_pool) >= total_needed * 2:
                        break
            logger.info(f"[SCRAPE] {len(articles_pool)} unique pending articles available for generation")
        except Exception as e:
            logger.warning(f"[SCRAPE] Failed, falling back to topic-based generation: {e}")
            articles_pool = []

    try:
        for topic_id, count in topics_to_generate.items():
            if topic_id not in Config.TOPICS:
                continue

            topic_info = Config.TOPICS[topic_id]

            for i in range(count):
                # Use a scraped article if available, else fall back to topic-based
                article = articles_pool.pop(0) if articles_pool else None

                if article:
                    logger.info(f"Generating from article: {article.get('title', 'N/A')[:60]}")
                    blog_data = blog_generator.generate_blog_from_article(article)
                    # Mark article as processed
                    try:
                        db.db.articles.update_one({"_id": article["_id"]}, {"$set": {"status": "processed"}})
                    except Exception:
                        pass
                else:
                    logger.info(f"No article available, generating from topic: {topic_id}")
                    blog_data = blog_generator.generate_blog(
                        topic=topic_info["name"],
                        topic_description=topic_info["description"],
                        keywords=topic_info["keywords"]
                    )
                
                if blog_data:
                    if account_id == Config.MEDIUM_ACCOUNT_ID:
                        blog_data = blog_generator.package_medium_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=topic_info["keywords"],
                            topic=topic_info["name"],
                            medium_settings=get_medium_settings(),
                        )
                    elif account_id == Config.QUORA_ACCOUNT_ID:
                        blog_data = blog_generator.package_quora_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=topic_info["keywords"],
                            topic=topic_info["name"],
                            quora_settings=get_quora_settings(),
                        )
                    elif account_id == devto_account_id:
                        blog_data = blog_generator.package_devto_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=topic_info["keywords"],
                            topic=topic_info["name"],
                            devto_settings=get_devto_settings(),
                        )
                    elif account_id == tumblr_account_id:
                        blog_data = blog_generator.package_tumblr_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=topic_info["keywords"],
                            topic=topic_info["name"],
                            tumblr_settings=get_tumblr_settings(),
                        )
                    elif account_id == blogger_account_id:
                        blog_data = blog_generator.package_blogger_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=topic_info["keywords"],
                            topic=topic_info["name"],
                            blogger_settings=get_blogger_settings(),
                        )
                    blog_data["account_id"] = account_id
                    blog_data["topic"] = topic_id
                    db.insert_blog(blog_data)
                    generated_count += 1
                else:
                    logger.warning(f"Blog generation returned None for {topic_id}")
        
    except Exception as e:
        error = str(e)
        logger.exception(f"Generation error: {error}")
    
    # Log generation event
    db.log_generation(account_id, generated_count, error)
    
    return jsonify({
        "account_id": account_id,
        "generated_count": generated_count,
        "error": error,
        "message": f"Successfully generated {generated_count} blogs" if not error else f"Generation failed: {error}"
    }), 200 if not error else 500


@app.route("/api/blogs/generate-from-articles", methods=["POST"])
def generate_blogs_from_articles():
    """Generate blogs based on scraped articles."""
    if not blog_generator or not db:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration"
        }), 500
    
    data = request.get_json() or {}
    account_id = data.get("account_id")
    num_blogs = int(data.get("num_blogs", 5))
    
    if not account_id:
        return jsonify({"error": "Missing account_id"}), 400
    
    account = db.get_account(account_id)
    if not account:
        return jsonify({"error": f"Account {account_id} not found"}), 404
    
    generated_count = 0
    error = None
    devto_account_id = getattr(Config, "DEVTO_ACCOUNT_ID", "account_6")
    tumblr_account_id = getattr(Config, "TUMBLR_ACCOUNT_ID", "account_7")
    blogger_account_id = getattr(Config, "BLOGGER_ACCOUNT_ID", "account_1")

    try:
        # Get pending articles from MongoDB
        if db.is_memory:
            logger.warning("Cannot get articles from in-memory database. Please use MongoDB.")
            return jsonify({
                "error": "Articles feature requires MongoDB",
                "message": "In-memory database does not support articles"
            }), 400
        
        articles_collection = db.db.articles
        pending_articles = list(articles_collection.find({"status": "pending"}).limit(num_blogs))
        
        logger.info(f"Found {len(pending_articles)} pending articles to generate blogs from")
        
        for article in pending_articles:
            try:
                logger.info(f"Generating blog from article: {article.get('title', 'N/A')[:50]}")
                
                blog_data = blog_generator.generate_blog_from_article(article)
                
                if blog_data:
                    article_topic = article.get("title", "general")
                    if account_id == Config.MEDIUM_ACCOUNT_ID:
                        blog_data = blog_generator.package_medium_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=blog_data.get("tags", [article.get("source", "AI")]),
                            topic=article_topic,
                            medium_settings=get_medium_settings(),
                        )
                    elif account_id == Config.QUORA_ACCOUNT_ID:
                        blog_data = blog_generator.package_quora_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=blog_data.get("tags", [article.get("source", "AI")]),
                            topic=article_topic,
                            quora_settings=get_quora_settings(),
                        )
                    elif account_id == devto_account_id:
                        blog_data = blog_generator.package_devto_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=blog_data.get("tags", [article.get("source", "AI")]),
                            topic=article_topic,
                            devto_settings=get_devto_settings(),
                        )
                    elif account_id == tumblr_account_id:
                        blog_data = blog_generator.package_tumblr_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=blog_data.get("tags", [article.get("source", "AI")]),
                            topic=article_topic,
                            tumblr_settings=get_tumblr_settings(),
                        )
                    elif account_id == blogger_account_id:
                        blog_data = blog_generator.package_blogger_post(
                            title=blog_data.get("title", ""),
                            body=blog_data.get("body", ""),
                            keywords=blog_data.get("tags", [article.get("source", "AI")]),
                            topic=article_topic,
                            blogger_settings=get_blogger_settings(),
                        )
                    blog_data["account_id"] = account_id
                    blog_data["source_type"] = "scraped_article"
                    db.insert_blog(blog_data)
                    
                    # Mark article as processed
                    articles_collection.update_one(
                        {"_id": article["_id"]},
                        {"$set": {"status": "processed"}}
                    )
                    
                    generated_count += 1
                    logger.info(f"Blog generated and saved: {blog_data.get('title', 'N/A')[:50]}")
                else:
                    logger.warning(f"Failed to generate blog for article: {article.get('title', 'N/A')[:50]}")
            except Exception as e:
                logger.error(f"Error generating blog from article: {e}")
                continue
        
    except Exception as e:
        error = str(e)
        logger.error(f"Generation from articles error: {error}")
    
    # Log generation event
    db.log_generation(account_id, generated_count, error)
    
    return jsonify({
        "account_id": account_id,
        "generated_count": generated_count,
        "articles_processed": len(pending_articles),
        "error": error,
        "message": f"Successfully generated {generated_count} blogs from {len(pending_articles)} articles" if not error else f"Generation failed: {error}"
    }), 200 if not error else 500


@app.route("/api/bulk-generate", methods=["POST"])
def bulk_generate_for_all_accounts():
    """
    One-click bulk generation:
    1. Fetch recent articles
    2. Generate insights from articles
    3. Create 5 variants (one per account) with unique titles but same essence
    """
    import time
    start_time = time.time()
    OPERATION_TIMEOUT = 50  # Stop after 50 seconds (leave 10s for response on 60s worker timeout)
    
    if not blog_generator or not db:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration"
        }), 500
    
    logger.info("\n" + "="*80)
    logger.info("BULK GENERATION STARTED - One-click multi-account workflow")
    logger.info("="*80)
    
    # Get all accounts
    accounts = [
        acc for acc in db.get_all_accounts()
        if acc["account_id"] not in {Config.MEDIUM_ACCOUNT_ID, Config.QUORA_ACCOUNT_ID}
    ]
    if not accounts:
        return jsonify({"error": "No accounts found"}), 404
    
    account_ids = [acc["account_id"] for acc in accounts]
    logger.info(f"📊 Processing {len(account_ids)} accounts: {[acc.get('name') for acc in accounts]}")
    
    # Step 1: Fetch recent articles using scrape function
    logger.info("\n📰 STEP 1: Fetching recent articles from RSS feeds...")
    try:
        from scrape_to_mongo import scrape_new_articles
        scrape_result = scrape_new_articles(limit=10)
        articles_inserted = scrape_result.get("inserted", 0)
        logger.info(f"✓ Scraped {articles_inserted} new articles")
    except Exception as e:
        logger.error(f"✗ Error scraping articles: {e}")
        articles_inserted = 0
    
    # Step 2: Generate draft blogs instantly from articles (no API calls)
    logger.info("\n💡 STEP 2: Creating draft blogs from pending articles (instant, no API calls)...")
    try:
        if db.is_memory:
            return jsonify({
                "error": "MongoDB required",
                "message": "In-memory database does not support articles"
            }), 400
        
        articles_collection = db.db.articles
        pending_articles = list(articles_collection.find({"status": "pending"}).limit(3))  # Reduce to 3
        
        logger.info(f"Found {len(pending_articles)} pending articles")
        
        generated_blogs = []
        for article in pending_articles:
            # Create a quick draft from article without API call
            article_title = article.get("title", "Untitled")
            article_content = article.get("content", article.get("contentSnippet", ""))[:1000]
            
            # Create simple title from article
            simple_title = article_title[:60] + ("..." if len(article_title) > 60 else "")
            
            generated_blogs.append({
                "title": simple_title,
                "body": article_content,
                "source_article_id": str(article.get("_id", "")),
                "source_article_title": article_title
            })
            
            # Mark article as processed
            articles_collection.update_one(
                {"_id": article["_id"]},
                {"$set": {"status": "processed"}}
            )
            logger.info(f"✓ Created draft: {simple_title[:50]}")
        
        logger.info(f"✓ Created {len(generated_blogs)} draft blogs")
        
    except Exception as e:
        logger.error(f"✗ Error creating drafts: {e}")
        generated_blogs = []
    
    # Step 3: Create 5 variants for each generated blog (one per account)
    logger.info("\n🎨 STEP 3: Creating 5 variants per blog (one for each account)...")
    
    total_variants_created = 0
    variants_per_account = {acc["account_id"]: 0 for acc in accounts}
    
    for blog_idx, blog in enumerate(generated_blogs, 1):
        # Check if we're running out of time
        elapsed = time.time() - start_time
        if elapsed > OPERATION_TIMEOUT - 5:  # Stop with 5 seconds buffer
            logger.warning(f"⏱️ Operation timeout approaching ({elapsed:.1f}s) - stopping variant generation")
            break
        
        logger.info(f"\n  Blog {blog_idx}/{len(generated_blogs)}: {blog['title'][:50]}")
        
        # Generate 5 variants of this blog
        variants = blog_generator.generate_blog_variants(
            blog_content=blog["body"],
            blog_title=blog["title"],
            num_variants=len(account_ids),
            account_names=[acc.get("name") for acc in accounts]
        )
        
        if variants and len(variants) >= len(account_ids):
            logger.info(f"    ✓ Generated {len(variants)} variants")
            
            # Assign one variant per account
            for account_idx, account in enumerate(accounts):
                variant = variants[account_idx]

                if account["account_id"] == Config.MEDIUM_ACCOUNT_ID:
                    variant = blog_generator.package_medium_post(
                        title=variant.get("title", ""),
                        body=variant.get("body", ""),
                        keywords=["MegaLLM", "AI", "Medium", "LLM", "Engineering"],
                        topic=blog.get("title", "MegaLLM Insights"),
                        medium_settings=get_medium_settings(),
                    )
                elif account["account_id"] == Config.QUORA_ACCOUNT_ID:
                    variant = blog_generator.package_quora_post(
                        title=variant.get("title", ""),
                        body=variant.get("body", ""),
                        keywords=["MegaLLM", "AI", "Quora", "LLM", "Engineering"],
                        topic=blog.get("title", "MegaLLM Insights"),
                        quora_settings=get_quora_settings(),
                    )
                
                blog_entry = {
                    "title": variant["title"],
                    "body": variant["body"],
                    "description": variant.get("description", ""),
                    "account_id": account["account_id"],
                    "status": "draft",
                    "source_type": "bulk_generated",
                    "source_article_id": blog.get("source_article_id", ""),
                    "source_article_title": blog.get("source_article_title", ""),
                    "variant_of": blog["title"],
                    "tags": variant.get("tags") or ["MegaLLM", "AI", "LLM", "Engineering", "Automation"],
                    "created_at": datetime.now(timezone.utc).isoformat()
                }

                if variant.get("post_format"):
                    blog_entry["post_format"] = variant["post_format"]
                
                db.insert_blog(blog_entry)
                variants_per_account[account["account_id"]] += 1
                total_variants_created += 1
                
                logger.info(f"      • {account['name']}: {variant['title'][:45]}")
        else:
            logger.warning(f"    ✗ Failed to generate variants or insufficient variants")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("BULK GENERATION COMPLETED")
    logger.info("="*80)
    logger.info(f"📊 Summary:")
    logger.info(f"   Articles scraped: {articles_inserted}")
    logger.info(f"   Blog insights generated: {len(generated_blogs)}")
    logger.info(f"   Total variants created: {total_variants_created}")
    logger.info(f"   Per account:")
    for account in accounts:
        count = variants_per_account[account["account_id"]]
        logger.info(f"      - {account['name']}: {count} blogs")
    
    # Log generation event for each account
    for account in accounts:
        count = variants_per_account[account["account_id"]]
        db.log_generation(account["account_id"], count, None)
    
    return jsonify({
        "status": "success",
        "articles_scraped": articles_inserted,
        "blog_insights_generated": len(generated_blogs),
        "total_variants_created": total_variants_created,
        "variants_per_account": variants_per_account,
        "message": f"Generated {total_variants_created} blog variants across {len(account_ids)} accounts"
    }), 200


if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=5000)

