"""Targeted repair of specific corpus articles in prod, with the source ref asserted first.

Exists because the 2026-08-19 sync tear (anxiety-001-ar absent, wellbeing-001-ar truncated
to 1 of 4 chunks) had no safe repair path. The obvious move -- re-run the sync -- is the
WRONG one: that path deletes a prefix before re-inserting it on a separate connection, and
it is what caused the damage. A pool exhaustion mid-run can turn a two-article hole into a
larger one.

This script instead re-ingests only the named articles through ingest_article, which
upserts (ON CONFLICT DO UPDATE), so no row is ever deleted and there is no instant at which
content is absent. Blast radius is exactly the articles you name.

    uv run python scripts/repair_corpus_articles.py --article anxiety-001:ar --dry-run
    uv run python scripts/repair_corpus_articles.py --article anxiety-001:ar --apply

Two guards are mandatory and non-optional:
  1. BEFORE writing, the corpus files must be byte-identical to origin/master. The first
     attempt at that repair ran from a checkout parked on a stale feature branch and wrote
     pre-refresh content into prod, reverting two approved citation upgrades.
  2. AFTER writing, every article's stored chunk count is compared against its file. A
     repair that leaves any article missing or truncated exits non-zero.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sys

import asyncpg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from scripts.prod_write_guard import assert_source_ref  # noqa: E402

CORPUS = "data/knowledge_corpus"


def _load(root: pathlib.Path, article_id: str, lang: str) -> dict:
    path = root / CORPUS / lang / f"{article_id}.json"
    if not path.exists():
        sys.exit(f"no such corpus file: {path}")
    return json.loads(path.read_text())


async def _stored_ids(conn, prefix: str) -> list[str]:
    rows = await conn.fetch(
        "SELECT article_id FROM public.knowledge_articles "
        "WHERE article_id = $1 OR article_id LIKE $1 || '-%' ORDER BY article_id", prefix)
    return [r["article_id"] for r in rows]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", action="append", required=True,
                    help="article_id:lang, e.g. anxiety-001:ar (repeatable)")
    ap.add_argument("--apply", action="store_true", help="write; default is a dry run")
    ap.add_argument("--ref", default="origin/master", help="ref the corpus must match")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    targets = []
    for spec in args.article:
        if ":" not in spec:
            sys.exit(f"--article expects article_id:lang, got {spec!r}")
        aid, lang = spec.rsplit(":", 1)
        targets.append((aid, lang))

    # Guard 1: never ship content from an unreviewed checkout.
    assert_source_ref([CORPUS], ref=args.ref, root=root)
    print(f"source ref verified against {args.ref}")

    from sage_poc.knowledge.ingestion import chunk_text, ingest_article

    dburl = os.environ.get("DBURL") or os.environ.get("DATABASE_URL")
    if not dburl:
        sys.exit("set DBURL (or DATABASE_URL) to the target database")

    pool = await asyncpg.create_pool(dburl, min_size=1, max_size=2, statement_cache_size=0)
    try:
        async with pool.acquire() as conn:
            print("\nPRE-STATE")
            for aid, lang in targets:
                art = _load(root, aid, lang)
                expected = len(chunk_text(art["content"], is_crisis_content=art["is_crisis_content"]))
                ids = await _stored_ids(conn, f"{aid}-{lang}")
                print(f"  {aid}-{lang}: stored {len(ids)}, file chunks {expected}")

        if not args.apply:
            print("\nDRY RUN — no writes. Re-run with --apply.")
            return 0

        print("\nAPPLYING (upsert only, never a delete)")
        for aid, lang in targets:
            n = await ingest_article(_load(root, aid, lang), pool)
            print(f"  {aid}-{lang}: upserted {n} chunks")

        # Guard 2: whole-corpus verification, not just the articles we touched — a repair
        # that fixes two articles while something else is broken is not a completed repair.
        from sage_poc.knowledge.sync import discover_corpus, verify_corpus_integrity
        async with pool.acquire() as conn:
            mismatches = await verify_corpus_integrity(conn, discover_corpus(root / CORPUS))
            total = await conn.fetchval("SELECT count(*) FROM public.knowledge_articles")
        if mismatches:
            print("\nREPAIR INCOMPLETE — corpus still diverges:")
            for prefix, exp, got in mismatches:
                print(f"  {prefix}: expected {exp}, stored {got}")
            return 1
        print(f"\nVERIFIED: every article matches its file; {total} chunks stored.")
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
