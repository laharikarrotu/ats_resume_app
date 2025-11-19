"""
Simple in-memory cache for expensive operations.
In production, use Redis or similar for distributed caching.
"""

from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime, timedelta

# Simple in-memory cache with TTL
_cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(hours=24)  # Cache for 24 hours


def _generate_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    # Create a hash of the arguments
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def get(key: str) -> Optional[Any]:
    """Get a value from cache if it exists and hasn't expired."""
    if key not in _cache:
        return None
    
    value, expiry = _cache[key]
    if datetime.now() > expiry:
        # Expired, remove it
        del _cache[key]
        return None
    
    return value


def set(key: str, value: Any, ttl: timedelta = CACHE_TTL) -> None:
    """Set a value in cache with TTL."""
    expiry = datetime.now() + ttl
    _cache[key] = (value, expiry)


def clear() -> None:
    """Clear all cache entries."""
    _cache.clear()


def cache_keywords(job_description: str) -> str:
    """Generate cache key for keyword extraction."""
    return f"keywords:{_generate_key(job_description)}"


def cache_resume_rewrite(session_id: str, job_description: str, content_type: str) -> str:
    """Generate cache key for resume content rewriting."""
    return f"rewrite:{session_id}:{content_type}:{_generate_key(job_description)}"

