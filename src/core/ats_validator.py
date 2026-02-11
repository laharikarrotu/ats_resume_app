"""
ATS Output Validator — Validates generated resumes for ATS compatibility.

This module runs post-generation checks to verify that the resume output
will parse correctly across the top 10 ATS platforms:
  Workday (45%), Taleo (20%), Greenhouse (15%), Lever (10%), iCIMS, etc.

Validation checks:
  1. Text extraction test (copy-paste simulation)
  2. Section identifiability (standard headers detected)
  3. Contact info parsability
  4. Date format consistency
  5. Special character detection
  6. Format structure (single column, no tables)
  7. Keyword density verification
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from ..models import ResumeData


# ═══════════════════════════════════════════════════════════
# Validation Result Models
# ═══════════════════════════════════════════════════════════

@dataclass
class ATSValidationIssue:
    """A single ATS validation issue found in the generated resume."""
    severity: str  # 'critical', 'warning', 'info'
    check: str     # Which check found this
    message: str
    suggestion: str = ""


@dataclass
class ATSValidationResult:
    """Complete ATS validation result for a generated resume."""
    ats_compatible: bool = True
    compatibility_score: int = 100  # 0-100
    issues: List[ATSValidationIssue] = field(default_factory=list)
    checks_passed: int = 0
    checks_total: int = 0
    section_detection: Dict[str, bool] = field(default_factory=dict)
    contact_parsed: Dict[str, bool] = field(default_factory=dict)
    keyword_density: Dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Standard ATS Section Headers (what ATS systems look for)
# ═══════════════════════════════════════════════════════════

STANDARD_SECTION_NAMES = {
    "experience": [
        "experience", "work experience", "professional experience",
        "employment", "employment history", "work history",
    ],
    "education": [
        "education", "academic background", "academic history",
    ],
    "skills": [
        "skills", "technical skills", "core competencies",
        "proficiencies", "technologies",
    ],
    "projects": [
        "projects", "personal projects", "key projects",
        "selected projects",
    ],
    "certifications": [
        "certifications", "certificates", "licenses",
        "professional certifications",
    ],
    "summary": [
        "summary", "professional summary", "profile",
        "objective", "career objective",
    ],
}

# Non-standard headers that ATS may NOT recognize
NON_STANDARD_HEADERS = {
    "my journey": "WORK EXPERIENCE",
    "career journey": "WORK EXPERIENCE",
    "what i've done": "WORK EXPERIENCE",
    "my story": "PROFESSIONAL SUMMARY",
    "about me": "PROFESSIONAL SUMMARY",
    "toolbox": "TECHNICAL SKILLS",
    "arsenal": "TECHNICAL SKILLS",
    "superpowers": "TECHNICAL SKILLS",
    "achievements": "WORK EXPERIENCE",
    "highlights": "PROFESSIONAL SUMMARY",
}

# ATS-unfriendly characters
ATS_BREAKING_CHARS = {
    "★": "*", "►": "-", "✓": "-", "✗": "-",
    "■": "-", "□": "-", "▪": "-", "▫": "-",
    "◆": "-", "◇": "-", "●": "*", "○": "-",
    "→": "->", "←": "<-", "↑": "^", "↓": "v",
    "❖": "*", "❯": ">", "❮": "<",
    "☐": "[ ]", "☑": "[x]", "☒": "[x]",
    "\u200b": "",  # zero-width space
    "\u00a0": " ",  # non-breaking space
    "\ufeff": "",  # BOM
}

# Date format patterns (ATS-parseable)
ATS_DATE_PATTERNS = [
    r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b',
    r'\b\d{1,2}/\d{4}\b',   # MM/YYYY
    r'\b\d{4}\b',            # YYYY alone
    r'\bPresent\b',
    r'\bCurrent\b',
]


# ═══════════════════════════════════════════════════════════
# Main Validation Function
# ═══════════════════════════════════════════════════════════

def validate_resume_output(
    resume_text: str,
    resume_data: Optional[ResumeData] = None,
    keywords: Optional[List[str]] = None,
) -> ATSValidationResult:
    """
    Validate a generated resume for ATS compatibility.

    Simulates how ATS platforms parse resumes by running
    the same checks they do: text extraction, section detection,
    contact parsing, date parsing, and format analysis.

    Args:
        resume_text: Full text of the generated resume (extracted from DOCX/PDF)
        resume_data: Original resume data (for verification)
        keywords: Target keywords to check density

    Returns:
        ATSValidationResult with score, issues, and detailed check results
    """
    result = ATSValidationResult()
    checks = []

    # 1. Text readability (copy-paste test)
    checks.append(_check_text_readability(resume_text, result))

    # 2. Section detection
    checks.append(_check_section_detection(resume_text, result))

    # 3. Contact info parsing
    checks.append(_check_contact_parsing(resume_text, resume_data, result))

    # 4. Date format consistency
    checks.append(_check_date_formats(resume_text, result))

    # 5. Special characters
    checks.append(_check_special_characters(resume_text, result))

    # 6. Structure checks (length, density)
    checks.append(_check_structure(resume_text, result))

    # 7. Non-standard section headers
    checks.append(_check_section_names(resume_text, result))

    # 8. Keyword density (if keywords provided)
    if keywords:
        checks.append(_check_keyword_density(resume_text, keywords, result))

    # 9. Contact info completeness
    checks.append(_check_contact_completeness(resume_text, result))

    # 10. Bullet point quality
    checks.append(_check_bullet_format(resume_text, result))

    # Calculate final score
    result.checks_total = len(checks)
    result.checks_passed = sum(1 for passed in checks if passed)

    # Score calculation: start at 100, deduct based on issues
    score = 100
    for issue in result.issues:
        if issue.severity == "critical":
            score -= 15
        elif issue.severity == "warning":
            score -= 5
        elif issue.severity == "info":
            score -= 1

    result.compatibility_score = max(0, min(100, score))
    result.ats_compatible = result.compatibility_score >= 70

    return result


# ═══════════════════════════════════════════════════════════
# Individual Checks
# ═══════════════════════════════════════════════════════════

def _check_text_readability(text: str, result: ATSValidationResult) -> bool:
    """Check 1: Text is readable (copy-paste test simulation)."""
    passed = True

    if not text or len(text.strip()) < 100:
        result.issues.append(ATSValidationIssue(
            severity="critical",
            check="text_readability",
            message="Resume text is too short or empty — ATS will reject this",
            suggestion="Ensure resume has substantial content (minimum 300 words)"
        ))
        return False

    # Check for garbled text (high ratio of non-ASCII characters)
    non_ascii_count = sum(1 for c in text if ord(c) > 127)
    non_ascii_ratio = non_ascii_count / len(text) if text else 0
    if non_ascii_ratio > 0.1:
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="text_readability",
            message=f"High non-ASCII character ratio ({non_ascii_ratio:.0%}) — may cause parsing issues",
            suggestion="Replace special characters with ASCII equivalents"
        ))
        passed = False

    # Check for scrambled text (words that are unreasonably long = concatenated)
    words = text.split()
    long_words = [w for w in words if len(w) > 30 and not w.startswith("http")]
    if len(long_words) > 3:
        result.issues.append(ATSValidationIssue(
            severity="critical",
            check="text_readability",
            message=f"Found {len(long_words)} excessively long words — text may be scrambled/concatenated",
            suggestion="Check PDF text extraction; ensure spaces between words"
        ))
        passed = False

    # Check for repeated characters (garbled output)
    if re.search(r'(.)\1{10,}', text):
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="text_readability",
            message="Found repeated character sequences — may indicate garbled text",
            suggestion="Check document encoding and font rendering"
        ))
        passed = False

    return passed


def _check_section_detection(text: str, result: ATSValidationResult) -> bool:
    """Check 2: ATS can identify resume sections."""
    passed = True
    text_lower = text.lower()

    required_sections = ["experience", "education", "skills"]
    optional_sections = ["projects", "certifications", "summary"]

    for section in required_sections:
        found = False
        for pattern in STANDARD_SECTION_NAMES.get(section, [section]):
            if pattern in text_lower:
                found = True
                break

        result.section_detection[section] = found
        if not found:
            result.issues.append(ATSValidationIssue(
                severity="critical",
                check="section_detection",
                message=f"Required section '{section.upper()}' not detected",
                suggestion=f"Add a clear '{section.upper()}' section header"
            ))
            passed = False

    for section in optional_sections:
        found = False
        for pattern in STANDARD_SECTION_NAMES.get(section, [section]):
            if pattern in text_lower:
                found = True
                break
        result.section_detection[section] = found

    return passed


def _check_contact_parsing(
    text: str,
    resume_data: Optional[ResumeData],
    result: ATSValidationResult,
) -> bool:
    """Check 3: ATS can parse contact information."""
    passed = True

    # Email detection
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    result.contact_parsed["email"] = len(emails) > 0

    if not emails:
        result.issues.append(ATSValidationIssue(
            severity="critical",
            check="contact_parsing",
            message="No email address detected in resume text",
            suggestion="Add email in standard format: name@domain.com"
        ))
        passed = False

    # Phone detection
    phone_pattern = r'[\+]?[(]?\d{1,4}[)]?[-\s\.]?\d{1,4}[-\s\.]?\d{1,9}'
    phones = re.findall(phone_pattern, text)
    # Filter out short numbers (years, metrics)
    phones = [p for p in phones if len(re.sub(r'[^\d]', '', p)) >= 10]
    result.contact_parsed["phone"] = len(phones) > 0

    if not phones:
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="contact_parsing",
            message="No phone number detected in resume text",
            suggestion="Add phone in format: (123) 456-7890 or +1-123-456-7890"
        ))
        passed = False

    # LinkedIn detection
    linkedin_found = "linkedin.com/in/" in text.lower() or "linkedin" in text.lower()
    result.contact_parsed["linkedin"] = linkedin_found

    # Location detection
    location_pattern = r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?,\s*[A-Z]{2}\b'
    locations = re.findall(location_pattern, text)
    result.contact_parsed["location"] = len(locations) > 0

    # Verify against original data if available
    if resume_data and resume_data.email and resume_data.email not in text:
        result.issues.append(ATSValidationIssue(
            severity="critical",
            check="contact_parsing",
            message=f"Original email '{resume_data.email}' not found in generated resume",
            suggestion="Ensure contact information is preserved in output"
        ))
        passed = False

    if resume_data and resume_data.phone:
        phone_digits = re.sub(r'[^\d]', '', resume_data.phone)
        if phone_digits and phone_digits not in re.sub(r'[^\d]', '', text):
            result.issues.append(ATSValidationIssue(
                severity="warning",
                check="contact_parsing",
                message="Original phone number not found in generated resume",
                suggestion="Ensure phone number is preserved in output"
            ))
            passed = False

    return passed


def _check_date_formats(text: str, result: ATSValidationResult) -> bool:
    """Check 4: Date formats are ATS-parseable."""
    passed = True

    # Find all dates in the text
    dates_found = []
    for pattern in ATS_DATE_PATTERNS:
        dates_found.extend(re.findall(pattern, text, re.IGNORECASE))

    if not dates_found:
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="date_formats",
            message="No parseable dates found in resume",
            suggestion="Use 'Month YYYY' format (e.g., 'Jan 2023 - Present')"
        ))
        passed = False

    # Check for inconsistent date formats
    month_year = len(re.findall(
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b',
        text, re.IGNORECASE
    ))
    numeric_dates = len(re.findall(r'\b\d{1,2}/\d{4}\b', text))

    if month_year > 0 and numeric_dates > 0:
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="date_formats",
            message="Mixed date formats detected (Month YYYY and MM/YYYY)",
            suggestion="Use a single consistent format throughout — 'Month YYYY' is most ATS-friendly"
        ))
        passed = False

    return passed


def _check_special_characters(text: str, result: ATSValidationResult) -> bool:
    """Check 5: No ATS-breaking special characters."""
    passed = True

    found_chars = {}
    for char, replacement in ATS_BREAKING_CHARS.items():
        if char in text:
            found_chars[char] = replacement

    if found_chars:
        char_list = ", ".join(f"'{c}'" for c in list(found_chars.keys())[:5])
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="special_characters",
            message=f"ATS-unfriendly characters detected: {char_list}",
            suggestion="Replace with standard ASCII: use - or * for bullets, standard quotes, etc."
        ))
        passed = False

    # Check for invisible characters
    invisible = [c for c in text if ord(c) < 32 and c not in '\n\r\t']
    if invisible:
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="special_characters",
            message=f"Found {len(invisible)} invisible/control characters",
            suggestion="Remove hidden characters that may confuse ATS parsers"
        ))
        passed = False

    return passed


def _check_structure(text: str, result: ATSValidationResult) -> bool:
    """Check 6: Overall document structure."""
    passed = True

    # Word count
    words = text.split()
    word_count = len(words)

    if word_count < 150:
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="structure",
            message=f"Resume has only {word_count} words — too sparse",
            suggestion="ATS may rank sparse resumes lower. Aim for 400-800 words"
        ))
        passed = False
    elif word_count > 1200:
        result.issues.append(ATSValidationIssue(
            severity="info",
            check="structure",
            message=f"Resume has {word_count} words — may exceed 2 pages",
            suggestion="Keep to 1-2 pages. 400-800 words for 1 page, 800-1200 for 2 pages"
        ))

    # Line count (rough page estimate)
    lines = text.strip().split('\n')
    non_empty_lines = [l for l in lines if l.strip()]

    if len(non_empty_lines) > 80:
        result.issues.append(ATSValidationIssue(
            severity="info",
            check="structure",
            message=f"Resume has {len(non_empty_lines)} content lines — may exceed 1 page",
            suggestion="Condense to fit within 1-2 pages"
        ))

    return passed


def _check_section_names(text: str, result: ATSValidationResult) -> bool:
    """Check 7: Section headers use ATS-recognized names."""
    passed = True
    text_lower = text.lower()

    for bad_name, good_name in NON_STANDARD_HEADERS.items():
        if bad_name in text_lower:
            result.issues.append(ATSValidationIssue(
                severity="critical",
                check="section_names",
                message=f"Non-standard section header '{bad_name}' detected",
                suggestion=f"Replace with ATS-standard: '{good_name}'"
            ))
            passed = False

    return passed


def _check_keyword_density(
    text: str,
    keywords: List[str],
    result: ATSValidationResult,
) -> bool:
    """Check 8: Target keywords appear with proper density."""
    passed = True
    text_lower = text.lower()

    present = 0
    total = len(keywords)

    for kw in keywords:
        kw_lower = kw.lower()
        count = text_lower.count(kw_lower)
        result.keyword_density[kw] = count

        if count > 0:
            present += 1

        # Keyword stuffing check (>5 occurrences is suspicious)
        if count > 5:
            result.issues.append(ATSValidationIssue(
                severity="warning",
                check="keyword_density",
                message=f"Keyword '{kw}' appears {count} times — may trigger keyword stuffing filter",
                suggestion="Use keywords 2-3 times naturally across different sections"
            ))

    if total > 0:
        match_pct = present / total * 100
        if match_pct < 40:
            result.issues.append(ATSValidationIssue(
                severity="critical",
                check="keyword_density",
                message=f"Only {match_pct:.0f}% keyword match ({present}/{total}) — below ATS threshold",
                suggestion="Target 60-80% keyword match. Add missing keywords to Skills and Experience"
            ))
            passed = False
        elif match_pct < 60:
            result.issues.append(ATSValidationIssue(
                severity="warning",
                check="keyword_density",
                message=f"{match_pct:.0f}% keyword match ({present}/{total}) — below optimal range",
                suggestion="Target 60-80% keyword match for best ATS ranking"
            ))

    return passed


def _check_contact_completeness(text: str, result: ATSValidationResult) -> bool:
    """Check 9: All essential contact info is present and in the first 5 lines."""
    passed = True
    lines = text.strip().split('\n')
    header_text = '\n'.join(lines[:8]).lower()  # First 8 lines = header area

    # Email in header
    if not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '\n'.join(lines[:8])):
        result.issues.append(ATSValidationIssue(
            severity="warning",
            check="contact_completeness",
            message="Email not found in header area (first 8 lines)",
            suggestion="Place contact info at the top of the resume, NOT in a header/footer"
        ))
        passed = False

    # Phone in header
    phone_in_header = re.search(r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', '\n'.join(lines[:8]))
    if not phone_in_header:
        result.issues.append(ATSValidationIssue(
            severity="info",
            check="contact_completeness",
            message="Phone number not found in header area",
            suggestion="Place phone number on the contact line at the top"
        ))

    return passed


def _check_bullet_format(text: str, result: ATSValidationResult) -> bool:
    """Check 10: Bullet points use ATS-safe characters."""
    passed = True

    # Find lines that look like bullets
    lines = text.split('\n')
    bullet_lines = [l.strip() for l in lines if l.strip() and (
        l.strip().startswith(('•', '-', '*', '–', '—', '►', '▪', '●'))
        or re.match(r'^\s*[\u2022\u2023\u25cf\u25cb\u25aa\u25ab]', l)
    )]

    if bullet_lines:
        # Check for exotic bullet chars
        exotic_bullets = [l for l in bullet_lines if not l.startswith(('•', '-', '*'))]
        if exotic_bullets:
            result.issues.append(ATSValidationIssue(
                severity="warning",
                check="bullet_format",
                message=f"{len(exotic_bullets)} bullets use non-standard characters",
                suggestion="Use only • (bullet), - (dash), or * (asterisk) for bullet points"
            ))
            passed = False

    return passed


# ═══════════════════════════════════════════════════════════
# Convenience: Validate DOCX file directly
# ═══════════════════════════════════════════════════════════

def validate_docx_file(
    file_path: str,
    resume_data: Optional[ResumeData] = None,
    keywords: Optional[List[str]] = None,
) -> ATSValidationResult:
    """Validate a DOCX file for ATS compatibility by extracting its text."""
    try:
        from docx import Document
        doc = Document(file_path)
        text_parts = []
        for para in doc.paragraphs:
            text_parts.append(para.text)
        full_text = '\n'.join(text_parts)
        return validate_resume_output(full_text, resume_data, keywords)
    except Exception as e:
        result = ATSValidationResult()
        result.ats_compatible = False
        result.compatibility_score = 0
        result.issues.append(ATSValidationIssue(
            severity="critical",
            check="file_read",
            message=f"Could not read DOCX file: {e}",
            suggestion="Ensure the file is a valid DOCX document"
        ))
        return result


def validate_pdf_file(
    file_path: str,
    resume_data: Optional[ResumeData] = None,
    keywords: Optional[List[str]] = None,
) -> ATSValidationResult:
    """Validate a PDF file for ATS compatibility by extracting its text."""
    try:
        from .pdf_extractor import extract_text_from_pdf
        text, _ = extract_text_from_pdf(file_path)
        return validate_resume_output(text, resume_data, keywords)
    except Exception as e:
        result = ATSValidationResult()
        result.ats_compatible = False
        result.compatibility_score = 0
        result.issues.append(ATSValidationIssue(
            severity="critical",
            check="file_read",
            message=f"Could not read PDF file: {e}",
            suggestion="Ensure the file is a valid PDF document"
        ))
        return result


# ═══════════════════════════════════════════════════════════
# Format Sanitizer
# ═══════════════════════════════════════════════════════════

def sanitize_for_ats(text: str) -> str:
    """
    Clean text for ATS compatibility.
    Replaces problematic characters and normalizes formatting.
    """
    # Replace ATS-breaking characters
    for char, replacement in ATS_BREAKING_CHARS.items():
        text = text.replace(char, replacement)

    # Normalize quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # smart single quotes
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # smart double quotes

    # Normalize dashes
    text = text.replace('\u2014', '--')  # em dash
    text = text.replace('\u2013', '-')   # en dash

    # Normalize whitespace
    text = re.sub(r'[\t ]{2,}', ' ', text)       # collapse multiple spaces
    text = re.sub(r'\n{3,}', '\n\n', text)        # max 2 newlines

    # Remove zero-width characters
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

    return text
