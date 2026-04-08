"""Insight-driven blog scheduler placeholder."""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def generate_blogs_from_insights_now(db, blog_generator, account_id: str, insight_limit: int = 10) -> Dict[str, Any]:
    """
    Generate blogs from insights for a specific account.
    
    This function:
    1. Fetches pending insights from MongoDB
    2. Maps insights to blog topics
    3. Generates blogs for each insight using the blog_generator
    
    Args:
        db: Database instance
        blog_generator: BlogGenerator instance
        account_id: Account ID to generate blogs for
        insight_limit: Maximum number of insights to process
    
    Returns:
        Dictionary with success status and generation count
    """
    try:
        logger.info(f"Generating blogs from insights for {account_id}")
        
        if db.is_memory:
            logger.warning("In-memory database - cannot access insights collection")
            return {
                "success": False,
                "account_id": account_id,
                "blogs_generated": 0,
                "error": "MongoDB required for insights"
            }
        
        # Fetch pending insights from MongoDB
        insights_collection = db.db.content_insights
        pending_insights = list(insights_collection.find().limit(insight_limit))
        
        logger.info(f"Found {len(pending_insights)} insights to generate blogs from")
        
        generated = 0
        errors = 0
        
        for insight in pending_insights:
            try:
                insight_id = insight.get('_id')
                insight_topic = insight.get('topic', 'General Tech Insights')
                insight_summary = insight.get('summary', '')
                article_id = insight.get('article_id')
                
                logger.info(f"Processing insight {insight_id}: {insight_summary[:50]}")
                
                # Create a blog prompt from the insight
                blog_data = blog_generator.generate_blog(
                    topic=insight_topic,
                    topic_description=insight_summary,
                    keywords=insight.get('keywords', [])
                )
                
                if blog_data:
                    blog_data["account_id"] = account_id
                    blog_data["source_type"] = "insight"
                    blog_data["insight_id"] = str(insight_id)
                    if article_id:
                        blog_data["article_id"] = str(article_id)
                    
                    db.insert_blog(blog_data)
                    generated += 1
                    logger.info(f"Blog generated from insight: {blog_data.get('title', 'N/A')[:40]}")
                else:
                    errors += 1
                    logger.warning(f"Failed to generate blog from insight {insight_id}")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error processing insight: {e}")
                continue
        
        return {
            "success": True,
            "account_id": account_id,
            "blogs_generated": generated,
            "errors": errors,
            "message": f"Generated {generated} blogs from insights ({errors} errors)"
        }
        
    except Exception as e:
        logger.error(f"Error generating from insights: {e}")
        return {
            "success": False,
            "account_id": account_id,
            "blogs_generated": 0,
            "error": str(e)
        }
