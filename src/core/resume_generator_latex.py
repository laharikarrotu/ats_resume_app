"""
LaTeX Resume Generator — ATS-Optimized for Top 10 ATS Platforms.

Compliant with: Workday (45%), Taleo (20%), Greenhouse (15%), Lever (10%),
                iCIMS, BambooHR, JazzHR, SmartRecruiters, Bullhorn, ADP.

Layout (US Letter, Helvetica 10pt):
  ┌──────────────────────────────────────┐
  │          FIRSTNAME LASTNAME          │  ← centered, bold, 14pt
  │  email | phone | LI | GH | City,ST  │  ← ONE line, centered
  ├── WORK EXPERIENCE ───────────────────┤
  │  Title                     Dates     │
  │  Company (italic)                    │
  │  - bullet with action verb + metrics │
  ├── PROJECTS ──────────────────────────┤
  │  Name | Tech1, Tech2                 │
  │  - description bullet with impact    │
  ├── EDUCATION ─────────────────────────┤
  │  Degree                     Year     │
  │  University, Location                │
  ├── TECHNICAL SKILLS ──────────────────┤
  │  Category: skill1, skill2, …         │
  ├── CERTIFICATIONS ────────────────────┤
  │  Cert Name - Issuer          Year    │
  └──────────────────────────────────────┘

ATS Rules Enforced:
  ✓ Single column — NO tables, NO columns, NO text boxes
  ✓ Contact on ONE line in body (not header/footer)
  ✓ Standard section names: WORK EXPERIENCE, EDUCATION, TECHNICAL SKILLS
  ✓ Simple bullets (-, •) ONLY
  ✓ Left-aligned content
  ✓ Helvetica 10pt (closest to Calibri in LaTeX)
  ✓ No images, graphics, icons
  ✓ Dates in "Month YYYY" format
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional

from ..models import ResumeData, Experience, Project, Education, Certification
from ..llm.client import (
    rewrite_experience_bullets,
    rewrite_project_description,
    match_experience_with_jd,
)


from ..config import BASE_DIR, OUTPUT_DIR

# ═══════════════════════════════════════════════════════════════
# LaTeX character escaping
# ═══════════════════════════════════════════════════════════════

def escape_latex(text: str) -> str:
    """Escape special LaTeX characters safely.

    Uses a placeholder strategy so that commands containing {}
    (like \\textbackslash{}) are not double-escaped.
    """
    if not text:
        return ""
    # Step 1 — replace chars whose LaTeX commands contain {} with placeholders
    text = text.replace('\\', '\x00BACKSLASH\x00')
    text = text.replace('^', '\x00CARET\x00')
    text = text.replace('~', '\x00TILDE\x00')
    # Step 2 — escape the rest (including braces)
    text = text.replace('&', r'\&')
    text = text.replace('%', r'\%')
    text = text.replace('$', r'\$')
    text = text.replace('#', r'\#')
    text = text.replace('_', r'\_')
    text = text.replace('{', r'\{')
    text = text.replace('}', r'\}')
    # Step 3 — restore placeholders with proper LaTeX commands
    text = text.replace('\x00BACKSLASH\x00', r'\textbackslash{}')
    text = text.replace('\x00CARET\x00', r'\textasciicircum{}')
    text = text.replace('\x00TILDE\x00', r'\textasciitilde{}')
    # Replace common Unicode chars that ATS may choke on
    text = text.replace('\u2192', r'$\rightarrow$')   # →
    text = text.replace('\u2014', '---')                # —
    text = text.replace('\u2013', '--')                 # –
    text = text.replace('\u2018', "'")                  # '
    text = text.replace('\u2019', "'")                  # '
    text = text.replace('\u201c', "``")                 # "
    text = text.replace('\u201d', "''")                 # "
    text = text.replace('\u2022', r'\textbullet{}')     # •
    return text


# ═══════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════

def generate_resume_latex(
    output_path: str,
    keywords: List[str],
    resume_data: Optional[ResumeData] = None,
    job_description: Optional[str] = None,
) -> str:
    """Generate an ATS-optimized resume as a PDF via LaTeX.

    Args:
        output_path: Where to save the generated PDF.
        keywords: Keywords extracted from job description.
        resume_data: Parsed resume data.
        job_description: Raw JD text (for tailoring bullets).

    Returns:
        Path to the generated PDF file.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Build the full LaTeX document string
    latex = _build_document(resume_data, keywords, job_description)

    # Write .tex
    tex_file = output_file.with_suffix('.tex')
    with open(tex_file, 'w', encoding='utf-8') as fh:
        fh.write(latex)

    # Compile .tex → .pdf
    pdf_file = _compile_latex(tex_file, output_file.with_suffix('.pdf'))
    return str(pdf_file)


