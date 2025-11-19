"""
Optimized LLM Client: Smart skipping, caching, and fast mode for GPT-like speed (2-5 seconds).

Key optimizations:
1. Smart skipping - Skip unnecessary LLM calls
2. Caching - Cache expensive operations
3. Fast mode - Skip rewriting, just inject keywords
4. JSON response format - Faster parsing
5. Reduced calls - Only process top 2-3 items
"""

import asyncio
import json
from typing import List, Optional, Tuple

from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from .utils import deduplicate_preserve_order, normalize_keyword
from .models import Experience, Project
from .cache import get, set, cache_keywords, cache_resume_rewrite

# Load environment variables
load_dotenv()

# Initialize async OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _bullets_contain_keywords(bullets: List[str], keywords: List[str]) -> bool:
    """Check if bullets already contain enough keywords (skip rewriting if true)."""
    if not bullets or not keywords:
        return False
    
    bullets_text = " ".join(bullets).lower()
    keywords_lower = [k.lower() for k in keywords[:10]]  # Check top 10 keywords
    
    # Count how many keywords are already present
    matches = sum(1 for keyword in keywords_lower if keyword in bullets_text)
    
    # If 30%+ keywords are present, skip rewriting
    return matches >= len(keywords_lower) * 0.3


async def extract_keywords_async_optimized(job_description: str, use_cache: bool = True) -> List[str]:
    """Optimized keyword extraction with caching."""
    # Check cache first
    if use_cache:
        cache_key = cache_keywords(job_description)
        cached = get(cache_key)
        if cached is not None:
            return cached
    
    if not async_client:
        from .llm_client import _fallback_keyword_extraction
        return _fallback_keyword_extraction(job_description)
    
    # Shorter, optimized prompt
    prompt = f"""Extract 20-30 key skills/technologies from this job description. Return ONLY a JSON array.

Job: {job_description[:800]}

JSON array:"""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract keywords. Return JSON array only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=250,  # Further reduced
            # Note: response_format requires specific prompt structure, using manual parsing for now
        )
        
        # Parse JSON response
        content = response.choices[0].message.content.strip()
        try:
            data = json.loads(content)
            # Handle both {"keywords": [...]} and [...] formats
            if isinstance(data, dict):
                keywords = data.get("keywords", data.get("skills", []))
            else:
                keywords = data if isinstance(data, list) else []
            
            normalized = [normalize_keyword(str(k)) for k in keywords if k]
            result = deduplicate_preserve_order(normalized)[:40]
            
            # Cache result
            if use_cache:
                set(cache_key, result)
            
            return result
        except json.JSONDecodeError:
            # Fallback parsing
            keywords = [line.strip("-• ").strip() for line in content.splitlines() if line.strip()]
            normalized = [normalize_keyword(k) for k in keywords if k]
            result = deduplicate_preserve_order(normalized)[:40]
            if use_cache:
                set(cache_key, result)
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
    """Optimized bullet rewriting with smart skipping and caching."""
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
        cached = get(cache_key)
        if cached is not None:
            return cached
    
    if not async_client:
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    # Shorter prompt
    prompt = f"""Rewrite these bullet points to match the job. Use STAR format. Include keywords: {', '.join(keywords[:15])}

Job context: {job_description[:600]}
Title: {experience.title}
Bullets:
{chr(10).join(f'- {b}' for b in experience.bullets[:4])}

Return JSON array only."""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Rewrite bullets. Return JSON array only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400,
            # Note: response_format requires specific prompt structure, using manual parsing for now
        )
        
        content = response.choices[0].message.content.strip()
        try:
            data = json.loads(content)
            bullets = data.get("bullets", data.get("points", []))
            if isinstance(bullets, list):
                result = [str(b).strip() for b in bullets if b][:5]
                if session_id:
                    set(cache_key, result)
                return result
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Fallback
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
    """Optimized project rewriting with smart skipping."""
    if not project.description:
        return ""
    
    # FAST MODE: Skip rewriting
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
        cached = get(cache_key)
        if cached is not None:
            return cached
    
    if not async_client:
        return project.description
    
    # Shorter prompt
    prompt = f"""Rewrite this project description to match the job. Include keywords: {', '.join(keywords[:15])}

Job: {job_description[:600]}
Project: {project.name}
Description: {project.description[:200]}

Return rewritten description only (no quotes, no JSON)."""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Rewrite project description. Return text only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150,
        )
        
        rewritten = response.choices[0].message.content.strip()
        # Remove quotes
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1]
        if rewritten.startswith("'") and rewritten.endswith("'"):
            rewritten = rewritten[1:-1]
        
        result = rewritten[:200]
        if session_id:
            set(cache_key, result)
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
    """Optimized experience matching with smart skipping."""
    # FAST MODE or small list: Skip matching, just return first N
    if fast_mode or len(experiences) <= top_n:
        return experiences[:top_n]
    
    if not async_client:
        return experiences[:top_n]
    
    # Shorter prompt
    summaries = [f"{i}. {exp.title} at {exp.company}" for i, exp in enumerate(experiences)]
    prompt = f"""Rank these experiences by relevance to the job. Return JSON array of indices (0-based).

Job: {job_description[:800]}
Experiences:
{chr(10).join(summaries)}

JSON array:"""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Rank experiences. Return JSON array of indices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=100,
            # Note: response_format requires specific prompt structure, using manual parsing for now
        )
        
        content = response.choices[0].message.content.strip()
        try:
            data = json.loads(content)
            indices = data.get("indices", data.get("ranked", []))
            if isinstance(indices, list) and all(isinstance(i, int) for i in indices):
                ranked = [experiences[i] for i in indices if 0 <= i < len(experiences)]
                # Add remaining
                for exp in experiences:
                    if exp not in ranked:
                        ranked.append(exp)
                return ranked[:top_n]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
    
    except Exception as e:
        print(f"Experience matching error: {e}")
    
    return experiences[:top_n]


