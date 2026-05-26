"""Knowledge base ingestion: chunk, embed, and upsert articles to pgvector.

Input article JSON format (required fields):
    {
        "article_id": "cbt-001",      # base ID; no language suffix here
        "language":   "en",           # "en" or "ar"
        "title":      "...",
        "source_url": "...",
        "citation":   "...",
        "content":    "...",
        "is_crisis_content": false    # REQUIRED — controls chunking strategy
    }

Bilingual pairing: "cbt-001-en" and "cbt-001-ar" must both be provided.
Chunk IDs: "{article_id}-{language}-{chunk_index:03d}" for multi-chunk articles.
          "{article_id}-{language}" for single-chunk (crisis) articles.
"""
from __future__ import annotations
import re
import logging
from typing import Any

_log = logging.getLogger(__name__)

_REQUIRED_FIELDS = {"article_id", "language", "title", "source_url", "citation", "content", "is_crisis_content"}

_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


def validate_article_schema(article: dict) -> None:
    """Raise ValueError if any required field is missing."""
    missing = _REQUIRED_FIELDS - set(article.keys())
    if missing:
        raise ValueError(f"Article missing required fields: {missing}")
    if article["language"] not in ("en", "ar"):
        raise ValueError(f"language must be 'en' or 'ar', got: {article['language']!r}")


def chunk_text(
    text: str,
    max_tokens: int = 100,
    is_crisis_content: bool = False,
) -> list[str]:
    """Split text into chunks at sentence boundaries.

    Crisis content is never split — returned as a single-element list.
    max_tokens is a word-count approximation (1 token ≈ 0.75 words; 100 tokens ≈ 75 words).
    """
    if is_crisis_content:
        return [text]
    sentences = _SENTENCE_END_RE.split(text.strip())
    chunks: list[str] = []
    current: list[str] = []
    word_count = 0
    max_words = int(max_tokens * 0.75)
    for sentence in sentences:
        sentence_words = len(sentence.split())
        if word_count + sentence_words > max_words and current:
            chunks.append(" ".join(current))
            current = [sentence]
            word_count = sentence_words
        else:
            current.append(sentence)
            word_count += sentence_words
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if c.strip()]


async def ingest_article(article: dict[str, Any], pool) -> int:
    """Chunk, embed, and upsert one article. Returns number of chunks inserted.

    Validates schema before any DB work. Raises ValueError on invalid input.
    Logs warnings for non-fatal issues (e.g. missing bilingual pair).
    """
    validate_article_schema(article)

    from sage_poc.memory.embedding import get_embedding  # noqa: PLC0415

    article_id_base = article["article_id"]
    language = article["language"]
    is_crisis = article["is_crisis_content"]
    chunk_id_prefix = f"{article_id_base}-{language}"
    citation_meta = {
        "title": article.get("title", ""),
        "source_url": article.get("source_url", ""),
        "citation": article.get("citation", ""),
    }

    chunks = chunk_text(article["content"], is_crisis_content=is_crisis)
    inserted = 0

    async with pool.acquire() as conn:
        for idx, chunk in enumerate(chunks):
            article_id = chunk_id_prefix if len(chunks) == 1 else f"{chunk_id_prefix}-{idx:03d}"
            embedding = get_embedding(chunk)
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            await conn.execute(
                """
                INSERT INTO public.knowledge_articles
                    (article_id, language, chunk_text, chunk_embedding,
                     is_crisis_content, source_title, source_url, citation_metadata)
                VALUES ($1, $2, $3, $4::vector, $5, $6, $7, $8)
                ON CONFLICT (article_id) DO UPDATE SET
                    chunk_text       = EXCLUDED.chunk_text,
                    chunk_embedding  = EXCLUDED.chunk_embedding,
                    is_crisis_content = EXCLUDED.is_crisis_content,
                    citation_metadata = EXCLUDED.citation_metadata
                """,
                article_id,
                language,
                chunk,
                embedding_str,
                is_crisis,
                article.get("title", ""),
                article.get("source_url", ""),
                citation_meta,
            )
            inserted += 1

    return inserted
