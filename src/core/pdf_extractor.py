"""
Smart PDF Text Extractor — recovers spaces from character-level position data.

Many LaTeX-generated PDFs (and some design tools) don't embed explicit space
characters. Instead, words are positioned with gaps between them.

This module reads individual character positions and inserts spaces where the
gap between consecutive characters exceeds a threshold.
"""

import re
from pathlib import Path
from typing import List, Optional

import pdfplumber
from pypdf import PdfReader

import logging

logger = logging.getLogger("ats")


# ═══════════════════════════════════════════════════════════
# Primary: character-level extraction with space recovery
# ═══════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF with intelligent space recovery.

    Strategy (in order):
      1. Character-level extraction with gap-based space insertion (most accurate)
      2. pdfplumber extract_text (fallback)
      3. pypdf extract_text (last resort)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    # Strategy 1: Character-level gap analysis
    try:
        text = _extract_with_char_gaps(file_path)
        if text and len(text.strip()) > 50:
            # Validate: check if spaces exist reasonably
            words = text.split()
            avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
            if avg_word_len < 15:  # reasonable word lengths
                logger.info("PDF extracted with char-gap method (%d chars, %d words)", len(text), len(words))
                return text
            else:
                logger.warning("Char-gap extraction produced long words (avg %.1f), trying fallbacks", avg_word_len)
    except Exception as e:
        logger.warning("Char-gap extraction failed: %s", e)

    # Strategy 2: pdfplumber default
    try:
        text = _extract_with_pdfplumber(file_path)
        if text and len(text.strip()) > 50:
            # Check if it needs space recovery
            text = _recover_spaces_heuristic(text)
            logger.info("PDF extracted with pdfplumber (%d chars)", len(text))
            return text
    except Exception as e:
        logger.warning("pdfplumber extraction failed: %s", e)

    # Strategy 3: pypdf
    try:
        text = _extract_with_pypdf(file_path)
        if text:
            text = _recover_spaces_heuristic(text)
            logger.info("PDF extracted with pypdf (%d chars)", len(text))
            return text
    except Exception as e:
        logger.warning("pypdf extraction failed: %s", e)

    raise RuntimeError(f"All PDF extraction methods failed for: {file_path}")


def extract_pdf_links(file_path: str) -> dict:
    """
    Extract hyperlinks embedded in the PDF (LinkedIn, GitHub, portfolio URLs).
    Returns a dict like: {"linkedin": "https://...", "github": "https://...", "portfolio": "..."}
    """
    links: dict = {}
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                if hasattr(page, "hyperlinks"):
                    for link in page.hyperlinks:
                        uri = link.get("uri", "")
                        if "linkedin.com" in uri:
                            links["linkedin"] = uri
                        elif "github.com" in uri:
                            links["github"] = uri
                        elif uri.startswith("http") and "linkedin" not in uri and "github" not in uri:
                            links.setdefault("portfolio", uri)

        # Fallback: try pypdf for annotations
        if not links:
            reader = PdfReader(file_path)
            for page in reader.pages:
                if "/Annots" in page:
                    annotations = page["/Annots"]
                    for annot in annotations:
                        obj = annot.get_object() if hasattr(annot, "get_object") else annot
                        if "/A" in obj and "/URI" in obj["/A"]:
                            uri = str(obj["/A"]["/URI"])
                            if "linkedin.com" in uri:
                                links["linkedin"] = uri
                            elif "github.com" in uri:
                                links["github"] = uri
                            elif uri.startswith("http"):
                                links.setdefault("portfolio", uri)
    except Exception as e:
        logger.warning("Could not extract PDF links: %s", e)

    return links


def _extract_with_char_gaps(file_path: str) -> str:
    """
    Read every character with its x/y position, reconstruct text
    by inserting spaces where the gap between chars exceeds a threshold.
    """
    all_lines: List[str] = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            chars = page.chars
            if not chars:
                continue

            # Sort by vertical position (top), then horizontal (x0)
            chars_sorted = sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"]))

            current_line_chars: List[str] = []
            prev_char = None
            prev_top = None

            for ch in chars_sorted:
                char_text = ch["text"]
                char_top = round(ch["top"], 1)
                char_x0 = ch["x0"]
                char_x1 = ch["x1"]
                char_size = ch.get("size", 10)

                # Detect new line (vertical jump)
                if prev_top is not None and abs(char_top - prev_top) > char_size * 0.4:
                    line_text = "".join(current_line_chars).rstrip()
                    if line_text:
                        all_lines.append(line_text)
                    current_line_chars = []
                    prev_char = None

                # Detect space (horizontal gap)
                if prev_char is not None:
                    gap = char_x0 - prev_char["x1"]
                    # Adaptive threshold: space if gap > ~30% of the average char width
                    avg_char_width = max((prev_char["x1"] - prev_char["x0"]), 3)
                    space_threshold = avg_char_width * 0.35

                    if gap > space_threshold:
                        current_line_chars.append(" ")

                current_line_chars.append(char_text)
                prev_char = ch
                prev_top = char_top

            # Flush last line of the page
            line_text = "".join(current_line_chars).rstrip()
            if line_text:
                all_lines.append(line_text)

    return "\n".join(all_lines)


