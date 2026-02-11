"""
Cover Letter Generator: Creates personalized cover letters based on resume + job description.

Uses LLM to generate tailored cover letters that:
- Reference specific achievements from the resume
- Address key requirements from the job description
- Maintain professional tone
- Include relevant keywords
"""

import json
import os
from typing import List, Optional

from ..models import ResumeData, CoverLetterResponse
from ..llm.provider import async_client, ASYNC_MODEL as MODEL


async def generate_cover_letter(
    resume_data: ResumeData,
    job_description: str,
    keywords: List[str],
    company_name: str = "",
    job_title: str = "",
    tone: str = "professional",
) -> CoverLetterResponse:
    """
    Generate a personalized cover letter using LLM.

    Args:
        resume_data: Parsed resume data
        job_description: Target job description
        keywords: Extracted keywords
        company_name: Target company name
        job_title: Target job title
        tone: 'professional', 'enthusiastic', or 'conversational'

    Returns:
        CoverLetterResponse with generated letter and metadata
    """
    # Build resume context
    experience_summary = ""
    for exp in resume_data.experience[:3]:
        bullets_text = "; ".join(exp.bullets[:3])
        experience_summary += f"- {exp.title} at {exp.company} ({exp.dates}): {bullets_text}\n"

    projects_summary = ""
    for proj in resume_data.projects[:2]:
        projects_summary += f"- {proj.name}: {proj.description[:150]}\n"

    skills_flat = []
    for skills_list in resume_data.skills.values():
        skills_flat.extend(skills_list)
    skills_text = ", ".join(skills_flat[:20])

    certs_text = ", ".join(c.name for c in resume_data.certifications) if resume_data.certifications else "None"

    tone_instruction = {
        "professional": "Use a formal, professional tone suitable for corporate applications.",
        "enthusiastic": "Use an enthusiastic, energetic tone that shows genuine excitement for the role.",
        "conversational": "Use a warm, conversational yet professional tone that feels personable.",
    }.get(tone, "Use a professional tone.")

    prompt = f"""Write a compelling cover letter for a job application. 

APPLICANT DETAILS:
- Name: {resume_data.name}
- Location: {resume_data.location}
- Email: {resume_data.email}

KEY EXPERIENCE:
{experience_summary}

NOTABLE PROJECTS:
{projects_summary}

KEY SKILLS: {skills_text}
CERTIFICATIONS: {certs_text}

TARGET JOB:
- Company: {company_name or 'the company'}
- Position: {job_title or 'the position'}
- Job Description:
\"\"\"{job_description[:1500]}\"\"\"

IMPORTANT KEYWORDS TO INCORPORATE: {', '.join(keywords[:15])}

REQUIREMENTS:
1. {tone_instruction}
2. Keep it 250-350 words (3-4 paragraphs)
3. Opening: Express interest in the specific role and company
4. Body: Connect 2-3 specific achievements from the resume to job requirements
5. Include relevant keywords naturally
6. Closing: Express enthusiasm and call to action
7. Do NOT include date, address headers, or signature block
8. Make it specific - reference actual projects and achievements
9. Show knowledge of the company/role
10. Focus on value the candidate brings

Return ONLY the cover letter text, no headers or formatting instructions."""

    if not async_client:
        return _generate_fallback_cover_letter(resume_data, job_description, company_name, job_title, keywords)

    try:
        response = await async_client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert cover letter writer. Write compelling, specific cover letters that connect candidate experience to job requirements. Return only the letter text."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,
        )

        cover_letter = response.choices[0].message.content.strip()

        # Clean up
        if cover_letter.startswith('"') and cover_letter.endswith('"'):
            cover_letter = cover_letter[1:-1]

        word_count = len(cover_letter.split())

        # Extract key points addressed
        key_points = []
        for kw in keywords[:10]:
            if kw.lower() in cover_letter.lower():
                key_points.append(f"Addressed: {kw}")
        for exp in resume_data.experience[:2]:
            if exp.company.lower() in cover_letter.lower():
                key_points.append(f"Referenced: {exp.title} at {exp.company}")

        return CoverLetterResponse(
            cover_letter=cover_letter,
            word_count=word_count,
            key_points=key_points[:8],
        )

    except Exception as e:
        print(f"Cover letter generation error: {e}")
        return _generate_fallback_cover_letter(resume_data, job_description, company_name, job_title, keywords)


def _generate_fallback_cover_letter(
    resume_data: ResumeData,
    job_description: str,
    company_name: str,
    job_title: str,
    keywords: List[str],
) -> CoverLetterResponse:
    """Generate a basic cover letter without LLM."""
    company = company_name or "your company"
    position = job_title or "this position"

    # Get top experience
    top_exp = resume_data.experience[0] if resume_data.experience else None
    top_project = resume_data.projects[0] if resume_data.projects else None

    skills_flat = []
    for skills_list in resume_data.skills.values():
        skills_flat.extend(skills_list)

    letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {position} role at {company}. With my background in {', '.join(skills_flat[:5])}, I am confident in my ability to make meaningful contributions to your team.

"""
    if top_exp:
        letter += f"In my role as {top_exp.title} at {top_exp.company}, I {top_exp.bullets[0].lower() if top_exp.bullets else 'gained significant experience'}. "
        if len(top_exp.bullets) > 1:
            letter += f"Additionally, I {top_exp.bullets[1].lower()}. "
        letter += "\n\n"

    if top_project:
        letter += f"I also developed {top_project.name}, where {top_project.description[:200]}. "
        letter += "\n\n"

    letter += f"I am particularly drawn to {company} and believe my skills in {', '.join(keywords[:5])} align well with your requirements. I would welcome the opportunity to discuss how my experience can benefit your team.\n\nThank you for considering my application. I look forward to hearing from you.\n\nBest regards,\n{resume_data.name}"

    return CoverLetterResponse(
        cover_letter=letter,
        word_count=len(letter.split()),
        key_points=[f"Mentioned: {kw}" for kw in keywords[:5]],
    )
