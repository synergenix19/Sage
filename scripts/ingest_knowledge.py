"""Load clinical knowledge articles into the pgvector knowledge_articles table.

Usage:
    uv run python scripts/ingest_knowledge.py --corpus-dir path/to/corpus/

Each file in corpus-dir must be a JSON file matching the article schema:
    {
        "article_id":      "cbt-001",
        "language":        "en",
        "title":           "CBT Overview",
        "source_url":      "https://...",
        "citation":        "Beck (1979)",
        "content":         "...",
        "is_crisis_content": false
    }

Bilingual pairing: cbt-001-en and cbt-001-ar are paired by article_id.
Missing pairs emit a WARNING but do not abort the run.
"""
import argparse
import asyncio
import json
import pathlib
import sys

import asyncpg


async def _run(corpus_dir: pathlib.Path, db_url: str) -> None:
    from sage_poc.knowledge.ingestion import ingest_article, check_bilingual_pairing, validate_article_schema

    files = sorted(corpus_dir.glob("*.json"))
    if not files:
        print(f"ERROR: No JSON files found in {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    articles = []
    for f in files:
        article = json.loads(f.read_text())
        try:
            validate_article_schema(article)
            articles.append(article)
        except ValueError as exc:
            print(f"ERROR in {f.name}: {exc}", file=sys.stderr)
            sys.exit(1)

    for warning in check_bilingual_pairing(articles):
        print(warning)

    pool = await asyncpg.create_pool(db_url, min_size=2, max_size=5)
    total = 0
    for article in articles:
        n = await ingest_article(article, pool)
        print(f"  ✓  {article['article_id']} ({article['language']})  —  {n} chunk(s)")
        total += n

    await pool.close()
    print(f"\nIngested {len(articles)} articles → {total} total chunks.")


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base articles into pgvector.")
    parser.add_argument("--corpus-dir", required=True, type=pathlib.Path)
    parser.add_argument("--db-url", required=True, help="asyncpg DSN: postgresql://user:pass@host/db")
    args = parser.parse_args()
    asyncio.run(_run(args.corpus_dir, args.db_url))


if __name__ == "__main__":
    main()
