"""
ATS Resume Generator — FastAPI application entry point.

All route handlers live in src/api/; this file wires them together
with middleware, exception handling, and logging.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, TEMPLATES_DIR, STATIC_DIR
from .exceptions import AppError
from .logger import setup_logging, logger
from .middleware import RateLimitMiddleware, RequestLoggingMiddleware
from .api import router


# ═══════════════════════════════════════════════════════════
# Logging (reconfigure with validated settings)
# ═══════════════════════════════════════════════════════════

setup_logging(level=settings.log_level, json_mode=settings.log_json)


# ═══════════════════════════════════════════════════════════
# App Factory
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)


# ═══════════════════════════════════════════════════════════
# Middleware (order matters — outermost first)
# ═══════════════════════════════════════════════════════════

# 1. Request logging
app.add_middleware(RequestLoggingMiddleware)

# 2. Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

# 3. CORS (allow local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ═══════════════════════════════════════════════════════════
# Global Exception Handlers
# ═══════════════════════════════════════════════════════════

@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """
    Catch any AppError subclass and return a uniform JSON response.
    """
    logger.error("AppError %s: %s", exc.status_code, exc.detail, exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Safety net: catch anything unexpected so the client always gets JSON.
    """
    logger.critical("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ═══════════════════════════════════════════════════════════
# Static Files + Templates
# ═══════════════════════════════════════════════════════════

class CachedStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        async def send_with_cache(message):
            if message["type"] == "http.response.start":
                existing_headers = list(message.get("headers", []))
                existing_headers.append(
                    (b"cache-control", b"public, max-age=31536000, immutable")
                )
                message["headers"] = existing_headers
            await send(message)

        await super().__call__(scope, receive, send_with_cache)


app.mount("/static", CachedStaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ═══════════════════════════════════════════════════════════
# Root Page
# ═══════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": settings.app_title},
    )


# ═══════════════════════════════════════════════════════════
# Include All API Routes
# ═══════════════════════════════════════════════════════════

app.include_router(router)


# ═══════════════════════════════════════════════════════════
# Startup / Shutdown Events
# ═══════════════════════════════════════════════════════════

@app.on_event("startup")
async def on_startup():
    from .llm.provider import get_provider_info

    info = get_provider_info()
    logger.info(
        "🚀 %s v%s started — LLM: %s (fallback: %s)",
        settings.app_title,
        settings.app_version,
        info["model"],
        info["fallback_model"] or "none",
    )
    if settings.debug:
        logger.info("⚠️  Debug mode ON — /docs enabled, CORS wide-open")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Server shutting down")
