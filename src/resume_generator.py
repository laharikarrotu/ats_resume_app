"""
Enhanced Resume Generator: Creates ATS-optimized resumes in C3 format with strict 1-page enforcement.

This module generates professional resumes that:
- Use C3 page size (7.17" x 10.51")
- Match the user's resume format exactly
- Enforce strict 1-page limit with auto-truncation
- Use personalized data from parsed resume
- Inject job-specific keywords naturally
"""

from pathlib import Path
from typing import List, Optional

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches

from .models import ResumeData, Experience
from .utils import deduplicate_preserve_order, normalize_keyword
from .llm_client import rewrite_experience_bullets, rewrite_project_description, match_experience_with_jd


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "resume_templates" / "c3_template.docx"

# C3 Page Size: 7.17" x 10.51" (324mm x 458mm)
C3_WIDTH = Inches(7.17)
C3_HEIGHT = Inches(10.51)

# Margins (0.5" all around for maximum content space)
MARGIN_TOP = Inches(0.5)
MARGIN_BOTTOM = Inches(0.5)
MARGIN_LEFT = Inches(0.5)
MARGIN_RIGHT = Inches(0.5)

# Font sizes
FONT_NAME = "Calibri"
FONT_SIZE_HEADER = Pt(18)  # Name
FONT_SIZE_SECTION = Pt(11)  # Section headings
FONT_SIZE_BODY = Pt(10)  # Body text
FONT_SIZE_CONTACT = Pt(9)  # Contact info

# Spacing
LINE_SPACING = Pt(12)
PARAGRAPH_SPACING = Pt(6)


def generate_resume(
    output_path: str,
    keywords: List[str],
    resume_data: Optional[ResumeData] = None,
    job_description: Optional[str] = None
) -> None:
    """
    Generate a personalized, ATS-optimized resume in C3 format.
    
    Args:
        output_path: Path to save the generated DOCX file
        keywords: Extracted keywords from job description
        resume_data: Parsed resume data (if available)
        job_description: Job description (for future LLM rewriting)
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create new document
    document = Document()
    
    # Set C3 page size
    _set_c3_page_size(document)
    
    # Set margins
    _set_margins(document)
    
    # Build resume sections
    _build_header(document, resume_data)
    _build_education(document, resume_data)
    _build_skills(document, resume_data, keywords)
    _build_experience(document, resume_data, keywords, job_description)
    _build_projects(document, resume_data, keywords, job_description)
    _build_certifications(document, resume_data)
    
    # Enforce 1-page limit
    _enforce_one_page(document)
    
    # Save document
    document.save(str(output_file))


def _set_c3_page_size(document: Document) -> None:
    """Set document to C3 page size (7.17" x 10.51")."""
    section = document.sections[0]
    section.page_width = C3_WIDTH
    section.page_height = C3_HEIGHT
    section.orientation = WD_ORIENT.PORTRAIT


def _set_margins(document: Document) -> None:
    """Set document margins to 0.5" all around."""
    section = document.sections[0]
    section.top_margin = MARGIN_TOP
    section.bottom_margin = MARGIN_BOTTOM
    section.left_margin = MARGIN_LEFT
    section.right_margin = MARGIN_RIGHT


def _build_header(document: Document, resume_data: Optional[ResumeData]) -> None:
    """Build resume header with name and contact information."""
    if resume_data:
        # Name
        name_para = document.add_paragraph()
        name_run = name_para.add_run(resume_data.name.upper())
        name_run.font.name = FONT_NAME
        name_run.font.size = FONT_SIZE_HEADER
        name_run.bold = True
        name_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Contact info
        contact_parts = []
        if resume_data.email:
            contact_parts.append(resume_data.email)
        if resume_data.phone:
            contact_parts.append(resume_data.phone)
        if resume_data.linkedin:
            contact_parts.append(resume_data.linkedin)
        if resume_data.github:
            contact_parts.append(resume_data.github)
        if resume_data.location:
            contact_parts.append(resume_data.location)
        
        if contact_parts:
            contact_para = document.add_paragraph()
            contact_run = contact_para.add_run(" • ".join(contact_parts))
            contact_run.font.name = FONT_NAME
            contact_run.font.size = FONT_SIZE_CONTACT
            contact_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    else:
        # Fallback header
        name_para = document.add_paragraph()
        name_run = name_para.add_run("YOUR NAME")
        name_run.font.name = FONT_NAME
        name_run.font.size = FONT_SIZE_HEADER
        name_run.bold = True
        
        contact_para = document.add_paragraph()
        contact_run = contact_para.add_run("Email • Phone • LinkedIn • GitHub • Location")
        contact_run.font.name = FONT_NAME
        contact_run.font.size = FONT_SIZE_CONTACT
    
    # Add spacing
    document.add_paragraph()


