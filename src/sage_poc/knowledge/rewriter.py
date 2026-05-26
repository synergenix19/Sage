"""POC-level Arabic query normalization.

Normalises common Alef variants (أ إ آ → ا), Ta marbuta (ة → ه),
and strips tatweel (ـ) so that Arabic queries match indexed text
regardless of diacritic variation.

Full Khaleeji→MSA rewriter with CAMeL Tools is a post-POC upgrade.
"""
import re

_ALEF_RE = re.compile(r"[أإآ]")
_TA_MARBUTA_RE = re.compile(r"ة")
_TATWEEL_RE = re.compile(r"ـ")


def normalize_arabic_query(query: str) -> str:
    """Normalize Arabic query text for pgvector full-text search compatibility."""
    query = _ALEF_RE.sub("ا", query)
    query = _TA_MARBUTA_RE.sub("ه", query)
    query = _TATWEEL_RE.sub("", query)
    return query
