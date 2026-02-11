"""
LLM Client: OpenAI integration for keyword extraction, bullet rewriting, and resume optimization.

Uses expert ATS prompts (15+ years experience) for:
  • Keyword extraction with required vs. preferred distinction
  • STAR/CAR-format bullet rewriting with action verbs + metrics
  • Experience ranking by JD relevance
  • Project description optimization
"""

import json
import os
from typing import List, Optional

from ..utils import deduplicate_preserve_order, normalize_keyword
from ..models import Experience, Project
from .prompts import (
    KEYWORD_EXTRACTION_SYSTEM,
    KEYWORD_EXTRACTION_PROMPT,
    BULLET_REWRITE_SYSTEM,
    BULLET_REWRITE_PROMPT,
    ACTION_VERBS_REFERENCE,
    PROJECT_REWRITE_SYSTEM,
    PROJECT_REWRITE_PROMPT,
    EXPERIENCE_RANK_SYSTEM,
    EXPERIENCE_RANK_PROMPT,
)
from .provider import client, MODEL


def _clean_json_response(raw: str) -> str:
    """Strip markdown code fences from LLM JSON output."""
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


# ═══════════════════════════════════════════════════════════════
# Keyword Extraction
# ═══════════════════════════════════════════════════════════════

def extract_keywords(job_description: str) -> List[str]:
    """
    Extract ATS-relevant keywords from a job description using expert prompts.
    
    Extracts 25-40 keywords covering:
      - Required technical skills
      - Preferred skills
      - Tools & platforms
      - Domain-specific terminology
      - Certifications
    
    Args:
        job_description: Raw job description text
    
    Returns:
        List of extracted keywords (deduplicated, normalized)
    """
    if not client:
        return _fallback_keyword_extraction(job_description)
    
    user_prompt = KEYWORD_EXTRACTION_PROMPT.format(job_description=job_description)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": KEYWORD_EXTRACTION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=600,
        )
        
        raw_output = _clean_json_response(response.choices[0].message.content.strip())
        
        try:
            keywords = json.loads(raw_output)
            if isinstance(keywords, list):
                normalized = [normalize_keyword(str(k)) for k in keywords if k]
                return deduplicate_preserve_order(normalized)[:50]
            elif isinstance(keywords, dict):
                # Handle {"required": [...], "preferred": [...]} format
                all_kw = []
                for category_list in keywords.values():
                    if isinstance(category_list, list):
                        all_kw.extend(category_list)
                normalized = [normalize_keyword(str(k)) for k in all_kw if k]
                return deduplicate_preserve_order(normalized)[:50]
        except json.JSONDecodeError:
            keywords = [line.strip("-• ").strip() for line in raw_output.splitlines() if line.strip()]
            normalized = [normalize_keyword(k) for k in keywords if k]
            return deduplicate_preserve_order(normalized)[:50]
    
    except Exception as e:
        print(f"OpenAI API error: {e}. Falling back to basic keyword extraction.")
        return _fallback_keyword_extraction(job_description)
    
    return []


# ═══════════════════════════════════════════════════════════════
# Bullet Rewriting
# ═══════════════════════════════════════════════════════════════

