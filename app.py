"""Render/WSGI entry point shim for gunicorn app:app."""

from blog_platform.app import app

__all__ = ["app"]
