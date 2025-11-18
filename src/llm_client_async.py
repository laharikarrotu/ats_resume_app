"""
Async LLM Client: Parallel OpenAI calls for faster resume generation.

This module provides async versions of LLM functions for parallel execution.
This can reduce generation time by 50-70%!
"""

import asyncio
import json
from typing import List, Optional, Tuple

from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

from .utils import deduplicate_preserve_order, normalize_keyword
from .models import Experience, Project

# Load environment variables
load_dotenv()

# Initialize async OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def extract_keywords_async(job_description: str) -> List[str]:
    """Async version of extract_keywords."""
    if not async_client:
        from .llm_client import _fallback_keyword_extraction
        return _fallback_keyword_extraction(job_description)
    
    prompt = f"""You are an ATS (Applicant Tracking System) optimization expert.

Extract 20-40 of the most important skills, technologies, tools, frameworks, and domain-specific keywords from the following job description.

Focus on:
- Programming languages (Python, Java, JavaScript, etc.)
- Frameworks and libraries (FastAPI, React, TensorFlow, etc.)
- Tools and platforms (AWS, Docker, Kubernetes, etc.)
- Methodologies (Agile, Scrum, CI/CD, etc.)
- Domain-specific terms (ML, LLM, Full-Stack, etc.)

Return ONLY a JSON array of strings, no explanation, no markdown formatting.

Job Description:
\"\"\"
{job_description}
\"\"\"

JSON array:"""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts keywords from job descriptions. Always return valid JSON arrays."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=500,
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Clean up
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        # Parse JSON
        try:
            keywords = json.loads(raw_output)
            if isinstance(keywords, list):
                normalized = [normalize_keyword(str(k)) for k in keywords if k]
                return deduplicate_preserve_order(normalized)[:50]
        except json.JSONDecodeError:
            keywords = [line.strip("-• ").strip() for line in raw_output.splitlines() if line.strip()]
            normalized = [normalize_keyword(k) for k in keywords if k]
            return deduplicate_preserve_order(normalized)[:50]
    
    except Exception as e:
        print(f"OpenAI API error: {e}. Falling back to basic keyword extraction.")
        from .llm_client import _fallback_keyword_extraction
        return _fallback_keyword_extraction(job_description)
    
    return []


async def rewrite_experience_bullets_async(
    experience: Experience,
    job_description: str,
    keywords: List[str]
) -> List[str]:
    """Async version of rewrite_experience_bullets."""
    if not async_client:
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    if not experience.bullets:
        return []
    
    original_bullets = "\n".join([f"- {bullet}" for bullet in experience.bullets])
    keywords_str = ", ".join(keywords[:20])
    
    prompt = f"""You are a resume optimization expert. Rewrite the following work experience bullet points to better match the job description.

Requirements:
1. Use STAR format (Situation, Task, Action, Result) when possible
2. Naturally incorporate these keywords: {keywords_str}
3. Quantify achievements with numbers/metrics when possible
4. Keep each bullet point concise (1-2 lines)
5. Focus on impact and results
6. Match the tone and terminology from the job description

Job Title: {experience.title}
Company: {experience.company}
Job Description Context:
\"\"\"
{job_description[:1000]}
\"\"\"

Original Bullet Points:
{original_bullets}

Return ONLY a JSON array of rewritten bullet points (strings), no explanation, no markdown.

JSON array:"""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a resume optimization expert. Always return valid JSON arrays of bullet points."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=800,
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Clean up
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        # Parse JSON
        try:
            rewritten_bullets = json.loads(raw_output)
            if isinstance(rewritten_bullets, list):
                return [str(bullet).strip() for bullet in rewritten_bullets if bullet][:5]
        except json.JSONDecodeError:
            bullets = [line.strip("-• ").strip() for line in raw_output.splitlines() if line.strip()]
            return bullets[:5]
    
    except Exception as e:
        print(f"OpenAI API error during bullet rewriting: {e}. Using original bullets.")
        from .llm_client import _inject_keywords_into_bullets
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    return experience.bullets


