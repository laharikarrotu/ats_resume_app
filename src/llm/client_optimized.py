"""
Optimized LLM Client: Smart skipping, caching, and fast mode for GPT-like speed (2-5 seconds).

Key optimizations:
1. Smart skipping — Skip unnecessary LLM calls if content already matches
2. Caching — Cache expensive operations for repeat calls
3. Fast mode — Skip rewriting, just inject keywords
4. Expert ATS prompts — Short but powerful prompt variants
5. Reduced calls — Only process top 2-3 items
"""

import asyncio
import json
from typing import List, Optional, Tuple

from ..utils import deduplicate_preserve_order, normalize_keyword
from ..models import Experience, Project, ResumeData
from ..core.cache import cache_get, cache_set, cache_keywords, cache_resume_rewrite
from .prompts import (
    KEYWORD_EXTRACTION_SYSTEM,
    KEYWORD_EXTRACTION_PROMPT_SHORT,
    BULLET_REWRITE_SYSTEM,
    BULLET_REWRITE_PROMPT_SHORT,
    PROJECT_REWRITE_SYSTEM,
    PROJECT_REWRITE_PROMPT_SHORT,
    EXPERIENCE_RANK_SYSTEM,
    EXPERIENCE_RANK_PROMPT_SHORT,
)
from .provider import async_client, ASYNC_MODEL as MODEL


def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


def _bullets_contain_keywords(bullets: List[str], keywords: List[str]) -> bool:
    """Check if bullets already contain enough keywords (skip rewriting if true)."""
    if not bullets or not keywords:
        return False
    
    bullets_text = " ".join(bullets).lower()
    keywords_lower = [k.lower() for k in keywords[:10]]
    
    matches = sum(1 for keyword in keywords_lower if keyword in bullets_text)
    
    # If 30%+ keywords are present, skip rewriting
    return matches >= len(keywords_lower) * 0.3


async def extract_keywords_async_optimized(job_description: str, use_cache: bool = True) -> List[str]:
    """Optimized keyword extraction with caching and expert ATS prompt."""
    # Check cache first
    if use_cache:
        cache_key = cache_keywords(job_description)
        cached = cache_get(cache_key)
        if cached is not None:
            return cached
    
    if not async_client:
        from .llm_client import _fallback_keyword_extraction
        return _fallback_keyword_extraction(job_description)
    
    user_prompt = KEYWORD_EXTRACTION_PROMPT_SHORT.format(
        job_description=job_description[:800]
    )

    try:
        response = await async_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": KEYWORD_EXTRACTION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=300,
        )
        
        content = _clean_json_response(response.choices[0].message.content.strip())
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                keywords = data.get("keywords", data.get("skills", []))
                if not isinstance(keywords, list):
                    keywords = []
                    for v in data.values():
                        if isinstance(v, list):
                            keywords.extend(v)
            else:
                keywords = data if isinstance(data, list) else []
            
            normalized = [normalize_keyword(str(k)) for k in keywords if k]
            result = deduplicate_preserve_order(normalized)[:40]
            
            if use_cache:
                cache_set(cache_key, result)
            
            return result
        except json.JSONDecodeError:
            keywords = [line.strip("-• ").strip() for line in content.splitlines() if line.strip()]
            normalized = [normalize_keyword(k) for k in keywords if k]
            result = deduplicate_preserve_order(normalized)[:40]
            if use_cache:
                cache_set(cache_key, result)
            return result
    
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        from .llm_client import _fallback_keyword_extraction
        return _fallback_keyword_extraction(job_description)
    
    return []


async def rewrite_experience_bullets_optimized(
    experience: Experience,
    job_description: str,
    keywords: List[str],
    fast_mode: bool = False,
    session_id: Optional[str] = None
) -> List[str]:
    """Optimized bullet rewriting with smart skipping, caching, and expert ATS prompt."""
    if not experience.bullets:
        return []
    
    # FAST MODE: Just inject keywords, no LLM call
    if fast_mode:
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    # SMART SKIP: If bullets already contain keywords, skip rewriting
    if _bullets_contain_keywords(experience.bullets, keywords):
        return experience.bullets
    
    # Check cache
    if session_id:
        cache_key = cache_resume_rewrite(session_id, job_description, f"bullets:{experience.title}")
        cached = cache_get(cache_key)
        if cached is not None:
            return cached
    
    if not async_client:
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    user_prompt = BULLET_REWRITE_PROMPT_SHORT.format(
        keywords=", ".join(keywords[:15]),
        job_description=job_description[:600],
        title=experience.title,
        bullets="\n".join(f"- {b}" for b in experience.bullets[:5]),
    )

    try:
        response = await async_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": BULLET_REWRITE_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500,
        )
        
        content = _clean_json_response(response.choices[0].message.content.strip())
        try:
            data = json.loads(content)
            if isinstance(data, list):
                bullets = data
            elif isinstance(data, dict):
                bullets = data.get("bullets", data.get("points", []))
            else:
                bullets = []
            if isinstance(bullets, list):
                result = [str(b).strip() for b in bullets if b][:6]
                if session_id:
                    cache_set(cache_key, result)
                return result
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
        
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    except Exception as e:
        print(f"Bullet rewriting error: {e}")
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)


