"""Idempotent corpus sync — auto-ingestion with content-hash change detection.

The corpus lives in version control under data/knowledge_corpus/{en,ar}/*.json.
Ingestion was historically a manual CLI (scripts/ingest_knowledge.py) that nobody
ran against prod, so knowledge_articles sat empty and every info_request abstained.

This module makes ingestion safe to run on every deploy:
  * unchanged articles are skipped (no re-embed) via a per-article content hash
    stashed in citation_metadata.content_hash,
  * edited articles are deleted-and-reinserted (handles chunk-count changes that a
    plain upsert would orphan),
  * a Postgres advisory lock serialises concurrent instances.

discover_corpus / content_hash / compute_sync_plan are pure (unit-tested).
sync_corpus is the thin DB wrapper wired into server startup.
"""
from __future__ import annotations

import json
import logging
import pathlib
import re
from dataclasses import dataclass, field

# content_hash lives in ingestion (lower level); re-exported here so callers and
# tests can import it from sync alongside the planning helpers.
from sage_poc.knowledge.ingestion import (
    content_hash,
    ingest_article,
    validate_article_schema,
)

_log = logging.getLogger(__name__)

# Fixed key for pg_advisory_lock so two booting instances can't double-ingest.
_LOCK_KEY = 0x5A6E_C0DE  # "Sage code" — arbitrary stable bigint
_CHUNK_SUFFIX_RE = re.compile(r"-\d{3}$")


def chunk_prefix(article: dict) -> str:
    """The article_id prefix shared by all of an article's chunks."""
    return f"{article['article_id']}-{article['language']}"


def discover_corpus(corpus_root: str | pathlib.Path) -> list[dict]:
    """Load and validate every article JSON under corpus_root, recursively.

    Recurses so a single root (data/knowledge_corpus/) picks up both en/ and ar/
    — the old flat glob silently found nothing when pointed at the parent dir.
    """
    root = pathlib.Path(corpus_root)
    articles: list[dict] = []
    for f in sorted(root.rglob("*.json")):
        article = json.loads(f.read_text())
        validate_article_schema(article)  # raises ValueError on bad input
        articles.append(article)
    return articles


@dataclass
class SyncPlan:
    to_ingest: list[dict] = field(default_factory=list)   # new or changed articles
    to_skip: list[str] = field(default_factory=list)      # unchanged chunk prefixes
    to_prune: list[str] = field(default_factory=list)     # db-only prefixes (if prune)


def compute_sync_plan(
    articles: list[dict],
    existing_hashes: dict[str, str],
    *,
    prune: bool,
) -> SyncPlan:
    """Decide, per article, whether to ingest / skip / prune.

    existing_hashes maps chunk_prefix -> stored content_hash currently in the DB.
    """
    plan = SyncPlan()
    seen: set[str] = set()
    for art in articles:
        prefix = chunk_prefix(art)
        seen.add(prefix)
        stored = existing_hashes.get(prefix)
        if stored is None or stored != content_hash(art):
            plan.to_ingest.append(art)
        else:
            plan.to_skip.append(prefix)
    if prune:
        plan.to_prune = [p for p in existing_hashes if p not in seen]
    return plan


@dataclass
class SyncResult:
    ingested: int = 0
    skipped: int = 0
    pruned: int = 0
    chunks: int = 0
    locked_out: bool = False  # another instance held the advisory lock


def _prefix_of(article_id: str) -> str:
    """Map a stored chunk id (cbt-001-en-000 or cbt-001-en) back to its prefix."""
    return _CHUNK_SUFFIX_RE.sub("", article_id)


async def _load_existing_hashes(conn) -> dict[str, str]:
    rows = await conn.fetch(
        "SELECT article_id, citation_metadata FROM public.knowledge_articles"
    )
    out: dict[str, str] = {}
    for r in rows:
        meta = r["citation_metadata"] or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        h = meta.get("content_hash")
        if h:
            out[_prefix_of(r["article_id"])] = h
    return out


async def _delete_prefix(conn, prefix: str) -> None:
    await conn.execute(
        "DELETE FROM public.knowledge_articles "
        "WHERE article_id = $1 OR article_id LIKE $1 || '-%'",
        prefix,
    )


async def sync_corpus(
    corpus_root: str | pathlib.Path,
    pool,
    *,
    prune: bool = False,
) -> SyncResult:
    """Reconcile the on-disk corpus into knowledge_articles. Idempotent.

    Safe to call on every deploy: unchanged articles cost one SELECT and no embed.
    Fail-open is the caller's responsibility (startup wraps this in try/except).
    """
    articles = discover_corpus(corpus_root)
    async with pool.acquire() as conn:
        got = await conn.fetchval("SELECT pg_try_advisory_lock($1)", _LOCK_KEY)
        if not got:
            _log.info("[corpus-sync] another instance holds the lock; skipping")
            return SyncResult(locked_out=True)
        try:
            existing = await _load_existing_hashes(conn)
            plan = compute_sync_plan(articles, existing, prune=prune)
            result = SyncResult(skipped=len(plan.to_skip))
            for art in plan.to_ingest:
                await _delete_prefix(conn, chunk_prefix(art))
                result.chunks += await ingest_article(art, pool)
                result.ingested += 1
            for prefix in plan.to_prune:
                await _delete_prefix(conn, prefix)
                result.pruned += 1
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", _LOCK_KEY)
    _log.info(
        "[corpus-sync] ingested=%d skipped=%d pruned=%d chunks=%d",
        result.ingested, result.skipped, result.pruned, result.chunks,
    )
    return result