def _build_education(document: Document, resume_data: Optional[ResumeData]) -> None:
    """Build education section."""
    if not resume_data or not resume_data.education:
        return
    
    # Section heading
    _add_section_heading(document, "EDUCATION")
    
    for edu in resume_data.education[:2]:  # Limit to 2 most recent
        # Degree and University
        edu_para = document.add_paragraph()
        edu_text = f"{edu.degree}"
        if edu.university:
            edu_text += f" | {edu.university}"
        if edu.location:
            edu_text += f", {edu.location}"
        
        edu_run = edu_para.add_run(edu_text)
        edu_run.font.name = FONT_NAME
        edu_run.font.size = FONT_SIZE_BODY
        edu_run.bold = True
        
        # Dates and GPA
        details_para = document.add_paragraph()
        details_parts = []
        if edu.dates:
            details_parts.append(edu.dates)
        if edu.gpa:
            details_parts.append(f"GPA: {edu.gpa}")
        
        if details_parts:
            details_run = details_para.add_run(" • ".join(details_parts))
            details_run.font.name = FONT_NAME
            details_run.font.size = FONT_SIZE_BODY
        
        # Coursework (if space allows)
        if edu.coursework and len(edu.coursework) > 0:
            coursework_para = document.add_paragraph()
            coursework_text = "Coursework: " + ", ".join(edu.coursework[:5])  # Limit to 5
            coursework_run = coursework_para.add_run(coursework_text)
            coursework_run.font.name = FONT_NAME
            coursework_run.font.size = FONT_SIZE_BODY
            coursework_run.italic = True
        
        document.add_paragraph()  # Spacing


def _build_skills(document: Document, resume_data: Optional[ResumeData], keywords: List[str]) -> None:
    """Build technical skills section with keyword injection."""
    # Section heading
    _add_section_heading(document, "TECHNICAL SKILLS")
    
    # Combine resume skills with extracted keywords
    all_skills = {}
    
    if resume_data and resume_data.skills:
        all_skills.update(resume_data.skills)
    
    # Add keywords as a new category if they don't exist
    if keywords:
        clean_keywords = deduplicate_preserve_order([normalize_keyword(k) for k in keywords if k])
        if clean_keywords:
            # Try to match keywords to existing categories, or create "Key Skills"
            if "Key Skills" not in all_skills:
                all_skills["Key Skills"] = []
            all_skills["Key Skills"].extend(clean_keywords[:15])  # Limit keywords
    
    # Format skills by category
    for category, skills_list in list(all_skills.items())[:6]:  # Limit to 6 categories
        if not skills_list:
            continue
        
        # Category header
        category_para = document.add_paragraph()
        category_run = category_para.add_run(f"{category}: ")
        category_run.font.name = FONT_NAME
        category_run.font.size = FONT_SIZE_BODY
        category_run.bold = True
        
        # Skills list
        skills_text = ", ".join(skills_list[:12])  # Limit skills per category
        skills_run = category_para.add_run(skills_text)
        skills_run.font.name = FONT_NAME
        skills_run.font.size = FONT_SIZE_BODY
    
    document.add_paragraph()  # Spacing


def _build_experience(
    document: Document,
    resume_data: Optional[ResumeData],
    keywords: List[str],
    job_description: Optional[str]
) -> None:
    """Build work experience section with personalized, optimized bullets."""
    if not resume_data or not resume_data.experience:
        return
    
    # Section heading
    _add_section_heading(document, "WORK EXPERIENCE")
    
    # Prioritize most relevant experiences using LLM
    if job_description and len(resume_data.experience) > 3:
        experiences = match_experience_with_jd(resume_data.experience, job_description, top_n=3)
    else:
        experiences = resume_data.experience[:3]
    
    for exp in experiences:
        # Title and Company (KEEP UNCHANGED - only personalize bullets)
        title_para = document.add_paragraph()
        title_text = f"{exp.title}"
        if exp.company:
            title_text += f" | {exp.company}"
        
        title_run = title_para.add_run(title_text)
        title_run.font.name = FONT_NAME
        title_run.font.size = FONT_SIZE_BODY
        title_run.bold = True
        
        # Dates (KEEP UNCHANGED)
        if exp.dates:
            dates_para = document.add_paragraph()
            dates_run = dates_para.add_run(exp.dates)
            dates_run.font.name = FONT_NAME
            dates_run.font.size = FONT_SIZE_BODY
        
        # Bullet points - PERSONALIZE using LLM if job description available
        if job_description and keywords:
            # Use LLM to rewrite bullets to match job description
            personalized_bullets = rewrite_experience_bullets(exp, job_description, keywords)
            bullets = personalized_bullets[:4]  # Limit to 4 bullets
        else:
            # Fallback to original bullets
            bullets = exp.bullets[:4]
        
        for bullet in bullets:
            bullet_para = document.add_paragraph(style="List Bullet")
            bullet_run = bullet_para.add_run(bullet)
            bullet_run.font.name = FONT_NAME
            bullet_run.font.size = FONT_SIZE_BODY
        
        document.add_paragraph()  # Spacing