# ═══════════════════════════════════════════════════════════
# Fallback extractors
# ═══════════════════════════════════════════════════════════

def _extract_with_pdfplumber(file_path: str) -> str:
    """Standard pdfplumber extraction."""
    parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _extract_with_pypdf(file_path: str) -> str:
    """pypdf extraction."""
    reader = PdfReader(file_path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
# Heuristic space recovery (for when extractors miss spaces)
# ═══════════════════════════════════════════════════════════

def _recover_spaces_heuristic(text: str) -> str:
    """
    Insert spaces into text where they're obviously missing.

    Handles CamelCase boundaries, lowercase→uppercase transitions,
    and common patterns from broken PDF extraction.
    """
    if not text:
        return text

    # Check if text already has reasonable spacing
    words = text.split()
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 10:
            return text  # Already well-spaced

    lines = text.split("\n")
    fixed_lines = []

    for line in lines:
        fixed_lines.append(_fix_line_spacing(line))

    return "\n".join(fixed_lines)


def _fix_line_spacing(line: str) -> str:
    """Fix spacing in a single line."""
    if not line or len(line) < 3:
        return line

    # Don't fix lines that already have good spacing
    words = line.split()
    if words and sum(len(w) for w in words) / len(words) < 10:
        return line

    result = []
    i = 0
    while i < len(line):
        c = line[i]
        result.append(c)

        if i + 1 < len(line):
            next_c = line[i + 1]

            # Insert space at lowercase→Uppercase boundary (camelCase split)
            # e.g., "SoftwareEngineer" → "Software Engineer"
            if c.islower() and next_c.isupper():
                result.append(" ")

            # Insert space at letter→digit boundary when it makes sense
            # e.g., "May2025" → "May 2025", "from87%" → "from 87%"
            elif c.isalpha() and next_c.isdigit() and not _is_known_compound(line, i):
                result.append(" ")

            # Insert space at digit→letter boundary
            # e.g., "98%to" → "98% to", "2025Present" → "2025 Present"
            # Allow: "3s", "800ms" (unit suffixes)
            elif c.isdigit() and next_c.isalpha():
                if next_c.isupper():
                    result.append(" ")
                elif not _is_unit_suffix(line, i + 1):
                    result.append(" ")

            # Insert space after % followed by a letter
            # e.g., "87%to" → "87% to"
            elif c == '%' and next_c.isalpha():
                result.append(" ")

            # Period followed by uppercase (sentence boundary)
            # e.g., "providers.Built" → "providers. Built"
            elif c == "." and next_c.isupper() and i + 1 < len(line):
                # But not for abbreviations like "U.S." or "Ph.D."
                if i >= 1 and not line[i-1].isupper():
                    result.append(" ")

        i += 1

    return "".join(result)


def _is_unit_suffix(text: str, pos: int) -> bool:
    """Check if position starts a measurement unit suffix like 's', 'ms', 'hrs', 'GB', 'MB', etc."""
    remaining = text[pos:pos + 4].lower()
    units = ["s ", "s.", "s,", "s-", "s→", "ms", "hr", "gb", "mb", "kb", "tb", "px", "pt", "em", "rem", "vh", "vw"]
    for unit in units:
        if remaining.startswith(unit):
            return True
    # Single 's' at end of text
    if pos == len(text) - 1 and text[pos].lower() == 's':
        return True
    return False


def _is_known_compound(text: str, pos: int) -> bool:
    """Check if the current position is part of a known compound like 'HL7', 'OAuth2', 'h1', etc."""
    # Look at a small window around the position
    start = max(0, pos - 5)
    end = min(len(text), pos + 6)
    window = text[start:end].lower()

    # Known patterns that shouldn't be split
    compounds = [
        "oauth2", "hl7", "h1", "h2", "h3", "s3", "ec2", "gpt4", "gpt3",
        "web3", "log4", "int8", "utf8", "md5", "sha256", "base64",
        "3s", "4s", "2s", "800ms", "100ms", "50ms",
    ]
    for compound in compounds:
        if compound in window:
            return True
    return False