# ═══════════════════════════════════════════════════════════════
# Document builder
# ═══════════════════════════════════════════════════════════════

def _build_document(
    resume_data: Optional[ResumeData],
    keywords: List[str],
    job_description: Optional[str],
) -> str:
    """Assemble the complete LaTeX source."""

    # Decide font size: try 10pt, fall back note for compiler
    font_size = "10pt"

    # ---------- Preamble ----------
    lines: List[str] = []
    lines.append(f"\\documentclass[{font_size},letterpaper]{{article}}")
    lines.append("")
    lines.append("% ── Packages")
    lines.append("\\usepackage[utf8]{inputenc}")
    lines.append("\\usepackage[T1]{fontenc}")
    lines.append("\\usepackage{helvet}")
    lines.append("\\renewcommand{\\familydefault}{\\sfdefault}")
    lines.append("\\usepackage[letterpaper, margin=0.5in, top=0.4in, bottom=0.4in]{geometry}")
    lines.append("\\usepackage{hyperref}")
    lines.append("\\usepackage{enumitem}")
    lines.append("\\usepackage{titlesec}")
    lines.append("\\usepackage{xcolor}")
    lines.append("")
    lines.append("% ── Page style")
    lines.append("\\pagestyle{empty}")
    lines.append("")
    lines.append("% ── Colors")
    lines.append("\\definecolor{linkblue}{HTML}{0563BB}")
    lines.append("\\definecolor{ruleline}{HTML}{333333}")
    lines.append("")
    lines.append("% ── Hyperlinks")
    lines.append("\\hypersetup{colorlinks=true, urlcolor=linkblue, linkcolor=linkblue, pdfborder={0 0 0}}")
    lines.append("")
    lines.append("% ── Section headings")
    lines.append("\\titleformat{\\section}{\\vspace{-6pt}\\large\\bfseries\\scshape}{}{0em}{}")
    lines.append("    [\\vspace{-6pt}\\color{ruleline}\\titlerule\\vspace{-4pt}]")
    lines.append("\\titlespacing{\\section}{0pt}{8pt}{4pt}")
    lines.append("")
    lines.append("% ── Compact lists")
    lines.append("\\setlist[itemize]{leftmargin=0.15in, topsep=1pt, parsep=0pt, partopsep=0pt, itemsep=1pt, label=\\textbullet}")
    lines.append("")
    lines.append("% ── Spacing")
    lines.append("\\setlength{\\parskip}{0pt}")
    lines.append("\\setlength{\\parindent}{0pt}")
    lines.append("\\setlength{\\tabcolsep}{0pt}")
    lines.append("")

    # ---------- Begin document ----------
    lines.append("\\begin{document}")
    lines.append("")

    if not resume_data:
        # Fallback: placeholder resume
        lines.append(_header_placeholder())
        lines.append(_section_placeholder("Experience", keywords))
        lines.append(_section_placeholder("Projects", keywords))
        lines.append(_section_placeholder("Education", keywords))
        lines.append(_section_placeholder("Technical Skills", keywords))
        lines.append(_section_placeholder("Certifications", keywords))
    else:
        lines.append(_build_header(resume_data))
        lines.append(_build_experience(resume_data, keywords, job_description))
        lines.append(_build_projects(resume_data, keywords, job_description))
        lines.append(_build_education(resume_data))
        lines.append(_build_skills(resume_data, keywords))
        lines.append(_build_certifications(resume_data))

    lines.append("")
    lines.append("\\end{document}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════

def _build_header(data: ResumeData) -> str:
    """Centered name on first line, contact info on second line."""
    name = escape_latex(data.name.upper()) if data.name else "YOUR NAME"

    # Build contact parts: City,ST | email | phone | LinkedIn | GitHub | Portfolio
    parts: List[str] = []

    if data.location:
        parts.append(escape_latex(data.location))

    if data.email:
        safe_email = escape_latex(data.email)
        parts.append(f"\\href{{mailto:{safe_email}}}{{{safe_email}}}")

    if data.phone:
        parts.append(escape_latex(data.phone))

    if data.linkedin:
        url = data.linkedin if data.linkedin.startswith("http") else f"https://{data.linkedin}"
        display = data.linkedin.replace("https://", "").replace("http://", "").rstrip("/")
        parts.append(f"\\href{{{escape_latex(url)}}}{{{escape_latex(display)}}}")

    if data.github:
        url = data.github if data.github.startswith("http") else f"https://{data.github}"
        display = data.github.replace("https://", "").replace("http://", "").rstrip("/")
        parts.append(f"\\href{{{escape_latex(url)}}}{{{escape_latex(display)}}}")

    contact_line = " \\enspace\\textbar\\enspace ".join(parts)

    return (
        "% ── HEADER\n"
        "\\begin{center}\n"
        f"    {{\\LARGE\\bfseries {name}}}\\\\[3pt]\n"
        f"    {{\\small {contact_line}}}\n"
        "\\end{center}\n"
        "\\vspace{-2pt}\n"
    )


# ═══════════════════════════════════════════════════════════════
# Experience Section
# ═══════════════════════════════════════════════════════════════

def _build_experience(
    data: ResumeData,
    keywords: List[str],
    job_description: Optional[str],
) -> str:
    if not data.experience:
        return ""

    lines = ["\\section{Work Experience}", ""]

    # Prioritize relevant experiences if JD available
    experiences = data.experience
    if job_description and len(experiences) > 3:
        try:
            experiences = match_experience_with_jd(experiences, job_description, top_n=4)
        except Exception:
            experiences = experiences[:4]
    else:
        experiences = experiences[:4]

    for i, exp in enumerate(experiences):
        title = escape_latex(exp.title)
        company = escape_latex(exp.company)
        dates = escape_latex(exp.dates) if exp.dates else ""

        lines.append(f"\\textbf{{{title}}} \\hfill \\textbf{{{dates}}}\\\\")
        lines.append(f"\\textit{{{company}}}")
        lines.append("")

        # Get bullets — optionally rewrite for JD
        bullets = exp.bullets
        if job_description and keywords:
            try:
                bullets = rewrite_experience_bullets(exp, job_description, keywords)
            except Exception:
                pass  # keep original bullets

        if bullets:
            lines.append("\\begin{itemize}")
            for bullet in bullets[:5]:  # max 5 bullets per role
                lines.append(f"    \\item {escape_latex(bullet)}")
            lines.append("\\end{itemize}")

        # Spacing between entries (not after the last one)
        if i < len(experiences) - 1:
            lines.append("\\vspace{2pt}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Projects Section
# ═══════════════════════════════════════════════════════════════

def _build_projects(
    data: ResumeData,
    keywords: List[str],
    job_description: Optional[str],
) -> str:
    if not data.projects:
        return ""

    lines = ["\\section{Projects}", ""]
    projects = data.projects[:4]  # max 4 projects

    for i, proj in enumerate(projects):
        name = escape_latex(proj.name)
        tech_str = ""
        if proj.technologies:
            tech_str = ", ".join(escape_latex(t) for t in proj.technologies[:8])

        # Header line: Name | Technologies   Link
        header = f"\\textbf{{{name}}}"
        if tech_str:
            header += f" \\enspace\\textbar\\enspace \\textit{{{tech_str}}}"
        lines.append(header)
        lines.append("")

        # Description bullets
        description = proj.description
        if job_description and keywords:
            try:
                description = rewrite_project_description(proj, job_description, keywords)
            except Exception:
                pass

        if description:
            # Split description into bullet-able sentences
            sentences = [s.strip() for s in description.replace(". ", ".\n").split("\n") if s.strip()]
            lines.append("\\begin{itemize}")
            for sent in sentences[:3]:  # max 3 bullets per project
                clean = sent.rstrip(".")
                lines.append(f"    \\item {escape_latex(clean)}.")
            lines.append("\\end{itemize}")

        if i < len(projects) - 1:
            lines.append("\\vspace{2pt}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Education Section
# ═══════════════════════════════════════════════════════════════

def _build_education(data: ResumeData) -> str:
    if not data.education:
        return ""

    lines = ["\\section{Education}", ""]

    for i, edu in enumerate(data.education):
        degree = escape_latex(edu.degree)
        dates = escape_latex(edu.dates) if edu.dates else ""

        # University + location
        uni_parts = []
        if edu.university:
            uni_parts.append(escape_latex(edu.university))
        if edu.location:
            uni_parts.append(escape_latex(edu.location))
        uni_str = ", ".join(uni_parts)

        lines.append(f"\\textbf{{{degree}}} \\hfill \\textbf{{{dates}}}\\\\")

        # University line (may include GPA inline)
        uni_line = ""
        if uni_str:
            uni_line = f"\\textit{{{uni_str}}}"
        if edu.gpa:
            uni_line += f" \\enspace\\textbar\\enspace GPA: {escape_latex(edu.gpa)}"
        if uni_line:
            lines.append(uni_line)

        # Coursework on next line
        if edu.coursework:
            cw = ", ".join(escape_latex(c) for c in edu.coursework)
            lines.append(f"\\\\Relevant Coursework: {cw}")

        if i < len(data.education) - 1:
            lines.append("\\vspace{2pt}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Technical Skills Section
# ═══════════════════════════════════════════════════════════════

def _build_skills(data: ResumeData, keywords: List[str]) -> str:
    skills = dict(data.skills) if data.skills else {}

    # Collect all existing skills (lowercase) across every category to avoid duplicates
    # Store both exact names AND the lowercase version for substring matching
    all_existing_lower: List[str] = []
    for skill_list in skills.values():
        for s in skill_list:
            all_existing_lower.append(s.lower())

    def _skill_already_present(keyword: str) -> bool:
        """Check if a keyword is already covered by an existing skill.
        Handles cases like keyword='AWS' matching skill='AWS (Lambda, S3)'.
        """
        kl = keyword.lower()
        for existing in all_existing_lower:
            if kl == existing or kl in existing or existing in kl:
                return True
        return False

    # Inject missing keywords into appropriate categories
    for kw in keywords:
        if _skill_already_present(kw):
            continue  # already present in some category
        cat = _categorize_skill(kw)
        if cat:
            if cat not in skills:
                skills[cat] = []
            skills[cat].append(kw)
            all_existing_lower.append(kw.lower())

    if not skills:
        return ""

    lines = ["\\section{Technical Skills}", ""]

    # Preferred category order
    preferred_order = [
        "Languages", "Programming Languages",
        "Backend", "Frameworks & APIs", "Frameworks",
        "Frontend",
        "Cloud", "Cloud Platforms",
        "Databases", "Databases & Storage",
        "AI/ML", "AI/ML & LLMs",
        "DevOps", "DevOps & MLOps",
        "Tools",
        "Monitoring & Analytics",
    ]

    rendered = set()
    skill_lines = []

    for cat_name in preferred_order:
        if cat_name in skills and cat_name not in rendered:
            skill_text = ", ".join(escape_latex(s) for s in skills[cat_name])
            skill_lines.append(f"\\textbf{{{escape_latex(cat_name)}:}} {skill_text}")
            rendered.add(cat_name)

    # Any remaining categories
    for cat_name, skill_list in skills.items():
        if cat_name not in rendered and skill_list:
            skill_text = ", ".join(escape_latex(s) for s in skill_list)
            skill_lines.append(f"\\textbf{{{escape_latex(cat_name)}:}} {skill_text}")

    lines.append("\\\\".join(skill_lines))
    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Certifications Section
# ═══════════════════════════════════════════════════════════════

def _build_certifications(data: ResumeData) -> str:
    if not data.certifications:
        return ""

    lines = ["\\section{Certifications}", ""]

    for cert in data.certifications:
        name = escape_latex(cert.name)
        issuer = escape_latex(cert.issuer) if cert.issuer else ""
        year = escape_latex(cert.year) if cert.year else ""

        entry = f"\\textbf{{{name}}}"
        if issuer:
            entry += f" --- {issuer}"
        if year:
            entry += f" \\hfill {year}"

        lines.append(entry)
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Placeholder / fallback content (when no resume_data)
# ═══════════════════════════════════════════════════════════════

def _header_placeholder() -> str:
    return (
        "\\begin{center}\n"
        "    {\\LARGE\\bfseries YOUR NAME}\\\\[3pt]\n"
        "    {\\small City, State \\enspace\\textbar\\enspace "
        "email@example.com \\enspace\\textbar\\enspace "
        "(555) 123-4567 \\enspace\\textbar\\enspace "
        "LinkedIn \\enspace\\textbar\\enspace GitHub}\n"
        "\\end{center}\n"
        "\\vspace{-2pt}\n"
    )


def _section_placeholder(title: str, keywords: List[str]) -> str:
    safe_title = escape_latex(title)
    lines = [f"\\section{{{safe_title}}}", ""]
    if title == "Technical Skills" and keywords:
        kw_text = ", ".join(escape_latex(k) for k in keywords[:15])
        lines.append(f"\\textbf{{Skills:}} {kw_text}")
    else:
        lines.append(f"{safe_title} content goes here.")
    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Skill categorization helper
# ═══════════════════════════════════════════════════════════════

def _categorize_skill(skill: str) -> Optional[str]:
    """Map a skill string to a resume category."""
    s = skill.lower()
    if any(k in s for k in ['python', 'java', 'javascript', 'typescript', 'sql',
                             'pyspark', 'scala', 'go', 'rust', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin']):
        return "Languages"
    if any(k in s for k in ['tensorflow', 'pytorch', 'hugging', 'llm', 'gpt',
                             'bert', 'ml', 'ai', 'machine learning', 'deep learning', 'gemini', 'ocr']):
        return "AI/ML"
    if any(k in s for k in ['aws', 'azure', 'gcp', 'cloud', 'sagemaker',
                             'lambda', 'oci', 'oracle cloud', 's3', 'ec2']):
        return "Cloud"
    if any(k in s for k in ['docker', 'kubernetes', 'terraform', 'ci/cd',
                             'devops', 'mlops', 'jenkins', 'github actions', 'ansible']):
        return "DevOps"
    if any(k in s for k in ['postgresql', 'mysql', 'mongodb', 'redis',
                             'database', 'dynamodb', 'cassandra', 'elasticsearch', 'oracle database']):
        return "Databases"
    if any(k in s for k in ['fastapi', 'django', 'flask', 'spring', 'express',
                             'node', 'rest', 'graphql', 'grpc']):
        return "Backend"
    if any(k in s for k in ['react', 'vue', 'angular', 'svelte', 'next',
                             'html', 'css', 'tailwind', 'redux', 'webpack']):
        return "Frontend"
    if any(k in s for k in ['git', 'jest', 'liquibase', 'jira', 'figma',
                             'postman', 'swagger', 'linux']):
        return "Tools"
    return None


# ═══════════════════════════════════════════════════════════════
# LaTeX Compilation
# ═══════════════════════════════════════════════════════════════

def _compile_latex(tex_file: Path, pdf_file: Path) -> Path:
    """Compile .tex → .pdf using the first available LaTeX engine."""

    engines = ['pdflatex', 'xelatex', 'lualatex']
    out_dir = str(pdf_file.parent)

    for engine in engines:
        if not shutil.which(engine):
            continue  # engine not installed
        try:
            result = subprocess.run(
                [engine, '-interaction=nonstopmode', '-output-directory', out_dir, str(tex_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                # Clean up aux files
                for ext in ['.aux', '.log', '.out']:
                    aux = tex_file.with_suffix(ext)
                    if aux.exists():
                        aux.unlink()
                return pdf_file
        except (subprocess.TimeoutExpired, OSError):
            continue

    # If we get here, no engine succeeded
    available = [e for e in engines if shutil.which(e)]
    if not available:
        raise RuntimeError(
            "No LaTeX engine found.  Install TeX Live (macOS: brew install --cask mactex-no-gui) "
            "or MiKTeX (Windows).  The .tex file has been generated and can be compiled manually."
        )
    raise RuntimeError(
        f"LaTeX compilation failed with engines: {', '.join(available)}.  "
        "Check the .log file next to the .tex for details."
    )
