"""
FastAPI middleware — rate limiting (Supabase-backed), request logging, metrics.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logger import logger
from .metrics import metrics


# ═══════════════════════════════════════════════════════════
# IP-based Sliding-Window Rate Limiter (Supabase-persisted)
# ═══════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiter that persists hit counts to Supabase.

    Architecture:
      - In-memory dict is the fast-path (avoids DB query on every request)
      - Every hit is ALSO recorded in Supabase `rate_limits` table
      - On startup (fresh memory), the first request from an IP loads its
        recent hit count from Supabase, so limits survive restarts
      - Old rate_limit rows are cleaned up periodically

    Parameters:
        max_requests:   Max allowed requests within the window.
        window_seconds: Length of the sliding window.
        exclude_paths:  Paths that should never be rate-limited.
    """

    def __init__(
        self,
        app,
        max_requests: int = 30,
        window_seconds: int = 3600,
        exclude_paths: tuple = ("/health", "/static", "/", "/docs", "/openapi.json"),
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths
        # ip -> list of request timestamps (in-memory fast path)
        self._hits: Dict[str, List[float]] = defaultdict(list)
        # Track which IPs we've loaded from DB (to avoid repeated DB lookups)
        self._loaded_from_db: set = set()
        # Periodic cleanup tracker
        self._last_cleanup = time.time()
        self._cleanup_interval = 600  # Clean up DB every 10 minutes

    def _client_ip(self, request: Request) -> str:
        """Extract client IP (supports X-Forwarded-For behind a proxy)."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _prune(self, ip: str, now: float) -> None:
        """Remove timestamps older than the window."""
        cutoff = now - self.window_seconds
        self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
        # Garbage-collect empty entries
        if not self._hits[ip]:
            del self._hits[ip]
            self._loaded_from_db.discard(ip)

    def _load_from_db(self, ip: str) -> None:
        """Load hit count from Supabase for an IP we haven't seen since restart."""
        if ip in self._loaded_from_db:
            return
        self._loaded_from_db.add(ip)

        try:
            from .db import count_rate_limit_hits, is_db_enabled
            if not is_db_enabled():
                return
            since = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
            count = count_rate_limit_hits(ip, since.isoformat())
            if count > 0:
                # Backfill in-memory with approximate timestamps
                now = time.time()
                step = self.window_seconds / max(count, 1)
                for i in range(count):
                    self._hits[ip].append(now - (count - i) * step)
                logger.debug("Loaded %d rate-limit hits from DB for IP %s", count, ip)
        except Exception as exc:
            logger.debug("Rate limit DB load failed for %s: %s", ip, exc)

    def _record_hit_db(self, ip: str, path: str) -> None:
        """Persist a rate-limit hit to Supabase (fire-and-forget)."""
        try:
            from .db import record_rate_limit_hit, is_db_enabled
            if is_db_enabled():
                record_rate_limit_hit(ip, path)
        except Exception:
            pass  # Best-effort

    def _maybe_cleanup_db(self) -> None:
        """Periodically delete old rate_limit rows from Supabase."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now

        try:
            from .db import cleanup_old_rate_limits, is_db_enabled
            if not is_db_enabled():
                return
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds * 2)
            deleted = cleanup_old_rate_limits(cutoff.isoformat())
            if deleted:
                logger.info("Cleaned up %d old rate_limit rows", deleted)
        except Exception:
            pass

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.time()

        # Load from DB if first time seeing this IP since restart
        self._load_from_db(ip)

        self._prune(ip, now)

        if len(self._hits[ip]) >= self.max_requests:
            remaining_seconds = int(self.window_seconds - (now - self._hits[ip][0]))
            logger.warning(
                "Rate limit exceeded for %s — %d requests in window",
                ip,
                len(self._hits[ip]),
                extra={"endpoint": path},
            )
            return Response(
                content=f'{{"detail":"Too many requests. Try again in {remaining_seconds}s."}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(remaining_seconds)},
            )

        self._hits[ip].append(now)

        # Persist hit to Supabase
        self._record_hit_db(ip, path)

        # Periodic DB cleanup
        self._maybe_cleanup_db()

        return await call_next(request)


# ═══════════════════════════════════════════════════════════
# Request Logging Middleware
# ═══════════════════════════════════════════════════════════

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with method, path, status code, and duration.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        duration_sec = duration_ms / 1000.0

        path = request.url.path
        method = request.method
        status = str(response.status_code)

        # ── Metrics ──
        metrics.inc("http_requests_total", labels={"method": method, "path": path, "status": status})
        metrics.observe("http_request_duration_seconds", duration_sec)

        if path.startswith("/api/"):
            metrics.observe("api_request_duration_seconds", duration_sec)

        # Track active requests gauge
        if response.status_code >= 500:
            metrics.inc("http_errors_total", labels={"method": method, "path": path})

        # Skip noisy static / health logs
        if path.startswith("/static") or path.startswith("/assets") or path == "/health":
            return response

        logger.info(
            "%s %s → %s (%.1fms)",
            method,
            path,
            response.status_code,
            duration_ms,
            extra={"endpoint": path, "duration_ms": duration_ms},
        )

        return response
