"""Load/refresh clinical knowledge articles in the pgvector knowledge_articles table.

Usage:
    uv run python scripts/ingest_knowledge.py                       # uses $DATABASE_URL, default corpus
    uv run python scripts/ingest_knowledge.py --corpus-dir data/knowledge_corpus
    uv run python scripts/ingest_knowledge.py --db-url postgresql://... --prune

Idempotent: unchanged articles are skipped (no re-embed), edited articles are
deleted-and-reinserted, and --prune removes articles no longer in the corpus.
Recurses into language subdirs (en/, ar/), so point --corpus-dir at the root.
This is the SAME code path the server runs automatically on startup
(sage_poc.knowledge.sync.sync_corpus); the CLI is for manual/one-off runs.
"""
import argparse
import asyncio
import os
import pathlib
import sys

import asyncpg

_DEFAULT_CORPUS = pathlib.Path(__file__).resolve().parent.parent / "data" / "knowledge_corpus"


async def _run(corpus_dir: pathlib.Path, db_url: str, prune: bool) -> None:
    from sage_poc.knowledge.sync import sync_corpus

    pool = await asyncpg.create_pool(db_url, min_size=2, max_size=5)
    try:
        result = await sync_corpus(corpus_dir, pool, prune=prune)
    finally:
        await pool.close()

    if result.locked_out:
        print("Another process holds the corpus-sync lock; nothing done.")
        return
    print(
        f"Corpus sync complete: ingested={result.ingested} "
        f"skipped={result.skipped} pruned={result.pruned} "
        f"({result.chunks} chunks embedded)."
    )


def main():
    parser = argparse.ArgumentParser(description="Sync knowledge base articles into pgvector.")
    parser.add_argument("--corpus-dir", type=pathlib.Path, default=_DEFAULT_CORPUS,
                        help=f"Corpus root (recursive). Default: {_DEFAULT_CORPUS}")
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"),
                        help="asyncpg DSN. Default: $DATABASE_URL")
    parser.add_argument("--prune", action="store_true",
                        help="Delete articles in the DB that are no longer in the corpus.")
    args = parser.parse_args()
    if not args.db_url:
        print("ERROR: no --db-url and $DATABASE_URL is unset", file=sys.stderr)
        sys.exit(1)
    if not args.corpus_dir.exists():
        print(f"ERROR: corpus dir not found: {args.corpus_dir}", file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run(args.corpus_dir, args.db_url, args.prune))


if __name__ == "__main__":
    main()
