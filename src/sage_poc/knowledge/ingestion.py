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
import hashlib
import json
import re
import logging
from typing import Any

_log = logging.getLogger(__name__)

_REQUIRED_FIELDS = {"article_id", "language", "title", "source_url", "citation", "content", "is_crisis_content"}

# Fields whose change should trigger a re-ingest (re-embed). Stable order.
_HASHED_FIELDS = ("article_id", "language", "title", "source_url", "video_url", "citation",
                  "content", "is_crisis_content")


def content_hash(article: dict) -> str:
    """Stable hash of the fields that affect retrieval/render output.

    Stored in citation_metadata.content_hash so sync_corpus can skip unchanged
    articles without re-embedding.
    """
    payload = json.dumps(
        {k: article.get(k) for k in _HASHED_FIELDS},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

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


def chunk_ids(article: dict[str, Any]) -> list[str]:
    """The exact article_id of every row this article produces, in order.

    Pure and deterministic, and deliberately the SINGLE source of those ids: the upsert
    below writes exactly this set, and the sync's surplus-delete keeps exactly this set.
    Two independent derivations of the same ids is how a delete predicate silently drifts
    from what was written — and this predicate deletes clinical content, so it must be
    provably the complement of the write, not merely similar to it.

    Single-chunk articles (crisis content, whole-document by contract) use the bare
    prefix; multi-chunk articles are suffixed -000, -001, ...
    """
    prefix = f"{article['article_id']}-{article['language']}"
    chunks = chunk_text(article["content"], is_crisis_content=article["is_crisis_content"])
    if len(chunks) == 1:
        return [prefix]
    return [f"{prefix}-{i:03d}" for i in range(len(chunks))]


class _ConnHolder:
    """Adapts a bare connection to the `async with pool.acquire()` shape."""

    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        holder = self

        class _Ctx:
            async def __aenter__(self):
                return holder._conn

            async def __aexit__(self, *_a):
                return False

        return _Ctx()


async def ingest_article(article: dict[str, Any], pool) -> int:
    """Chunk, embed, and upsert one article. Returns number of chunks inserted.

    Validates schema before any DB work. Raises ValueError on invalid input.
    Logs warnings for non-fatal issues (e.g. missing bilingual pair).

    `pool` may be an asyncpg pool OR an already-acquired connection. Passing the caller's
    connection matters during sync: acquiring a SECOND connection while the caller holds
    one doubles the sync's concurrent connection use and makes the write reachable by
    failures the caller's connection never sees — which is exactly how the 2026-08-19 tear
    happened (delete committed on one connection, re-ingest died on another when the
    session-mode pool ceiling was hit).
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
        "video_url": article.get("video_url", ""),
        "citation": article.get("citation", ""),
        "content_hash": content_hash(article),
    }

    chunks = chunk_text(article["content"], is_crisis_content=is_crisis)
    ids = chunk_ids(article)          # the one derivation; the delete predicate reuses it
    inserted = 0

    acquirer = pool if hasattr(pool, "acquire") else _ConnHolder(pool)
    async with acquirer.acquire() as conn:
        for idx, chunk in enumerate(chunks):
            article_id = ids[idx]
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
                json.dumps(citation_meta),
            )
            inserted += 1

    return inserted


def check_bilingual_pairing(articles: list[dict]) -> list[str]:
    """Return warning strings for article IDs that have only one language variant."""
    by_id: dict[str, set[str]] = {}
    for a in articles:
        validate_article_schema(a)
        base_id = a["article_id"]
        by_id.setdefault(base_id, set()).add(a["language"])
    warnings = []
    for base_id, langs in by_id.items():
        if "en" not in langs:
            warnings.append(f"WARNING: {base_id} has no English variant")
        if "ar" not in langs:
            warnings.append(f"WARNING: {base_id} has no Arabic variant")
    return warnings
