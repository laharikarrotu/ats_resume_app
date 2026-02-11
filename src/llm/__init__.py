"""
LLM package — All language model interactions.

Re-exports key functions so existing code can use:
    from src.llm import extract_keywords, client, MODEL
"""

from .provider import (
    client,
    async_client,
    MODEL,
    ASYNC_MODEL,
    fallback_client,
    FALLBACK_MODEL,
    get_provider_info,
)
from .client import (
    extract_keywords,
    rewrite_experience_bullets,
    match_experience_with_jd,
    rewrite_project_description,
)
from .client_async import extract_keywords_async
from .parser import parse_resume_with_llm
from .prompts import (
    RESUME_PARSER_SYSTEM,
    RESUME_PARSER_PROMPT,
    KEYWORD_EXTRACTION_SYSTEM,
    KEYWORD_EXTRACTION_PROMPT,
    BULLET_REWRITE_SYSTEM,
    BULLET_REWRITE_PROMPT,
)

__all__ = [
    "client", "async_client", "MODEL", "ASYNC_MODEL",
    "fallback_client", "FALLBACK_MODEL", "get_provider_info",
    "extract_keywords", "rewrite_experience_bullets",
    "match_experience_with_jd", "rewrite_project_description",
    "extract_keywords_async", "parse_resume_with_llm",
]
