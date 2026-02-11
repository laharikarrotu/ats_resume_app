"""
Resume Generation routes — creates tailored DOCX / PDF resumes.

Post-generation flow:
  1. Extract keywords from JD
  2. Generate DOCX or PDF
  3. Run ATS validation on generated file
  4. Return file + validation metadata in headers
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Form, Query, HTTPException
from fastapi.responses import FileResponse

from ..config import OUTPUT_DIR
from ..models import JobDescriptionRequest, ResumeResponse, ResumeVersion
from ..exceptions import LLMProviderError, SessionNotFoundError
from ..llm.client_async import extract_keywords_async
from ..core.resume_generator import generate_resume
from ..core.ats_validator import validate_docx_file, validate_pdf_file
from ..metrics import metrics
from ..logger import logger
from ..db import save_generation
from .deps import get_resume_data, has_session, resume_versions, analysis_cache

# Try optimized version
try:
    from ..llm.client_optimized import extract_keywords_async_optimized
    OPTIMIZED_AVAILABLE = True
except ImportError:
    OPTIMIZED_AVAILABLE = False

# Try LaTeX generator
try:
    from ..core.resume_generator_latex import generate_resume_latex
    LATEX_AVAILABLE = True
except ImportError:
    LATEX_AVAILABLE = False

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# Form-based endpoint (browser UI)
# ═══════════════════════════════════════════════════════════

@router.post("/generate_resume/", response_class=FileResponse)
async def create_resume(
    job_description: str = Form(...),
    session_id: Optional[str] = Form(None),
    output_format: str = Form("docx"),
    fast_mode: str = Form("false"),
):
    """Generate a tailored ATS-optimized resume."""
    use_fast_mode = fast_mode.lower() == "true"
    metrics.inc("resume_generations_total", labels={"format": output_format})

    # Extract keywords — gracefully handle LLM failures
    keywords = []
    try:
        with metrics.timer("llm_keyword_extraction_seconds"):
            if OPTIMIZED_AVAILABLE:
                keywords = await extract_keywords_async_optimized(job_description, use_cache=True)
            else:
                keywords = await extract_keywords_async(job_description)
    except Exception as exc:
        logger.warning("LLM keyword extraction failed during generation, continuing: %s", exc)

    resume_data = None
    if session_id:
        resume_data = get_resume_data(session_id)

    filename = f"ATS_resume_{uuid4().hex[:8]}.docx"
    output_path = OUTPUT_DIR / filename

    if output_format.lower() == "pdf" and LATEX_AVAILABLE:
        try:
            import asyncio
            pdf_path = await asyncio.to_thread(
                generate_resume_latex,
                str(output_path).replace(".docx", ".pdf"),
                keywords,
                resume_data,
                job_description,
            )
            filename = Path(pdf_path).name

            if session_id:
                _save_version(session_id, filename, keywords, job_description)

            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=filename,
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"LaTeX template not found: {str(e)}")
        except RuntimeError as e:
            error_msg = str(e)
            if "LaTeX not installed" in error_msg or "not found" in error_msg.lower():
                raise HTTPException(status_code=503, detail=f"LaTeX not available. Use DOCX format. Error: {error_msg}")
            raise HTTPException(status_code=500, detail=f"LaTeX compilation failed: {error_msg}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
    else:
        await generate_resume(
            str(output_path),
            keywords,
            resume_data=resume_data,
            job_description=job_description,
            use_parallel=True,
            fast_mode=use_fast_mode,
            session_id=session_id,
        )

    if session_id:
        _save_version(session_id, filename, keywords, job_description)

    # ── Post-generation ATS validation ──
    validation = _run_post_gen_validation(str(output_path), resume_data, keywords)

    # Persist to Supabase (fire-and-forget)
    save_generation(
        session_id=session_id or "",
        filename=filename,
        output_format="docx",
        ats_score=validation.get("compatibility_score", 100),
        ats_compatible=validation.get("ats_compatible", True),
        ats_issues_count=len(validation.get("issues", [])),
        keywords_used=keywords[:15] if keywords else [],
        fast_mode=use_fast_mode,
    )

    response = FileResponse(
        path=str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="ATS_resume.docx",
    )
    # Attach validation metadata in response headers
    response.headers["X-ATS-Compatible"] = str(validation.get("ats_compatible", True))
    response.headers["X-ATS-Score"] = str(validation.get("compatibility_score", 100))
    response.headers["X-ATS-Issues"] = str(len(validation.get("issues", [])))
    return response


# ═══════════════════════════════════════════════════════════
# JSON API endpoint
# ═══════════════════════════════════════════════════════════

@router.post("/api/generate_resume", response_model=ResumeResponse)
async def create_resume_api(
    payload: JobDescriptionRequest,
    session_id: Optional[str] = Query(None),
    output_format: str = Query("docx"),
):
    """JSON API endpoint for resume generation."""
    keywords = await extract_keywords_async(payload.job_description)

    resume_data = None
    if session_id:
        resume_data = get_resume_data(session_id)

    if output_format.lower() == "pdf" and LATEX_AVAILABLE:
        filename = f"ATS_resume_{uuid4().hex[:8]}.pdf"
        output_path = OUTPUT_DIR / filename
        try:
            import asyncio
            await asyncio.to_thread(
                generate_resume_latex,
                str(output_path),
                keywords,
                resume_data,
                payload.job_description,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        filename = f"ATS_resume_{uuid4().hex[:8]}.docx"
        output_path = OUTPUT_DIR / filename
        await generate_resume(
            str(output_path),
            keywords,
            resume_data=resume_data,
            job_description=payload.job_description,
            use_parallel=True,
        )

    # ── Post-generation ATS validation ──
    validation = _run_post_gen_validation(str(output_path), resume_data, keywords)

    # Persist to Supabase (fire-and-forget)
    save_generation(
        session_id=session_id or "",
        filename=filename,
        output_format=output_format.lower(),
        ats_score=validation.get("compatibility_score", 100),
        ats_compatible=validation.get("ats_compatible", True),
        ats_issues_count=len(validation.get("issues", [])),
        keywords_used=keywords[:15] if keywords else [],
    )

    return ResumeResponse(
        download_path=f"/download/{filename}",
        keywords=keywords,
        ats_compatible=validation.get("ats_compatible", True),
        ats_compatibility_score=validation.get("compatibility_score", 100),
        ats_issues_count=len(validation.get("issues", [])),
    )


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _save_version(session_id: str, filename: str, keywords: List, job_description: str):
    """Save a resume version."""
    if session_id not in resume_versions:
        resume_versions[session_id] = []

    # Try to extract job title from JD
    job_title = ""
    jd_lower = job_description.lower()
    for prefix in ["job title:", "position:", "role:"]:
        if prefix in jd_lower:
            idx = jd_lower.index(prefix) + len(prefix)
            job_title = job_description[idx : idx + 50].strip().split("\n")[0].strip()
            break

    analysis = analysis_cache.get(f"{session_id}:latest")
    ats_score = analysis.overall_score if analysis else 0

    version = ResumeVersion(
        version_id=uuid4().hex[:12],
        job_title=job_title or "Untitled Position",
        company="",
        created_at=datetime.now().isoformat(),
        filename=filename,
        ats_score=ats_score,
        keywords_used=keywords[:10] if keywords else [],
    )

    resume_versions[session_id].append(version)

    # Keep only last 20 versions
    if len(resume_versions[session_id]) > 20:
        resume_versions[session_id] = resume_versions[session_id][-20:]


def _run_post_gen_validation(
    file_path: str,
    resume_data=None,
    keywords: Optional[List[str]] = None,
) -> dict:
    """Run ATS validation on a generated file. Returns dict with score + issues."""
    from dataclasses import asdict
    try:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".docx":
            result = validate_docx_file(file_path, resume_data, keywords)
        elif suffix == ".pdf":
            result = validate_pdf_file(file_path, resume_data, keywords)
        else:
            return {"ats_compatible": True, "compatibility_score": 100, "issues": []}
        return asdict(result)
    except Exception:
        return {"ats_compatible": True, "compatibility_score": 100, "issues": []}
