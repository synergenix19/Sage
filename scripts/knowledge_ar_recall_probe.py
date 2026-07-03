"""AR-recall probe: recall@5 + MRR, rewrite-off vs rewrite-on, split by
variance_type. Rewrite-off calls _search directly (raw query); rewrite-on calls
retrieve() (template normalizes). See 2026-07-03 rewriter-wiring spec §5."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path

_PROBE = Path(__file__).parent.parent / "tests" / "fixtures" / "knowledge_probe" / "ar_recall_probe.jsonl"


def recall_at_k(gold_ids, retrieved_ids, k=5) -> float:
    top = retrieved_ids[:k]
    return 1.0 if any(g in top for g in gold_ids) else 0.0


def reciprocal_rank(gold_ids, retrieved_ids) -> float:
    for i, rid in enumerate(retrieved_ids, start=1):
        if rid in gold_ids:
            return 1.0 / i
    return 0.0


def load_rows(path=_PROBE):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


async def score_probe(rows, retrieve_fn) -> dict:
    """retrieve_fn(query, language) -> list[source_id]. Aggregates recall@5 + MRR
    overall and per (dialect_tag, variance_type) cell."""
    buckets: dict = {}
    for row in rows:
        ids = await retrieve_fn(row["query"], "ar")
        r = recall_at_k(row["gold_article_ids"], ids, k=5)
        rr = reciprocal_rank(row["gold_article_ids"], ids)
        for key in ("overall", f'{row["dialect_tag"]}/{row["variance_type"]}'):
            b = buckets.setdefault(key, {"n": 0, "recall_sum": 0.0, "rr_sum": 0.0})
            b["n"] += 1
            b["recall_sum"] += r
            b["rr_sum"] += rr
    return {
        k: {"n": b["n"], "recall_at_5": b["recall_sum"] / b["n"], "mrr": b["rr_sum"] / b["n"]}
        for k, b in buckets.items()
    }


async def _main():
    import os
    import asyncpg
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

    # Build our own pool from DATABASE_URL — do NOT import `server.app`: its
    # app.state._db_pool is only populated by FastAPI startup hooks, so a
    # standalone run would get None and crash on the first query. Use the same
    # connection string the server uses (server.py:212, :240).
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not set — cannot run the AR-recall probe.")
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=4)
    try:
        repo = PostgresKnowledgeRepository(pool)
        rows = load_rows()

        async def rewrite_off(query, language):
            res = await repo._search(query, language=language, top_k=5)   # raw query, no normalization
            return [p.source_id for p in res.passages]

        async def rewrite_on(query, language):
            res = await repo.retrieve(query, language=language, top_k=5)   # template normalizes
            return [p.source_id for p in res.passages]

        off = await score_probe(rows, rewrite_off)
        on = await score_probe(rows, rewrite_on)
        print(json.dumps({"rewrite_off": off, "rewrite_on": on}, ensure_ascii=False, indent=2))
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(_main())
