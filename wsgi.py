"""WSGI entry point for production deployment."""

import sys
from pathlib import Path

# Add blog_platform to Python path
sys.path.insert(0, str(Path(__file__).parent / "blog_platform"))

from app import app

if __name__ == "__main__":
    app.run()
