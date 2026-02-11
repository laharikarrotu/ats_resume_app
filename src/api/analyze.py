"""
ATS Analysis route — scores a resume against a job description.
"""

from typing import Optional

from fastapi import APIRouter, Form, HTTPException

from ..exceptions import SessionNotFoundError
from ..llm.client import extract_keywords
from ..llm.client_async import extract_keywords_async
from ..core.ats_scorer import analyze_resume_ats
from ..metrics import metrics
from ..db import save_analysis
from .deps import get_resume_data, save_analysis_data, has_session

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
    if not session_id or not has_session(session_id):
        raise SessionNotFoundError()

    resume_data = get_resume_data(session_id)

    # Extract keywords
    with metrics.timer("llm_keyword_extraction_seconds"):
        if OPTIMIZED_AVAILABLE:
            keywords = await extract_keywords_async_optimized(job_description, use_cache=True)
        else:
            keywords = await extract_keywords_async(job_description)

    # Run ATS analysis
    with metrics.timer("ats_analysis_seconds"):
        analysis = analyze_resume_ats(resume_data, job_description, keywords)
    metrics.inc("analyses_total")
    metrics.observe("ats_scores", analysis.overall_score)

    # Cache analysis (memory + Supabase)
    save_analysis_data(session_id, f"{session_id}:latest", analysis)

    # Persist to Supabase (fire-and-forget)
    save_analysis(
        session_id=session_id,
        overall_score=analysis.overall_score,
        grade=analysis.grade,
        keyword_match_pct=analysis.keyword_match_percentage,
        matched_count=len(analysis.matched_keywords),
        missing_count=len(analysis.missing_keywords),
        format_issues_count=len(analysis.format_issues),
        skill_gaps_count=len(analysis.skill_gaps),
        job_description_snippet=job_description[:500],
    )

    return analysis.model_dump()
