"""Measure whether KNOWLEDGE_ABSTAIN_THRESHOLD (RRF score) can separate
relevant info questions from off-topic ones, against the live corpus.

Unlike calibrate_retrieval_threshold.py (session-summary cosine), this runs the
ACTUAL hybrid RRF retrieval (PostgresKnowledgeRepository) used by Node 6, so the
scores are on the real scale the abstain constant is compared against.

Run: DBURL=... uv run python scripts/calibrate_knowledge_threshold.py
"""
import asyncio
import os

import asyncpg

from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

# (query, language, expected_topic_prefix-or-None). None = off-topic, should abstain.
RELEVANT = [
    ("Can you explain what anxiety is and why my body reacts the way it does?", "en", "anxiety"),
    ("what is CBT and how does it help with anxiety", "en", "cbt"),
    ("what are the symptoms of depression", "en", "depression"),
    ("I have been feeling really stressed lately, how do I cope", "en", "stress"),
    ("what is mindfulness and how does it work", "en", "mindfulness"),
    ("I can't sleep at night, my mind keeps racing", "en", "sleep"),
    ("how do I cope with grief after losing someone", "en", "grief"),
    ("can you teach me a breathing exercise to calm down", "en", "breathing"),
    ("how do I build more self compassion", "en", "self-compassion"),
    ("ما هي اعراض الاكتئاب؟", "ar", "depression"),
    ("كيف اخفف التوتر والضغط", "ar", "stress"),
    ("كيف اتعامل مع القلق", "ar", "anxiety"),
]

OFF_TOPIC = [
    ("what time does the pharmacy close today", "en"),
    ("how do I cook rice properly", "en"),
    ("can you help me write a cover letter for a job application", "en"),
    ("what is the best phone to buy this year", "en"),
    ("where can I find job platforms in the UAE", "en"),
    ("recommend a good restaurant near me", "en"),
    ("عطني منصات للوظايف في دولة الامارات", "ar"),
    ("كيف اطبخ الرز", "ar"),
]


async def main():
    pool = await asyncpg.create_pool(os.environ["DBURL"], min_size=1, max_size=3)
    repo = PostgresKnowledgeRepository(pool)

    print("=" * 78)
    print("RELEVANT — should retrieve a topical article (high top RRF)")
    print("=" * 78)
    rel_scores = []
    for q, lang, topic in RELEVANT:
        res = await repo.retrieve(q, language=lang, top_k=3)
        top = res.passages[0] if res.passages else None
        score = top.relevance_score if top else 0.0
        sid = top.source_id if top else "(abstain)"
        hit = "✅" if (top and topic and sid.startswith(topic)) else f"⚠️ got {sid}"
        rel_scores.append(score)
        print(f"  {score:.4f}  {hit:<22} exp={topic:<14} [{lang}] {q[:46]}")

    print()
    print("=" * 78)
    print("OFF-TOPIC — should abstain (low top RRF, ideally below threshold)")
    print("=" * 78)
    off_scores = []
    for q, lang in OFF_TOPIC:
        res = await repo.retrieve(q, language=lang, top_k=3)
        top = res.passages[0] if res.passages else None
        score = top.relevance_score if top else 0.0
        sid = top.source_id if top else "(abstain)"
        off_scores.append(score)
        print(f"  {score:.4f}  top={sid:<20} [{lang}] {q[:46]}")

    print()
    print("=" * 78)
    print("GAP ANALYSIS")
    print("=" * 78)
    min_rel = min(rel_scores)
    max_off = max(off_scores)
    gap = min_rel - max_off
    print(f"  lowest RELEVANT top score:   {min_rel:.4f}")
    print(f"  highest OFF-TOPIC top score: {max_off:.4f}")
    print(f"  gap:                         {gap:.4f}")
    print(f"  relevant range: {min(rel_scores):.4f} – {max(rel_scores):.4f}")
    print(f"  off-topic range: {min(off_scores):.4f} – {max(off_scores):.4f}")
    if gap > 0.005:
        mid = round((min_rel + max_off) / 2, 4)
        print(f"\n  CLEAN-ISH GAP → candidate threshold (midpoint) = {mid}")
    else:
        print("\n  NO USABLE GAP — RRF score cannot separate relevant from off-topic.")
        print("  Recommend gating on vector cosine distance, not RRF score.")
    await pool.close()


asyncio.run(main())