def rewrite_experience_bullets(
    experience: Experience,
    job_description: str,
    keywords: List[str]
) -> List[str]:
    """
    Rewrite experience bullet points using expert ATS prompts.
    
    Applies:
      - CAR format (Challenge-Action-Result)
      - Strong action verbs
      - Quantifiable metrics
      - JD keyword injection
    
    Args:
        experience: Experience object with original bullets
        job_description: Target job description
        keywords: Extracted keywords from job description
    
    Returns:
        List of rewritten, ATS-optimized bullet points
    """
    if not client:
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    if not experience.bullets:
        return []
    
    original_bullets = "\n".join([f"- {bullet}" for bullet in experience.bullets])
    keywords_str = ", ".join(keywords[:20])
    
    user_prompt = BULLET_REWRITE_PROMPT.format(
        action_verbs_ref=ACTION_VERBS_REFERENCE,
        keywords=keywords_str,
        title=experience.title,
        company=experience.company,
        job_description=job_description[:1200],
        bullets=original_bullets,
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": BULLET_REWRITE_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        
        raw_output = _clean_json_response(response.choices[0].message.content.strip())
        
        try:
            rewritten_bullets = json.loads(raw_output)
            if isinstance(rewritten_bullets, list):
                return [str(bullet).strip() for bullet in rewritten_bullets if bullet][:6]
            elif isinstance(rewritten_bullets, dict):
                bullets = rewritten_bullets.get("bullets", rewritten_bullets.get("points", []))
                if isinstance(bullets, list):
                    return [str(b).strip() for b in bullets if b][:6]
        except json.JSONDecodeError:
            bullets = [line.strip("-• ").strip() for line in raw_output.splitlines() if line.strip()]
            return bullets[:6]
    
    except Exception as e:
        print(f"OpenAI API error during bullet rewriting: {e}. Using original bullets with keyword injection.")
        return _inject_keywords_into_bullets(experience.bullets, keywords)
    
    return experience.bullets


# ═══════════════════════════════════════════════════════════════
# Experience Ranking
# ═══════════════════════════════════════════════════════════════

def match_experience_with_jd(
    experiences: List[Experience],
    job_description: str,
    top_n: int = 3
) -> List[Experience]:
    """
    Prioritize and select the most relevant work experiences for a job description.
    
    Uses LLM to rank by: skill overlap, industry match, role similarity, recency.
    
    Args:
        experiences: List of all work experiences
        job_description: Target job description
        top_n: Number of top experiences to return
    
    Returns:
        List of most relevant experiences (prioritized)
    """
    if not client or len(experiences) <= top_n:
        return experiences[:top_n]
    
    experience_summaries = []
    for i, exp in enumerate(experiences):
        bullets_preview = "; ".join(exp.bullets[:2]) if exp.bullets else "No details"
        summary = f"{i}. {exp.title} at {exp.company} ({exp.dates}): {bullets_preview}"
        experience_summaries.append(summary)
    
    user_prompt = EXPERIENCE_RANK_PROMPT.format(
        job_description=job_description[:1500],
        experience_summaries="\n".join(experience_summaries),
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": EXPERIENCE_RANK_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=200,
        )
        
        raw_output = _clean_json_response(response.choices[0].message.content.strip())
        
        try:
            indices = json.loads(raw_output)
            if isinstance(indices, list) and all(isinstance(i, int) for i in indices):
                ranked_experiences = [experiences[i] for i in indices if 0 <= i < len(experiences)]
                for exp in experiences:
                    if exp not in ranked_experiences:
                        ranked_experiences.append(exp)
                return ranked_experiences[:top_n]
        except (json.JSONDecodeError, IndexError, ValueError):
            pass
    
    except Exception as e:
        print(f"OpenAI API error during experience matching: {e}. Using original order.")
    
    return experiences[:top_n]


# ═══════════════════════════════════════════════════════════════
# Project Rewriting
# ═══════════════════════════════════════════════════════════════

def rewrite_project_description(
    project: Project,
    job_description: str,
    keywords: List[str]
) -> str:
    """
    Rewrite project description to match job description using expert ATS prompts.
    
    Keeps project name and technologies unchanged, only personalizes the description.
    
    Args:
        project: Project object with original description
        job_description: Target job description
        keywords: Extracted keywords from job description
    
    Returns:
        Rewritten, optimized project description
    """
    if not client or not project.description:
        return project.description
    
    keywords_str = ", ".join(keywords[:20])
    
    user_prompt = PROJECT_REWRITE_PROMPT.format(
        keywords=keywords_str,
        project_name=project.name,
        technologies=", ".join(project.technologies[:10]),
        job_description=job_description[:1000],
        description=project.description,
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROJECT_REWRITE_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=250,
        )
        
        rewritten = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1]
        if rewritten.startswith("'") and rewritten.endswith("'"):
            rewritten = rewritten[1:-1]
        
        return rewritten[:250]
    
    except Exception as e:
        print(f"OpenAI API error during project rewriting: {e}. Using original description.")
        return project.description


# ═══════════════════════════════════════════════════════════════
# Fallback / Helpers
# ═══════════════════════════════════════════════════════════════

def _fallback_keyword_extraction(job_description: str) -> List[str]:
    """Enhanced fallback keyword extraction when OpenAI is not available."""
    # Known technical skills for better matching
    KNOWN_SKILLS = {
        "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
        "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "html", "css",
        "react", "angular", "vue", "next.js", "node.js", "express", "django",
        "flask", "fastapi", "spring", "spring boot", ".net",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb",
        "kafka", "rabbitmq", "graphql", "rest", "grpc",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "jenkins", "github actions", "gitlab ci", "circleci",
        "agile", "scrum", "kanban", "ci/cd", "devops", "microservices",
        "machine learning", "deep learning", "nlp", "computer vision",
        "linux", "git", "jira", "confluence",
    }
    
    jd_lower = job_description.lower()
    
    # First pass: find known skills
    found_skills = []
    for skill in KNOWN_SKILLS:
        if skill in jd_lower:
            found_skills.append(skill)
    
    # Second pass: extract other potential keywords
    raw_tokens = [
        token.strip(",.:-;()[]{}\"'").lower()
        for token in job_description.split()
    ]
    
    stopwords = {
        "and", "or", "the", "a", "an", "to", "of", "in", "for", "on",
        "with", "at", "as", "is", "are", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "will", "would", "should",
        "could", "may", "might", "must", "can", "this", "that", "these",
        "those", "we", "you", "they", "he", "she", "it", "our", "your",
        "its", "from", "about", "into", "through", "during", "before",
        "after", "above", "below", "between", "but", "not", "only",
        "very", "just", "also", "more", "some", "any", "all", "each",
        "every", "both", "few", "than", "then", "too", "such",
        "experience", "team", "work", "position", "role", "company",
        "looking", "seeking", "opportunity", "responsibilities", "requirements",
        "preferred", "required", "qualifications", "benefits", "salary",
    }
    
    candidates = [
        t for t in raw_tokens if len(t) > 2 and t not in stopwords
    ]
    
    # Combine found skills + candidates, deduplicate
    all_keywords = found_skills + candidates
    normalized = [normalize_keyword(c) for c in all_keywords]
    return deduplicate_preserve_order(normalized)[:50]


def _inject_keywords_into_bullets(bullets: List[str], keywords: List[str]) -> List[str]:
    """Simple keyword injection fallback when OpenAI rewriting is not available."""
    if not bullets or not keywords:
        return bullets
    # Fallback: return as-is. LLM-based rewriting is always preferred.
    return bullets
