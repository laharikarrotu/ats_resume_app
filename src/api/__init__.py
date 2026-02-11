"""
API package — FastAPI route handlers.

Collects all routers into a single `router` that main.py includes.
"""

from fastapi import APIRouter

from .upload import router as upload_router
from .analyze import router as analyze_router
from .generate import router as generate_router
from .validate import router as validate_router
from .misc import router as misc_router

router = APIRouter()
router.include_router(upload_router)
router.include_router(analyze_router)
router.include_router(generate_router)
router.include_router(validate_router)
router.include_router(misc_router)

__all__ = ["router"]
