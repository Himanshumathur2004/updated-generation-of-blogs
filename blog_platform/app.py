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

from config import Config
from database import Database
from blog_generator import BlogGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
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
    if not Config.OPENROUTER_API_KEY:
        logger.error("ERROR: OPENROUTER_API_KEY not set in .env file!")
        logger.error("Set OPENROUTER_API_KEY=sk-or-v1-... in .env")
        return False
    return True

# Initialize database and generator
db = None
blog_generator = None

try:
    if not validate_config():
        raise ValueError("Configuration validation failed")
    
    db = Database(Config.MONGODB_URI, Config.MONGODB_DB)
    blog_generator = BlogGenerator(Config.OPENROUTER_API_KEY, Config.OPENROUTER_BASE_URL, Config.OPENROUTER_MODEL)
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
    """Create accounts if they don't exist, or update if names changed."""
    created = 0
    updated = 0
    
    for account in Config.ACCOUNTS:
        existing_account = db.get_account(account["id"])
        if existing_account:
            if existing_account.get("name") != account["name"] or existing_account.get("description") != account["description"]:
                db.update_account(account["id"], account["name"], account["description"])
                updated += 1
        else:
            if db.create_account(account["id"], account["name"], account["description"]):
                created += 1
    
    if created > 0 or updated > 0:
        logger.info(f"Accounts: {created} created, {updated} updated")

init_accounts()


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
    
    if not topics_to_generate:
        topics_to_generate = {topic_id: 3 for topic_id in Config.TOPICS.keys()}
    
    generated_count = 0
    error = None
    
    try:
        for topic_id, count in topics_to_generate.items():
            if topic_id not in Config.TOPICS:
                continue
            
            topic_info = Config.TOPICS[topic_id]
            
            for i in range(count):
                logger.info(f"Generating blog for topic: {topic_id}")
                blog_data = blog_generator.generate_blog(
                    topic=topic_info["name"],
                    topic_description=topic_info["description"],
                    keywords=topic_info["keywords"]
                )
                
                if blog_data:
                    blog_data["account_id"] = account_id
                    blog_data["topic"] = topic_id
                    db.insert_blog(blog_data)
                    generated_count += 1
                else:
                    logger.warning(f"Blog generation returned None for {topic_id}")
        
    except Exception as e:
        error = str(e)
        logger.error(f"Generation error: {error}")
    
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
    if not blog_generator or not db:
        return jsonify({
            "error": "Blog generator not initialized",
            "message": "Check .env configuration"
        }), 500
    
    logger.info("\n" + "="*80)
    logger.info("BULK GENERATION STARTED - One-click multi-account workflow")
    logger.info("="*80)
    
    # Get all accounts
    accounts = db.get_all_accounts()
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
    
    # Step 2: Generate insights from pending articles
    logger.info("\n💡 STEP 2: Generating insights from pending articles...")
    try:
        if db.is_memory:
            return jsonify({
                "error": "MongoDB required",
                "message": "In-memory database does not support articles"
            }), 400
        
        articles_collection = db.db.articles
        pending_articles = list(articles_collection.find({"status": "pending"}).limit(5))
        
        logger.info(f"Found {len(pending_articles)} pending articles")
        
        generated_blogs = []
        for article in pending_articles:
            blog_data = blog_generator.generate_blog_from_article(article)
            if blog_data:
                generated_blogs.append({
                    "title": blog_data["title"],
                    "body": blog_data["body"],
                    "source_article_id": str(article.get("_id", "")),
                    "source_article_title": article.get("title", "")
                })
                
                # Mark article as processed
                articles_collection.update_one(
                    {"_id": article["_id"]},
                    {"$set": {"status": "processed"}}
                )
                logger.info(f"✓ Generated insight: {blog_data['title'][:50]}")
        
        logger.info(f"✓ Generated {len(generated_blogs)} blog insights")
        
    except Exception as e:
        logger.error(f"✗ Error generating insights: {e}")
        generated_blogs = []
    
    # Step 3: Create 5 variants for each generated blog (one per account)
    logger.info("\n🎨 STEP 3: Creating 5 variants per blog (one for each account)...")
    
    total_variants_created = 0
    variants_per_account = {acc["account_id"]: 0 for acc in accounts}
    
    for blog_idx, blog in enumerate(generated_blogs, 1):
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
                
                blog_entry = {
                    "title": variant["title"],
                    "body": variant["body"],
                    "account_id": account["account_id"],
                    "status": "draft",
                    "source_type": "bulk_generated",
                    "source_article_id": blog.get("source_article_id", ""),
                    "source_article_title": blog.get("source_article_title", ""),
                    "variant_of": blog["title"],
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
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
