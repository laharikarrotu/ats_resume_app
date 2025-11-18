"""
LLM Client: OpenAI integration for keyword extraction and resume personalization.

This module provides:
- Keyword extraction from job descriptions
- Personalized experience bullet rewriting
- STAR format conversion
- Experience matching with job requirements
"""

import json
import os
from typing import List, Optional

from openai import OpenAI
from dotenv import load_dotenv

from .utils import deduplicate_preserve_order, normalize_keyword
from .models import Experience, Project

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def extract_keywords(job_description: str) -> List[str]:
    """
    Extract ATS-relevant keywords from a job description using OpenAI.
    
    Args:
        job_description: Raw job description text
    
    Returns:
        List of extracted keywords (skills, technologies, tools, etc.)
    """
    # If no API key, fall back to basic extraction
    if not client:
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective model
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
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=500,
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Clean up the response (remove markdown code blocks if present)
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        # Parse JSON array
        try:
            keywords = json.loads(raw_output)
            if isinstance(keywords, list):
                normalized = [normalize_keyword(str(k)) for k in keywords if k]
                return deduplicate_preserve_order(normalized)[:50]
        except json.JSONDecodeError:
            # Fallback: treat as newline-separated list
            keywords = [line.strip("-• ").strip() for line in raw_output.splitlines() if line.strip()]
            normalized = [normalize_keyword(k) for k in keywords if k]
            return deduplicate_preserve_order(normalized)[:50]
    
    except Exception as e:
        # If OpenAI call fails, fall back to basic extraction
        print(f"OpenAI API error: {e}. Falling back to basic keyword extraction.")
        return _fallback_keyword_extraction(job_description)
    
    return []


def rewrite_experience_bullets(
    experience: Experience,
    job_description: str,
    keywords: List[str]
) -> List[str]:
    """
    Rewrite experience bullet points to match job description using OpenAI.
    
    Uses STAR format (Situation, Task, Action, Result) and injects relevant keywords.
    
    Args:
        experience: Experience object with original bullets
        job_description: Target job description
        keywords: Extracted keywords from job description
    
    Returns:
        List of rewritten, optimized bullet points
    """
    if not client:
        # Fallback: return original bullets with keyword injection
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    if not experience.bullets:
        return []
    
    # Prepare context
    original_bullets = "\n".join([f"- {bullet}" for bullet in experience.bullets])
    keywords_str = ", ".join(keywords[:20])  # Limit to top 20 keywords
    
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
{job_description[:1000]}  # Limit to first 1000 chars
\"\"\"

Original Bullet Points:
{original_bullets}

Return ONLY a JSON array of rewritten bullet points (strings), no explanation, no markdown.

JSON array:"""

    try:
        response = client.chat.completions.create(
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
            temperature=0.3,  # Slightly higher for creativity
            max_tokens=800,
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Clean up response
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        # Parse JSON array
        try:
            rewritten_bullets = json.loads(raw_output)
            if isinstance(rewritten_bullets, list):
                return [str(bullet).strip() for bullet in rewritten_bullets if bullet][:5]  # Limit to 5 bullets
        except json.JSONDecodeError:
            # Fallback: treat as newline-separated
            bullets = [line.strip("-• ").strip() for line in raw_output.splitlines() if line.strip()]
            return bullets[:5]
    
    except Exception as e:
        print(f"OpenAI API error during bullet rewriting: {e}. Using original bullets with keyword injection.")
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    return experience.bullets  # Fallback to original


def match_experience_with_jd(
    experiences: List[Experience],
    job_description: str,
    top_n: int = 3
) -> List[Experience]:
    """
    Prioritize and select the most relevant work experiences for a job description.
    
    Args:
        experiences: List of all work experiences
        job_description: Target job description
        top_n: Number of top experiences to return
    
    Returns:
        List of most relevant experiences (prioritized)
    """
    if not client or len(experiences) <= top_n:
        # If no API key or already small enough, return as-is
        return experiences[:top_n]
    
    # Create a summary of all experiences
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
        response = client.chat.completions.create(
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
                # Reorder experiences based on ranking
                ranked_experiences = [experiences[i] for i in indices if 0 <= i < len(experiences)]
                # Add any missing experiences
                for i, exp in enumerate(experiences):
                    if exp not in ranked_experiences:
                        ranked_experiences.append(exp)
                return ranked_experiences[:top_n]
        except (json.JSONDecodeError, IndexError, ValueError):
            pass
    
    except Exception as e:
        print(f"OpenAI API error during experience matching: {e}. Using original order.")
    
    # Fallback: return first top_n experiences
    return experiences[:top_n]


def _fallback_keyword_extraction(job_description: str) -> List[str]:
    """Fallback keyword extraction when OpenAI is not available."""
    # Naive heuristic: split on whitespace and filter basic tokens
    raw_tokens = [
        token.strip(",.:-;()").lower()
        for token in job_description.split()
    ]
    
    stopwords = {
        "and", "or", "the", "a", "an", "to", "of", "in", "for", "on",
        "with", "at", "as", "is", "are", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "will", "would", "should",
        "could", "may", "might", "must", "can", "this", "that", "these",
        "those", "we", "you", "they", "he", "she", "it", "our", "your",
    }
    
    candidates = [
        t for t in raw_tokens if len(t) > 2 and t not in stopwords
    ]
    
    normalized = [normalize_keyword(c) for c in candidates]
    return deduplicate_preserve_order(normalized)[:50]


def rewrite_project_description(
    project: Project,
    job_description: str,
    keywords: List[str]
) -> str:
    """
    Rewrite project description to match job description using OpenAI.
    
    Keeps project name and technologies the same, only personalizes the description.
    
    Args:
        project: Project object with original description
        job_description: Target job description
        keywords: Extracted keywords from job description
    
    Returns:
        Rewritten, optimized project description
    """
    if not client or not project.description:
        # Fallback: return original description
        return project.description
    
    keywords_str = ", ".join(keywords[:20])  # Limit to top 20 keywords
    
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
        response = client.chat.completions.create(
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
        
        # Remove quotes if present
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1]
        if rewritten.startswith("'") and rewritten.endswith("'"):
            rewritten = rewritten[1:-1]
        
        return rewritten[:200]  # Limit length
    
    except Exception as e:
        print(f"OpenAI API error during project rewriting: {e}. Using original description.")
        return project.description


def _inject_keywords_into_bullets(bullets: List[str], keywords: List[str]) -> List[str]:
    """Simple keyword injection fallback when OpenAI rewriting is not available."""
    if not bullets or not keywords:
        return bullets
    
    # Simple approach: try to naturally incorporate keywords
    # This is a basic fallback - OpenAI rewriting is much better
    return bullets  # For now, return as-is. Can enhance later if needed.

