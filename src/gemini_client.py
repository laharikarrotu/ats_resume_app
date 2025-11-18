from typing import List

from .utils import deduplicate_preserve_order, normalize_keyword


def extract_keywords(job_description: str) -> List[str]:
    """
    Placeholder keyword extractor for local/demo use.

    In production, replace this with a real Gemini/OpenAI call that:
    - Summarizes the job description.
    - Extracts skills, responsibilities, and domain keywords.
    """
    # Naive heuristic: split on whitespace and filter basic tokens.
    raw_tokens = [
        token.strip(",.:-;()").lower()
        for token in job_description.split()
    ]

    # Filter out very short/common words
    stopwords = {
        "and",
        "or",
        "the",
        "a",
        "an",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "as",
        "is",
        "are",
    }
    candidates = [
        t for t in raw_tokens if len(t) > 2 and t not in stopwords
    ]

    normalized = [normalize_keyword(c) for c in candidates]
    return deduplicate_preserve_order(normalized)[:50]


# Example sketch of how you might wire Gemini/OpenAI later:
#
# import os
# import httpx
# 
# async def extract_keywords_llm(job_description: str) -> List[str]:
#     api_key = os.environ.get("GEMINI_API_KEY")
#     if not api_key:
#         raise RuntimeError("GEMINI_API_KEY not set")
#     async with httpx.AsyncClient(timeout=30) as client:
#         # Call your preferred LLM endpoint here.
#         ...


