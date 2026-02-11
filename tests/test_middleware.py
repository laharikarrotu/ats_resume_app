"""Tests for middleware — rate limiting and request logging."""

import time
from unittest.mock import MagicMock, AsyncMock

import pytest
from src.middleware import RateLimitMiddleware


class TestRateLimitMiddleware:
    def test_prune_removes_old(self):
        """Prune should remove timestamps outside the window."""
        mw = RateLimitMiddleware(app=MagicMock(), max_requests=5, window_seconds=60)
        now = time.time()
        ip = "1.2.3.4"
        # Add timestamps: 3 old + 2 recent
        mw._hits[ip] = [now - 120, now - 90, now - 70, now - 10, now - 5]
        mw._prune(ip, now)
        assert len(mw._hits[ip]) == 2  # only the two within 60s window

    def test_prune_cleans_empty(self):
        """Should garbage-collect IP entry when all timestamps are old."""
        mw = RateLimitMiddleware(app=MagicMock(), max_requests=5, window_seconds=60)
        now = time.time()
        ip = "5.6.7.8"
        mw._hits[ip] = [now - 120]  # all old
        mw._prune(ip, now)
        assert ip not in mw._hits

    def test_client_ip_forwarded(self):
        """Should extract IP from X-Forwarded-For header."""
        mw = RateLimitMiddleware(app=MagicMock())
        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
        assert mw._client_ip(request) == "10.0.0.1"

    def test_client_ip_direct(self):
        """Should use client.host when no forwarded header."""
        mw = RateLimitMiddleware(app=MagicMock())
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"
        assert mw._client_ip(request) == "192.168.1.1"

    def test_client_ip_unknown(self):
        """Should return 'unknown' when no client info."""
        mw = RateLimitMiddleware(app=MagicMock())
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert mw._client_ip(request) == "unknown"
