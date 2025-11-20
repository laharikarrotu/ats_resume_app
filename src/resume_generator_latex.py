"""
LaTeX Resume Generator: Generates resumes using LaTeX template for precise formatting.

This module:
- Uses your LaTeX template for exact format control
- Generates .tex file from ResumeData
- Compiles to PDF using pdflatex
- Ensures perfect format matching
"""

import re
import subprocess
from pathlib import Path
from typing import List, Optional

from .models import ResumeData
from .llm_client import rewrite_experience_bullets, rewrite_project_description, match_experience_with_jd


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "resume_templates" / "resume_template.latex"
OUTPUT_DIR = BASE_DIR / "outputs"


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    # LaTeX special characters that need escaping
    special_chars = {
        '\\': r'\\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '^': r'\textasciicircum{}',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
    }
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)
    return text


def generate_resume_latex(
    output_path: str,
    keywords: List[str],
    resume_data: Optional[ResumeData] = None,
    job_description: Optional[str] = None
) -> str:
    """
    Generate a personalized, ATS-optimized resume using LaTeX template.
    
    Args:
        output_path: Path to save the generated PDF file
        keywords: Extracted keywords from job description
        resume_data: Parsed resume data (if available)
        job_description: Job description (for personalization)
    
    Returns:
        Path to generated PDF file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Read template
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"LaTeX template not found: {TEMPLATE_PATH}")
    
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Generate LaTeX content from resume data
    latex_content = _build_latex_content(template, resume_data, keywords, job_description)
    
    # Write .tex file
    tex_file = output_file.with_suffix('.tex')
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    
    # Compile to PDF
    pdf_file = _compile_latex(tex_file, output_file.with_suffix('.pdf'))
    
    return str(pdf_file)


def _build_latex_content(
    template: str,
    resume_data: Optional[ResumeData],
    keywords: List[str],
    job_description: Optional[str]
) -> str:
    """Build LaTeX content by replacing placeholders with actual data."""
    
    if not resume_data:
        # Fallback content
        content = template
        # Replace header
        content = re.sub(r'\\textbf\{LAHARI KARROTU\}', r'\\textbf{YOUR NAME}', content)
        content = re.sub(r'\\url\{laharikarrotu24@gmail\.com\}', r'\\url{your.email@example.com}', content)
        content = re.sub(r'\+1 \(321\) 234-6914', r'+1 (555) 123-4567', content)
        content = re.sub(r'\\url\{linkedin\.com/in/lahari-karrotu\}', r'\\url{linkedin.com/in/yourprofile}', content)
        content = re.sub(r'\\url\{github\.com/lahari-karrotu\}', r'\\url{github.com/yourusername}', content)
        content = re.sub(r'Miami, FL', r'Your City, State', content)
        # Replace sections with placeholder
        content = _replace_section(content, 'EDUCATION', 'Education section placeholder')
        content = _replace_section(content, 'TECHNICAL SKILLS', f'Skills: {", ".join(keywords[:10])}')
        content = _replace_section(content, 'WORK EXPERIENCE', 'Work experience placeholder')
        content = _replace_section(content, 'PROJECTS', 'Projects placeholder')
        content = _replace_section(content, 'CERTIFICATIONS', 'Certifications placeholder')
        return content
    
    # Replace header with actual data
    content = template
    
    # Replace name
    content = re.sub(
        r'\\textbf\{LAHARI KARROTU\}',
        f'\\textbf{{{escape_latex(resume_data.name.upper())}}}',
        content
    )
    
    # Replace contact info
    if resume_data.email:
        content = re.sub(
            r'\\url\{laharikarrotu24@gmail\.com\}',
            f'\\url{{{escape_latex(resume_data.email)}}}',
            content
        )
    
    if resume_data.phone:
        content = re.sub(
            r'\+1 \(321\) 234-6914',
            escape_latex(resume_data.phone),
            content
        )
    
    # Replace social links
    linkedin_clean = resume_data.linkedin.replace('https://', '').replace('http://', '') if resume_data.linkedin else ''
    github_clean = resume_data.github.replace('https://', '').replace('http://', '') if resume_data.github else ''
    
    if linkedin_clean and github_clean:
        social_line = f'\\url{{{escape_latex(linkedin_clean)}}} \\textbar{{}}\\n\\url{{{escape_latex(github_clean)}}}'
        content = re.sub(
            r'\\url\{linkedin\.com/in/lahari-karrotu\} \\textbar\{\}\\n\\url\{github\.com/lahari-karrotu\}',
            social_line,
            content
        )
    
    if resume_data.location:
        content = re.sub(
            r'Miami, FL',
            escape_latex(resume_data.location),
            content
        )
    
    # Replace EDUCATION section
    education_latex = _build_education_latex(resume_data.education)
    content = _replace_section(content, 'EDUCATION', education_latex)
    
    # Replace TECHNICAL SKILLS section
    skills_latex = _build_skills_latex(resume_data.skills, keywords)
    content = _replace_section(content, 'TECHNICAL SKILLS', skills_latex)
    
    # Replace WORK EXPERIENCE section
    experience_latex = _build_experience_latex(resume_data.experience, keywords, job_description)
    content = _replace_section(content, 'WORK EXPERIENCE', experience_latex)
    
    # Replace PROJECTS section
    projects_latex = _build_projects_latex(resume_data.projects, keywords, job_description)
    content = _replace_section(content, 'PROJECTS', projects_latex)
    
    # Replace CERTIFICATIONS section
    certs_latex = _build_certifications_latex(resume_data.certifications)
    content = _replace_section(content, 'CERTIFICATIONS', certs_latex)
    
    return content


def _replace_section(content: str, section_name: str, replacement: str) -> str:
    """Replace a section in LaTeX content."""
    # Find section pattern: \textbf{SECTION_NAME} ... until next \textbf{_} or end
    # Escape braces properly in f-string by doubling them
    escaped_section = re.escape(section_name)
    pattern = rf'\\textbf\{{{escaped_section}\}}.*?(?=\\textbf\{{|\\end\{{document\}})'
    
    # Create replacement with section header
    # Use a lambda function to avoid escape sequence interpretation issues
    # This prevents Python from interpreting \u, \n, etc. in the replacement string
    def replacer(match):
        # Return the replacement - backslashes are literal here
        return '\\textbf{' + section_name + '}\n\n' + replacement + '\n'
    
    content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    return content


def _build_education_latex(education: List) -> str:
    """Build education section in LaTeX format."""
    if not education:
        return "Education information not available."
    
    lines = []
    for edu in education:
        # Degree and university
        degree_text = escape_latex(edu.degree)
        if edu.university:
            degree_text += f", {escape_latex(edu.university)}"
        if edu.location:
            degree_text += f", {escape_latex(edu.location)}"
        lines.append(degree_text)
        
        # GPA and dates
        details = []
        if edu.gpa:
            details.append(f"GPA: {escape_latex(edu.gpa)}")
        if edu.dates:
            details.append(escape_latex(edu.dates))
        
        if details:
            lines.append(f"\\textbar{{}} ".join(details).replace('--', '--'))
        lines.append("")
    
    return "\n".join(lines).strip()


def _build_skills_latex(skills: dict, keywords: List[str]) -> str:
    """Build technical skills section in LaTeX format."""
    lines = []
    
    # Use existing skills or create from keywords
    if not skills:
        skills = {}
    
    # Add keywords to appropriate categories
    for keyword in keywords:
        category = _categorize_skill(keyword)
        if category:
            if category not in skills:
                skills[category] = []
            if keyword not in skills[category]:
                skills[category].append(keyword)
    
    # Category order matching your format
    category_order = [
        "Programming Languages",
        "AI/ML & LLMs",
        "Cloud Platforms",
        "Data Engineering",
        "DevOps & MLOps",
        "Databases & Storage",
        "Frameworks & APIs",
        "Monitoring & Analytics"
    ]
    
    for category in category_order:
        if category in skills and skills[category]:
            skill_list = ", ".join([escape_latex(s) for s in skills[category][:20]])
            lines.append(f"\\textbf{{{category}:}} {skill_list}.")
    
    # Add any remaining categories
    for category, skill_list in skills.items():
        if category not in category_order:
            skill_text = ", ".join([escape_latex(s) for s in skill_list[:20]])
            lines.append(f"\\textbf{{{category}:}} {skill_text}.")
    
    return "\n\n".join(lines)


def _categorize_skill(skill: str) -> Optional[str]:
    """Categorize a skill (matching your resume format)."""
    skill_lower = skill.lower()
    if any(kw in skill_lower for kw in ['python', 'java', 'sql', 'javascript', 'typescript', 'pyspark', 'scala', 'r', 'go', 'rust']):
        return "Programming Languages"
    elif any(kw in skill_lower for kw in ['tensorflow', 'pytorch', 'hugging', 'llm', 'gpt', 'bert', 'ml', 'ai', 'machine learning', 'deep learning']):
        return "AI/ML & LLMs"
    elif any(kw in skill_lower for kw in ['aws', 'azure', 'gcp', 'cloud', 'sagemaker', 'lambda', 'glue']):
        return "Cloud Platforms"
    elif any(kw in skill_lower for kw in ['spark', 'databricks', 'kafka', 'etl', 'data engineering', 'airflow']):
        return "Data Engineering"
    elif any(kw in skill_lower for kw in ['docker', 'kubernetes', 'terraform', 'ci/cd', 'devops', 'mlops']):
        return "DevOps & MLOps"
    elif any(kw in skill_lower for kw in ['postgresql', 'mongodb', 'redis', 'database', 'storage', 'dynamodb']):
        return "Databases & Storage"
    elif any(kw in skill_lower for kw in ['fastapi', 'django', 'flask', 'react', 'node', 'api', 'framework']):
        return "Frameworks & APIs"
    elif any(kw in skill_lower for kw in ['datadog', 'new relic', 'splunk', 'monitoring', 'analytics']):
        return "Monitoring & Analytics"
    return None


def _build_experience_latex(
    experiences: List,
    keywords: List[str],
    job_description: Optional[str]
) -> str:
    """Build work experience section in LaTeX format."""
    if not experiences:
        return "Work experience not available."
    
    # Prioritize most relevant experiences
    if job_description and len(experiences) > 3:
        experiences = match_experience_with_jd(experiences, job_description, top_n=4)
    else:
        experiences = experiences[:4]
    
    lines = []
    for exp in experiences:
        # Title and company
        title_text = f"\\textbf{{{escape_latex(exp.title)} - {escape_latex(exp.company)}}}"
        lines.append(title_text)
        lines.append("")
        
        # Dates
        if exp.dates:
            lines.append(f"\\textbf{{{escape_latex(exp.dates)}}}")
            lines.append("")
        
        # Bullet points - personalize if job description available
        if job_description and keywords:
            bullets = rewrite_experience_bullets(exp, job_description, keywords)
        else:
            bullets = exp.bullets
        
        for bullet in bullets[:6]:  # Limit to 6 bullets per experience
            lines.append(f"• {escape_latex(bullet)}")
        
        lines.append("")
    
    return "\n".join(lines).strip()


def _build_projects_latex(
    projects: List,
    keywords: List[str],
    job_description: Optional[str]
) -> str:
    """Build projects section in LaTeX format."""
    if not projects:
        return "Projects not available."
    
    projects = projects[:4]  # Limit to 4 projects
    
    lines = []
    for project in projects:
        # Project name with category
        name_text = f"\\textbf{{{escape_latex(project.name)}"
        if project.category:
            name_text += f" ({escape_latex(project.category)})"
        name_text += "}"
        lines.append(name_text)
        lines.append("")
        
        lines.append("\\begin{itemize}")
        
        # Technologies
        if project.technologies:
            tech_text = ", ".join([escape_latex(t) for t in project.technologies[:15]])
            lines.append(f"\\item\n  Technologies: {tech_text}")
        
        # Description - personalize if available
        if project.description:
            if job_description and keywords:
                personalized = rewrite_project_description(project, job_description, keywords)
                # Split into sentences for multiple items
                sentences = personalized.split('. ')
                for sentence in sentences[:3]:
                    if sentence.strip():
                        lines.append(f"\\item\n  {escape_latex(sentence.strip())}.")
            else:
                sentences = project.description.split('. ')
                for sentence in sentences[:3]:
                    if sentence.strip():
                        lines.append(f"\\item\n  {escape_latex(sentence.strip())}.")
        
        lines.append("\\end{itemize}")
        lines.append("")
    
    return "\n".join(lines).strip()


def _build_certifications_latex(certifications: List) -> str:
    """Build certifications section in LaTeX format."""
    if not certifications:
        return "Certifications not available."
    
    lines = []
    for cert in certifications:
        cert_text = escape_latex(cert.name)
        if cert.year:
            cert_text += f" ({escape_latex(cert.year)})"
        lines.append(cert_text)
    
    return "\n".join(lines)


def _compile_latex(tex_file: Path, pdf_file: Path) -> Path:
    """Compile LaTeX file to PDF using pdflatex."""
    try:
        # Run pdflatex (requires LaTeX installation)
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(pdf_file.parent), str(tex_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            # If pdflatex fails, try xelatex or lualatex
            for command in ['xelatex', 'lualatex']:
                try:
                    result = subprocess.run(
                        [command, '-interaction=nonstopmode', '-output-directory', str(pdf_file.parent), str(tex_file)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        break
                except FileNotFoundError:
                    continue
        
        if result.returncode != 0:
            raise RuntimeError(f"LaTeX compilation failed: {result.stderr}")
        
        return pdf_file
    
    except FileNotFoundError:
        raise RuntimeError(
            "LaTeX not installed. Please install MiKTeX (Windows) or TeX Live (Linux/Mac).\n"
            "Alternatively, the .tex file has been generated and you can compile it manually."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("LaTeX compilation timed out.")

