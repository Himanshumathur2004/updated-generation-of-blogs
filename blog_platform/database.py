"""MongoDB database models and utilities with in-memory fallback."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
import logging
import os

logger = logging.getLogger(__name__)


class InMemoryDatabase:
    """In-memory database fallback when MongoDB is unavailable."""
    
    def __init__(self):
        logger.info("Using in-memory database (MongoDB not available)")
        self.accounts: Dict[str, Dict] = {}
        self.blogs: Dict[str, Dict] = {}  # blog_id -> blog_data
        self.generation_history: List[Dict] = []
        self.next_blog_id = 1
    
    def close(self) -> None:
        """Close database connection (no-op for in-memory)."""
        pass
    
    # ========== ACCOUNT MANAGEMENT ==========
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all accounts."""
        return sorted(self.accounts.values(), key=lambda x: x.get("account_id", ""))
    
    def get_account(self, account_id: str) -> Optional[Dict]:
        """Get single account by ID."""
        return self.accounts.get(account_id)
    
    def create_account(self, account_id: str, name: str, description: str = "") -> bool:
        """Create a new account."""
        if account_id in self.accounts:
            return False
        self.accounts[account_id] = {
            "account_id": account_id,
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "blog_count": 0,
            "posted_count": 0,
            "last_generation": None,
        }
        return True
    
    def update_account(self, account_id: str, name: str, description: str = "") -> bool:
        """Update an existing account's name and description."""
        if account_id in self.accounts:
            self.accounts[account_id]["name"] = name
            self.accounts[account_id]["description"] = description
            return True
        return False
    
    # ========== BLOG MANAGEMENT ==========
    
    def get_blogs_by_account(
        self,
        account_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get blogs for an account, optionally filtered by status."""
        blogs = [
            blog for blog in self.blogs.values()
            if blog["account_id"] == account_id and (status is None or blog["status"] == status)
        ]
        blogs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return blogs[offset:offset + limit]
    
    def get_blog_by_id(self, blog_id: str) -> Optional[Dict]:
        """Get a single blog by ID."""
        return self.blogs.get(str(blog_id))
    
    def insert_blog(self, blog_data: Dict) -> str:
        """Insert a new blog and return its ID."""
        blog_id = str(self.next_blog_id)
        self.next_blog_id += 1
        
        blog_data["_id"] = blog_id
        blog_data["created_at"] = datetime.now(timezone.utc).isoformat()
        blog_data["status"] = "draft"
        blog_data["posted_at"] = None
        blog_data["views"] = 0
        
        self.blogs[blog_id] = blog_data
        return blog_id
    
    def update_blog(self, blog_id: str, update_data: Dict) -> bool:
        """Update blog data."""
        if str(blog_id) not in self.blogs:
            return False
        
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.blogs[str(blog_id)].update(update_data)
        return True
    
    def mark_blog_posted(self, blog_id: str) -> bool:
        """Mark a blog as posted."""
        return self.update_blog(
            blog_id,
            {
                "status": "posted",
                "posted_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def delete_blog(self, blog_id: str) -> bool:
        """Delete a blog."""
        if str(blog_id) in self.blogs:
            del self.blogs[str(blog_id)]
            return True
        return False
    
    def count_blogs_by_status(self, account_id: str) -> Dict[str, int]:
        """Count blogs by status for an account."""
        counts = {}
        for blog in self.blogs.values():
            if blog["account_id"] == account_id:
                status = blog["status"]
                counts[status] = counts.get(status, 0) + 1
        return counts
    
    # ========== GENERATION HISTORY ==========
    
    def log_generation(self, account_id: str, generated_count: int, error: Optional[str] = None) -> None:
        """Log a generation cycle."""
        self.generation_history.append({
            "account_id": account_id,
            "generated_count": generated_count,
            "error": error,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        
        # Update account's last generation time
        if account_id in self.accounts and error is None:
            self.accounts[account_id]["last_generation"] = datetime.now(timezone.utc).isoformat()
            self.accounts[account_id]["blog_count"] += generated_count
    
    def get_generation_history(self, account_id: str, limit: int = 10) -> List[Dict]:
        """Get generation history for an account."""
        history = [h for h in self.generation_history if h["account_id"] == account_id]
        return sorted(history, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]
    
    # ========== BULK OPERATIONS ==========
    
    def get_dashboard_summary(self, account_id: str) -> Dict:
        """Get dashboard summary for an account."""
        account = self.get_account(account_id)
        if not account:
            return {}
        
        status_counts = self.count_blogs_by_status(account_id)
        
        # Get blogs by topic
        topic_counts = {}
        for blog in self.blogs.values():
            if blog["account_id"] == account_id:
                topic = blog.get("topic", "unknown")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Get recent blogs
        recent_blogs = self.get_blogs_by_account(account_id, limit=5)
        
        return {
            "account": account,
            "total_blogs": account.get("blog_count", 0),
            "posted_blogs": status_counts.get("posted", 0),
            "draft_blogs": status_counts.get("draft", 0),
            "status_breakdown": status_counts,
            "blogs_by_topic": topic_counts,
            "recent_blogs": recent_blogs,
        }


class Database:
    """MongoDB database wrapper with in-memory fallback."""
    
    def __init__(self, uri: str, db_name: str):
        self.is_memory = False
        try:
            # Log connection attempt
            logger.info(f"Attempting MongoDB connection...")
            logger.info(f"URI starts with: {uri[:30] if uri else 'NONE'}...")
            logger.info(f"Database: {db_name}")
            
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000)
            # Verify connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self._init_collections()
            logger.info("✓ Connected to MongoDB")
        except Exception as e:
            logger.error(f"✗ MongoDB connection FAILED: {type(e).__name__}: {str(e)[:200]}")
            logger.warning(f"FALLING BACK TO IN-MEMORY DATABASE (data will be lost on restart!)")
            self._fallback = InMemoryDatabase()
            self.is_memory = True
    
    def _init_collections(self) -> None:
        """Initialize collections and indexes."""
        # Create indexes if they don't exist
        self.db.accounts.create_index("account_id", unique=True)
        self.db.blogs.create_index("account_id")
        self.db.blogs.create_index("topic")
        self.db.blogs.create_index("status")
        self.db.blogs.create_index("created_at")
        self.db.generation_history.create_index("account_id")
        self.db.generation_history.create_index("created_at")
    
    def close(self) -> None:
        """Close database connection."""
        if self.is_memory:
            self._fallback.close()
        else:
            self.client.close()
    
    # ========== ACCOUNT MANAGEMENT ==========
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all accounts."""
        if self.is_memory:
            return self._fallback.get_all_accounts()
        return list(self.db.accounts.find({}, {"_id": 0}).sort("account_id", 1))
    
    def get_account(self, account_id: str) -> Optional[Dict]:
        """Get single account by ID."""
        if self.is_memory:
            return self._fallback.get_account(account_id)
        return self.db.accounts.find_one({"account_id": account_id}, {"_id": 0})
    
    def create_account(self, account_id: str, name: str, description: str = "") -> bool:
        """Create a new account."""
        if self.is_memory:
            return self._fallback.create_account(account_id, name, description)
        
        try:
            self.db.accounts.insert_one({
                "account_id": account_id,
                "name": name,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "blog_count": 0,
                "posted_count": 0,
                "last_generation": None,
            })
            return True
        except Exception as e:
            logger.error(f"Error creating account {account_id}: {e}")
            return False
    
    def update_account(self, account_id: str, name: str, description: str = "") -> bool:
        """Update an existing account's name and description."""
        if self.is_memory:
            return self._fallback.update_account(account_id, name, description)
        
        try:
            result = self.db.accounts.update_one(
                {"account_id": account_id},
                {"$set": {"name": name, "description": description}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating account {account_id}: {e}")
            return False
    
    # ========== BLOG MANAGEMENT ==========
    
    def get_blogs_by_account(
        self,
        account_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get blogs for an account, optionally filtered by status."""
        if self.is_memory:
            return self._fallback.get_blogs_by_account(account_id, status, limit, offset)
        
        query = {"account_id": account_id}
        if status:
            query["status"] = status
        
        blogs = list(
            self.db.blogs.find(query)
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for blog in blogs:
            if "_id" in blog:
                blog["_id"] = str(blog["_id"])
        
        return blogs
    
    def get_blog_by_id(self, blog_id: str) -> Optional[Dict]:
        """Get a single blog by ID."""
        if self.is_memory:
            return self._fallback.get_blog_by_id(blog_id)
        
        try:
            oid = ObjectId(blog_id)
            blog = self.db.blogs.find_one({"_id": oid})
            if blog:
                blog["_id"] = str(blog["_id"])
            return blog
        except Exception as e:
            logger.error(f"Error fetching blog {blog_id}: {e}")
            return None
    
    def insert_blog(self, blog_data: Dict) -> str:
        """Insert a new blog and return its ID."""
        if self.is_memory:
            return self._fallback.insert_blog(blog_data)
        
        blog_data["created_at"] = datetime.now(timezone.utc).isoformat()
        blog_data["status"] = "draft"
        blog_data["posted_at"] = None
        blog_data["views"] = 0
        
        result = self.db.blogs.insert_one(blog_data)
        return str(result.inserted_id)
    
    def update_blog(self, blog_id: str, update_data: Dict) -> bool:
        """Update blog data."""
        if self.is_memory:
            return self._fallback.update_blog(blog_id, update_data)
        
        try:
            oid = ObjectId(blog_id)
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            result = self.db.blogs.update_one(
                {"_id": oid},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating blog {blog_id}: {e}")
            return False
    
    def mark_blog_posted(self, blog_id: str) -> bool:
        """Mark a blog as posted."""
        return self.update_blog(
            blog_id,
            {
                "status": "posted",
                "posted_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def delete_blog(self, blog_id: str) -> bool:
        """Delete a blog."""
        if self.is_memory:
            return self._fallback.delete_blog(blog_id)
        
        try:
            oid = ObjectId(blog_id)
            result = self.db.blogs.delete_one({"_id": oid})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting blog {blog_id}: {e}")
            return False
    
    def count_blogs_by_status(self, account_id: str) -> Dict[str, int]:
        """Count blogs by status for an account."""
        if self.is_memory:
            return self._fallback.count_blogs_by_status(account_id)
        
        result = self.db.blogs.aggregate([
            {"$match": {"account_id": account_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ])
        
        return {item["_id"]: item["count"] for item in result}
    
    # ========== GENERATION HISTORY ==========
    
    def log_generation(self, account_id: str, generated_count: int, error: Optional[str] = None) -> None:
        """Log a generation cycle."""
        if self.is_memory:
            return self._fallback.log_generation(account_id, generated_count, error)
        
        self.db.generation_history.insert_one({
            "account_id": account_id,
            "generated_count": generated_count,
            "error": error,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        
        # Update account's last generation time and blog count
        if error is None:
            self.db.accounts.update_one(
                {"account_id": account_id},
                {
                    "$set": {"last_generation": datetime.now(timezone.utc).isoformat()},
                    "$inc": {"blog_count": generated_count}
                }
            )
    
    def get_generation_history(self, account_id: str, limit: int = 10) -> List[Dict]:
        """Get generation history for an account."""
        if self.is_memory:
            return self._fallback.get_generation_history(account_id, limit)
        
        return list(
            self.db.generation_history.find(
                {"account_id": account_id},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
        )
    
    # ========== BULK OPERATIONS ==========
    
    def get_dashboard_summary(self, account_id: str) -> Dict:
        """Get dashboard summary for an account."""
        if self.is_memory:
            return self._fallback.get_dashboard_summary(account_id)
        
        account = self.get_account(account_id)
        if not account:
            return {}
        
        status_counts = self.count_blogs_by_status(account_id)
        
        # Get blogs by topic
        topic_counts = list(self.db.blogs.aggregate([
            {"$match": {"account_id": account_id}},
            {"$group": {"_id": "$topic", "count": {"$sum": 1}}}
        ]))
        
        # Get recent blogs
        recent_blogs = self.get_blogs_by_account(account_id, limit=5)
        
        # Filter out None topic keys for JSON serialization
        blogs_by_topic = {str(item["_id"]): item["count"] for item in topic_counts if item["_id"] is not None}
        
        return {
            "account": account,
            "total_blogs": account.get("blog_count", 0),
            "posted_blogs": status_counts.get("posted", 0),
            "draft_blogs": status_counts.get("draft", 0),
            "status_breakdown": status_counts,
            "blogs_by_topic": blogs_by_topic,
            "recent_blogs": recent_blogs,
        }