async def match_experience_with_jd_async(
    experiences: List[Experience],
    job_description: str,
    top_n: int = 3
) -> List[Experience]:
    """Async version of match_experience_with_jd."""
    if not async_client or len(experiences) <= top_n:
        return experiences[:top_n]
    
    experience_summaries = []
    for i, exp in enumerate(experiences):
        summary = f"{i}. {exp.title} at {exp.company}: {', '.join(exp.bullets[:2])}"
        experience_summaries.append(summary)
    
    prompt = f"""You are a resume optimization expert. Analyze the following work experiences and rank them by relevance to the job description.

Job Description:
\"\"\"
{job_description[:1500]}
\"\"\"

Work Experiences:
{chr(10).join(experience_summaries)}

Return ONLY a JSON array of indices (0-based) in order of relevance (most relevant first), no explanation.

Example: [2, 0, 1] means experience #2 is most relevant, then #0, then #1.

JSON array:"""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a resume optimization expert. Always return valid JSON arrays of indices."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=200,
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Clean up
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        # Parse indices
        try:
            indices = json.loads(raw_output)
            if isinstance(indices, list) and all(isinstance(i, int) for i in indices):
                ranked_experiences = [experiences[i] for i in indices if 0 <= i < len(experiences)]
                for i, exp in enumerate(experiences):
                    if exp not in ranked_experiences:
                        ranked_experiences.append(exp)
                return ranked_experiences[:top_n]
        except (json.JSONDecodeError, IndexError, ValueError):
            pass
    
    except Exception as e:
        print(f"OpenAI API error during experience matching: {e}. Using original order.")
    
    return experiences[:top_n]


async def rewrite_project_description_async(
    project: Project,
    job_description: str,
    keywords: List[str]
) -> str:
    """Async version of rewrite_project_description."""
    if not async_client or not project.description:
        return project.description
    
    keywords_str = ", ".join(keywords[:20])
    
    prompt = f"""You are a resume optimization expert. Rewrite the following project description to better match the job description.

Requirements:
1. Keep the project name and technologies unchanged (only rewrite the description)
2. Naturally incorporate these keywords: {keywords_str}
3. Highlight aspects relevant to the job role
4. Keep it concise (2-3 sentences max)
5. Focus on impact and technical achievements
6. Match the tone and terminology from the job description

Project Name: {project.name}
Technologies: {', '.join(project.technologies[:10])}
Job Description Context:
\"\"\"
{job_description[:1000]}
\"\"\"

Original Description:
{project.description}

Return ONLY the rewritten description text, no explanation, no markdown, no quotes."""

    try:
        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a resume optimization expert. Return only the rewritten project description text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )
        
        rewritten = response.choices[0].message.content.strip()
        
        # Remove quotes
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1]
        if rewritten.startswith("'") and rewritten.endswith("'"):
            rewritten = rewritten[1:-1]
        
        return rewritten[:200]
    
    except Exception as e:
        print(f"OpenAI API error during project rewriting: {e}. Using original description.")
        return project.description


async def prepare_resume_data_parallel(
    resume_data: Optional,
    job_description: str,
    keywords: List[str]
) -> Tuple[List[Experience], List[Project]]:
    """
    Prepare resume data with parallel LLM calls for maximum speed.
    
    This function runs multiple LLM calls in parallel:
    - Experience matching
    - Bullet rewriting for each experience
    - Project description rewriting
    
    Returns:
        Tuple of (prioritized_experiences, personalized_projects)
    """
    if not resume_data:
        return [], []
    
    # Prioritize experiences (single call)
    if job_description and len(resume_data.experience) > 3:
        prioritized_experiences = await match_experience_with_jd_async(
            resume_data.experience,
            job_description,
            top_n=4
        )
    else:
        prioritized_experiences = resume_data.experience[:4]
    
    # Create parallel tasks for bullet rewriting
    bullet_tasks = []
    for exp in prioritized_experiences[:4]:  # Limit to top 4
        task = rewrite_experience_bullets_async(exp, job_description, keywords)
        bullet_tasks.append(task)
    
    # Create parallel tasks for project rewriting
    project_tasks = []
    for project in resume_data.projects[:4]:  # Limit to top 4
        task = rewrite_project_description_async(project, job_description, keywords)
        project_tasks.append(task)
    
    # Execute all tasks in parallel
    rewritten_bullets_list, rewritten_project_descriptions = await asyncio.gather(
        asyncio.gather(*bullet_tasks),
        asyncio.gather(*project_tasks)
    )
    
    # Update experiences with rewritten bullets
    for i, exp in enumerate(prioritized_experiences):
        if i < len(rewritten_bullets_list):
            exp.bullets = rewritten_bullets_list[i]
    
    # Update projects with rewritten descriptions
    personalized_projects = []
    for i, project in enumerate(resume_data.projects[:4]):
        if i < len(rewritten_project_descriptions):
            project.description = rewritten_project_descriptions[i]
        personalized_projects.append(project)
    
    return prioritized_experiences, personalized_projects

