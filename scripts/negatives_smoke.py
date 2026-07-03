"""Negatives smoke test of the live abstain gate. Off-domain queries with no relevant
corpus answer -> correct behaviour is abstain=True. Runs read-only against the DB in
DATABASE_URL. Valid at current corpus scale only (see RESULTS caveat)."""
import os, asyncio, asyncpg
from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

NEG = [
    ("en", "how do I file my income taxes this year?"), ("en", "what is the capital of Australia?"),
    ("en", "how do I fix a flat car tire?"), ("en", "what is the best recipe for chocolate cake?"),
    ("en", "how does photosynthesis work in plants?"), ("en", "how do I reset my wifi router password?"),
    ("ar", "كيف أطبخ الأرز بالبخار؟"), ("ar", "ما هي عاصمة اليابان؟"),
    ("ar", "كيف أصلح إطار السيارة المثقوب؟"), ("ar", "ما هو سعر صرف الدولار اليوم؟"),
    ("ar", "كيف أحجز تذكرة طيران؟"), ("ar", "ما هي أفضل وصفة للكيك؟"),
]

async def main():
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=4)
    repo = PostgresKnowledgeRepository(pool)
    ab = 0
    for lang, q in NEG:
        r = await repo.retrieve(q, language=lang, top_k=5)
        ab += r.abstain
        print(f"[{lang}] {'ABSTAIN' if r.abstain else 'LEAK'} sim={r.top_similarity} | {q}")
    print(f"\n{ab}/{len(NEG)} abstained")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
