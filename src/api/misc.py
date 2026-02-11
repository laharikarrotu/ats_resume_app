"""
Miscellaneous routes — health check, versions, downloads, cover letter.
"""

from typing import Optional

from fastapi import APIRouter, Form, Query, HTTPException
from fastapi.responses import FileResponse

from ..config import OUTPUT_DIR, settings
from ..exceptions import SessionNotFoundError
from ..llm.provider import get_provider_info
from ..llm.client_async import extract_keywords_async
from ..core.cover_letter import generate_cover_letter
from .deps import resume_data_cache, resume_versions

# Try optimized version
try:
    from ..llm.client_optimized import extract_keywords_async_optimized
    OPTIMIZED_AVAILABLE = True
except ImportError:
    OPTIMIZED_AVAILABLE = False

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": settings.app_version,
        "llm": get_provider_info(),
        "rate_limit": f"{settings.rate_limit_requests} req / {settings.rate_limit_window_seconds}s",
    }


# ═══════════════════════════════════════════════════════════
# Cover Letter
# ═══════════════════════════════════════════════════════════

@router.post("/api/cover_letter")
async def create_cover_letter(
    job_description: str = Form(...),
    session_id: Optional[str] = Form(None),
    company_name: str = Form(""),
    job_title: str = Form(""),
    tone: str = Form("professional"),
):
    """Generate a personalized cover letter."""
    if not session_id or session_id not in resume_data_cache:
        raise SessionNotFoundError()

    resume_data = resume_data_cache[session_id]

    if OPTIMIZED_AVAILABLE:
        keywords = await extract_keywords_async_optimized(job_description, use_cache=True)
    else:
        keywords = await extract_keywords_async(job_description)

    result = await generate_cover_letter(
        resume_data=resume_data,
        job_description=job_description,
        keywords=keywords,
        company_name=company_name,
        job_title=job_title,
        tone=tone,
    )

    return result.model_dump()


# ═══════════════════════════════════════════════════════════
# Resume Data Preview
# ═══════════════════════════════════════════════════════════

@router.get("/api/resume_data")
async def get_resume_data(session_id: str = Query(...)):
    """Get parsed resume data for preview."""
    if session_id not in resume_data_cache:
        raise HTTPException(status_code=404, detail="No resume data found")

    data = resume_data_cache[session_id]
    return data.model_dump()


# ═══════════════════════════════════════════════════════════
# Resume Versions
# ═══════════════════════════════════════════════════════════

@router.get("/api/versions")
async def get_versions(session_id: str = Query(...)):
    """Get all saved resume versions for a session."""
    versions = resume_versions.get(session_id, [])
    return {"versions": [v.model_dump() for v in versions]}


# ═══════════════════════════════════════════════════════════
# File Downloads
# ═══════════════════════════════════════════════════════════

@router.get("/download/{filename}", response_class=FileResponse)
async def download_resume(filename: str):
    """Serve generated resume files."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = (
        "application/pdf"
        if filename.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