def _build_projects(
    document: Document,
    resume_data: Optional[ResumeData],
    keywords: List[str],
    job_description: Optional[str]
) -> None:
    """Build projects section with personalized descriptions."""
    if not resume_data or not resume_data.projects:
        return
    
    # Section heading
    _add_section_heading(document, "PROJECTS")
    
    # Limit to top 3 projects
    projects = resume_data.projects[:3]
    
    for project in projects:
        # Project name (KEEP UNCHANGED - only personalize description)
        name_para = document.add_paragraph()
        name_text = project.name
        if project.category:
            name_text += f" ({project.category})"
        
        name_run = name_para.add_run(name_text)
        name_run.font.name = FONT_NAME
        name_run.font.size = FONT_SIZE_BODY
        name_run.bold = True
        
        # Technologies (KEEP UNCHANGED)
        if project.technologies:
            tech_para = document.add_paragraph()
            tech_text = "Technologies: " + ", ".join(project.technologies[:8])
            tech_run = tech_para.add_run(tech_text)
            tech_run.font.name = FONT_NAME
            tech_run.font.size = FONT_SIZE_BODY
            tech_run.italic = True
        
        # Description - PERSONALIZE using LLM if job description available
        if project.description:
            if job_description and keywords:
                # Use LLM to rewrite description to match job description
                personalized_description = rewrite_project_description(project, job_description, keywords)
                description_text = personalized_description[:200]  # Limit length
            else:
                # Fallback to original description
                description_text = project.description[:150]
            
            desc_para = document.add_paragraph(style="List Bullet")
            desc_run = desc_para.add_run(description_text)
            desc_run.font.name = FONT_NAME
            desc_run.font.size = FONT_SIZE_BODY
        
        document.add_paragraph()  # Spacing


def _build_certifications(document: Document, resume_data: Optional[ResumeData]) -> None:
    """Build certifications section."""
    if not resume_data or not resume_data.certifications:
        return
    
    # Section heading
    _add_section_heading(document, "CERTIFICATIONS")
    
    for cert in resume_data.certifications[:5]:  # Limit to 5
        cert_para = document.add_paragraph()
        cert_text = cert.name
        if cert.year:
            cert_text += f" ({cert.year})"
        if cert.issuer:
            cert_text += f" - {cert.issuer}"
        
        cert_run = cert_para.add_run(cert_text)
        cert_run.font.name = FONT_NAME
        cert_run.font.size = FONT_SIZE_BODY
    
    document.add_paragraph()  # Spacing


def _add_section_heading(document: Document, heading_text: str) -> None:
    """Add a section heading with consistent formatting."""
    heading_para = document.add_paragraph()
    heading_run = heading_para.add_run(heading_text)
    heading_run.font.name = FONT_NAME
    heading_run.font.size = FONT_SIZE_SECTION
    heading_run.bold = True
    heading_run.underline = True
    heading_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    # Add small spacing after heading
    document.add_paragraph()


def _enforce_one_page(document: Document) -> None:
    """
    Enforce 1-page limit by checking content height and truncating if needed.
    
    This is a simplified version. In production, you might want to:
    - Calculate exact content height
    - Remove less critical sections if needed
    - Reduce font sizes slightly
    - Remove less important bullet points
    """
    # python-docx doesn't have built-in page height calculation
    # So we use heuristics: limit total paragraphs and content
    
    # Count paragraphs
    total_paragraphs = len(document.paragraphs)
    
    # Rough estimate: C3 page can fit ~40-50 paragraphs with our formatting
    # If we exceed, we need to truncate
    max_paragraphs = 45
    
    if total_paragraphs > max_paragraphs:
        # Remove last few paragraphs (usually from less critical sections)
        paragraphs_to_remove = total_paragraphs - max_paragraphs
        for _ in range(paragraphs_to_remove):
            if len(document.paragraphs) > 10:  # Keep at least header and some content
                # Remove last paragraph
                last_para = document.paragraphs[-1]
                p_element = last_para._element
                p_element.getparent().remove(p_element)
    
    # Alternative: You could also reduce font sizes slightly if needed
    # But for now, paragraph limiting should work for most cases
