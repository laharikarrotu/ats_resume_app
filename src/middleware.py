"""
FastAPI middleware — rate limiting, request logging, CORS helpers.
"""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logger import logger


# ═══════════════════════════════════════════════════════════
# IP-based Sliding-Window Rate Limiter
# ═══════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Lightweight in-memory rate limiter (sliding window per IP).

    Parameters:
        max_requests:   Max allowed requests within the window.
        window_seconds: Length of the sliding window.
        exclude_paths:  Paths that should never be rate-limited (health checks, static).
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
        # ip -> list of request timestamps
        self._hits: Dict[str, List[float]] = defaultdict(list)

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
        # Garbage-collect empty entries periodically
        if not self._hits[ip]:
            del self._hits[ip]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.time()
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

        # Skip noisy static / health logs
        path = request.url.path
        if path.startswith("/static") or path == "/health":
            return response

        logger.info(
            "%s %s → %s (%.1fms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
            extra={"endpoint": path, "duration_ms": duration_ms},
        )

        return response
