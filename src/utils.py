from typing import Iterable, List


def normalize_keyword(keyword: str) -> str:
    """Basic normalization for keywords before inserting into resume."""
    cleaned = keyword.strip()
    if not cleaned:
        return ""
    # Title case is a safe default for skills/technologies
    return cleaned.replace("_", " ").strip()


def deduplicate_preserve_order(items: Iterable[str]) -> List[str]:
    """Remove duplicates while preserving the original order."""
    seen = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