async def prepare_resume_data_optimized(
    resume_data: Optional,
    job_description: str,
    keywords: List[str],
    fast_mode: bool = False,
    session_id: Optional[str] = None,
    max_experiences: int = 3,  # Reduced from 4 to 3
    max_projects: int = 3  # Reduced from 4 to 3
) -> Tuple[List[Experience], List[Project]]:
    """
    OPTIMIZED: Prepare resume data with smart skipping and caching.
    
    Key optimizations:
    - Skip matching if ≤3 experiences
    - Only process top 3 (not 4)
    - Smart skip rewriting if content is good
    - Fast mode skips all rewriting
    """
    if not resume_data:
        return [], []
    
    # Limit to top N for speed
    experiences_to_process = resume_data.experience[:max_experiences]
    projects_to_process = resume_data.projects[:max_projects]
    
    # SMART SKIP: Only match if we have many experiences
    if not fast_mode and job_description and len(resume_data.experience) > 3:
        prioritized_experiences = await match_experience_with_jd_optimized(
            resume_data.experience,
            job_description,
            top_n=max_experiences,
            fast_mode=fast_mode
        )
    else:
        prioritized_experiences = experiences_to_process
    
    # Create parallel tasks (but fewer now)
    bullet_tasks = [
        rewrite_experience_bullets_optimized(exp, job_description, keywords, fast_mode, session_id)
        for exp in prioritized_experiences
    ]
    
    project_tasks = [
        rewrite_project_description_optimized(proj, job_description, keywords, fast_mode, session_id)
        for proj in projects_to_process
    ]
    
    # Execute in parallel
    results = await asyncio.gather(*bullet_tasks, *project_tasks)
    
    rewritten_bullets_list = results[:len(bullet_tasks)]
    rewritten_project_descriptions = results[len(bullet_tasks):]
    
    # Update experiences
    for i, exp in enumerate(prioritized_experiences):
        if i < len(rewritten_bullets_list):
            exp.bullets = rewritten_bullets_list[i]
    
    # Update projects
    personalized_projects = []
    for i, project in enumerate(projects_to_process):
        if i < len(rewritten_project_descriptions):
            project.description = rewritten_project_descriptions[i]
        personalized_projects.append(project)
    
    return prioritized_experiences, personalized_projects

