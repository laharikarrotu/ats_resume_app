"""
ATS Analysis route — scores a resume against a job description.
"""

from typing import Optional

from fastapi import APIRouter, Form, HTTPException

from ..exceptions import SessionNotFoundError
from ..llm.client import extract_keywords
from ..llm.client_async import extract_keywords_async
from ..core.ats_scorer import analyze_resume_ats
from .deps import resume_data_cache, analysis_cache

# Try optimized version (faster)
try:
    from ..llm.client_optimized import extract_keywords_async_optimized
    OPTIMIZED_AVAILABLE = True
except ImportError:
    OPTIMIZED_AVAILABLE = False

router = APIRouter()


@router.post("/api/analyze")
async def analyze_resume(
    job_description: str = Form(...),
    session_id: Optional[str] = Form(None),
):
    """
    Analyze resume against job description and return ATS score + analysis.
    Returns keyword matches, format issues, skill gaps, and recommendations.
    """
    if not session_id or session_id not in resume_data_cache:
        raise SessionNotFoundError()

    resume_data = resume_data_cache[session_id]

    # Extract keywords
    if OPTIMIZED_AVAILABLE:
        keywords = await extract_keywords_async_optimized(job_description, use_cache=True)
    else:
        keywords = await extract_keywords_async(job_description)

    # Run ATS analysis
    analysis = analyze_resume_ats(resume_data, job_description, keywords)

    # Cache analysis
    analysis_cache[f"{session_id}:latest"] = analysis

    return analysis.model_dump()
