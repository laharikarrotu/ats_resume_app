"""
Miscellaneous routes — health, metrics, versions, downloads, cover letter, admin.
"""

from typing import Optional

from fastapi import APIRouter, Form, Query, HTTPException, Depends
from fastapi.responses import FileResponse, PlainTextResponse

from ..config import OUTPUT_DIR, settings
from ..exceptions import SessionNotFoundError
from ..llm.provider import get_provider_info
from ..llm.client_async import extract_keywords_async
from ..core.cover_letter import generate_cover_letter
from ..db import get_usage_stats, is_db_enabled
from ..metrics import metrics
from ..auth import get_api_key, get_key_stats, is_auth_enabled
from ..tasks import task_queue
from .deps import resume_data_cache, resume_versions, get_resume_data, has_session

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
        "database": "supabase" if is_db_enabled() else "in-memory",
        "auth": "api_key" if is_auth_enabled() else "open",
        "task_queue": task_queue.stats,
        "rate_limit": f"{settings.rate_limit_requests} req / {settings.rate_limit_window_seconds}s",
    }


# ═══════════════════════════════════════════════════════════
# Usage Stats (Supabase analytics)
# ═══════════════════════════════════════════════════════════

@router.get("/api/stats")
async def usage_stats():
    """Return aggregate usage stats from Supabase."""
    stats = get_usage_stats()
    stats["db_enabled"] = is_db_enabled()
    return stats


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
    if not session_id or not has_session(session_id):
        raise SessionNotFoundError()

    resume_data = get_resume_data(session_id)

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
async def get_resume_data_endpoint(session_id: str = Query(...)):
    """Get parsed resume data for preview (checks memory, then Supabase)."""
    data = get_resume_data(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="No resume data found")

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


# ═══════════════════════════════════════════════════════════
# Prometheus Metrics
# ═══════════════════════════════════════════════════════════

@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return metrics.to_prometheus()


@router.get("/api/metrics")
async def metrics_json():
    """JSON metrics for dashboards."""
    return metrics.to_dict()


# ═══════════════════════════════════════════════════════════
# Task Queue Status
# ═══════════════════════════════════════════════════════════

@router.get("/api/tasks")
async def list_tasks(status: Optional[str] = Query(None), limit: int = Query(20)):
    """List background tasks."""
    from ..tasks import TaskStatus as TS
    task_status = TS(status) if status else None
    tasks = task_queue.list_tasks(status=task_status, limit=limit)
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "status": t.status.value,
                "error": t.error,
                "duration_seconds": t.duration_seconds,
            }
            for t in tasks
        ],
        "stats": task_queue.stats,
    }


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get the status/result of a specific background task."""
    result = task_queue.get_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": result.task_id,
        "status": result.status.value,
        "result": result.result,
        "error": result.error,
        "duration_seconds": result.duration_seconds,
    }