async def rewrite_project_description_optimized(
    project: Project,
    job_description: str,
    keywords: List[str],
    fast_mode: bool = False,
    session_id: Optional[str] = None
) -> str:
    """Optimized project rewriting with smart skipping and expert ATS prompt."""
    if not project.description:
        return ""
    
    if fast_mode:
        return project.description
    
    # SMART SKIP: If description already contains keywords
    desc_lower = project.description.lower()
    keywords_lower = [k.lower() for k in keywords[:10]]
    if sum(1 for k in keywords_lower if k in desc_lower) >= 3:
        return project.description
    
    # Check cache
    if session_id:
        cache_key = cache_resume_rewrite(session_id, job_description, f"project:{project.name}")
        cached = cache_get(cache_key)
        if cached is not None:
            return cached
    
    if not async_client:
        return project.description
    
    user_prompt = PROJECT_REWRITE_PROMPT_SHORT.format(
        keywords=", ".join(keywords[:15]),
        job_description=job_description[:600],
        project_name=project.name,
        description=project.description[:200],
    )

    try:
        response = await async_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROJECT_REWRITE_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        
        rewritten = response.choices[0].message.content.strip()
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1]
        if rewritten.startswith("'") and rewritten.endswith("'"):
            rewritten = rewritten[1:-1]
        
        result = rewritten[:250]
        if session_id:
            cache_set(cache_key, result)
        return result
    
    except Exception as e:
        print(f"Project rewriting error: {e}")
        return project.description


async def match_experience_with_jd_optimized(
    experiences: List[Experience],
    job_description: str,
    top_n: int = 3,
    fast_mode: bool = False
) -> List[Experience]:
    """Optimized experience matching with smart skipping and expert ATS prompt."""
    if fast_mode or len(experiences) <= top_n:
        return experiences[:top_n]
    
    if not async_client:
        return experiences[:top_n]
    
    summaries = [
        f"{i}. {exp.title} at {exp.company} ({exp.dates})"
        for i, exp in enumerate(experiences)
    ]
    user_prompt = EXPERIENCE_RANK_PROMPT_SHORT.format(
        job_description=job_description[:800],
        experience_summaries="\n".join(summaries),
    )

    try:
        response = await async_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": EXPERIENCE_RANK_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=100,
        )
        
        content = _clean_json_response(response.choices[0].message.content.strip())
        try:
            data = json.loads(content)
            if isinstance(data, list):
                indices = data
            elif isinstance(data, dict):
                indices = data.get("indices", data.get("ranked", []))
            else:
                indices = []
            if isinstance(indices, list) and all(isinstance(i, int) for i in indices):
                ranked = [experiences[i] for i in indices if 0 <= i < len(experiences)]
                for exp in experiences:
                    if exp not in ranked:
                        ranked.append(exp)
                return ranked[:top_n]
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            pass
    
    except Exception as e:
        print(f"Experience matching error: {e}")
    
    return experiences[:top_n]


async def prepare_resume_data_optimized(
    resume_data: Optional[ResumeData],
    job_description: str,
    keywords: List[str],
    fast_mode: bool = False,
    session_id: Optional[str] = None,
    max_experiences: int = 3,
    max_projects: int = 3
) -> Tuple[List[Experience], List[Project]]:
    """
    OPTIMIZED: Prepare resume data with smart skipping, caching, and expert ATS prompts.
    
    Key optimizations:
    - Skip matching if <= 3 experiences
    - Only process top 3 items
    - Smart skip rewriting if content is already good
    - Fast mode skips all rewriting
    - Expert ATS prompts for superior quality
    """
    if not resume_data:
        return [], []
    
    experiences_to_process = resume_data.experience[:max_experiences]
    projects_to_process = resume_data.projects[:max_projects]
    
    # SMART SKIP: Only match if many experiences
    if not fast_mode and job_description and len(resume_data.experience) > 3:
        prioritized_experiences = await match_experience_with_jd_optimized(
            resume_data.experience,
            job_description,
            top_n=max_experiences,
            fast_mode=fast_mode
        )
    else:
        prioritized_experiences = experiences_to_process
    
    # Create parallel tasks
    bullet_tasks = [
        rewrite_experience_bullets_optimized(exp, job_description, keywords, fast_mode, session_id)
        for exp in prioritized_experiences
    ]
    project_tasks = [
        rewrite_project_description_optimized(proj, job_description, keywords, fast_mode, session_id)
        for proj in projects_to_process
    ]
    
    # Execute all in parallel
    results = await asyncio.gather(*bullet_tasks, *project_tasks)
    
    rewritten_bullets_list = results[:len(bullet_tasks)]
    rewritten_project_descriptions = results[len(bullet_tasks):]
    
    for i, exp in enumerate(prioritized_experiences):
        if i < len(rewritten_bullets_list):
            exp.bullets = rewritten_bullets_list[i]
    
    personalized_projects = []
    for i, project in enumerate(projects_to_process):
        if i < len(rewritten_project_descriptions):
            project.description = rewritten_project_descriptions[i]
        personalized_projects.append(project)
    
    return prioritized_experiences, personalized_projects
