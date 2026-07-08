"""Thin-margin abstain monitor for the interim cosine abstain gate (2026-07-03).

The gate threshold (0.42) sits only ~0.008 above the weakest calibrated positive
(0.4283, khaleeji/lexical), so a production paraphrase of that class can be falsely
abstained. This is a READ-ONLY check for any such case in the danger band.

POC POSTURE — ON-DEMAND, NOT SCHEDULED. The durable control is the audit column
itself: migration 007 records knowledge_top_similarity on every turn, permanently,
so any false abstention is retrospectively visible whenever anyone looks. Run this
manually BEFORE demos/pilot sessions and AFTER any knowledge-path change (30s, no
infra). Scheduled monitoring is a production-hardening item (see spec §3.8) bundled
with /health/version + the LLM-observability stack.

Lever on any LEGITIMATE in-band abstention: nudge SAGE_COSINE_ABSTAIN_THRESHOLD down,
or fail-open at 0.0 (config flip, no code deploy).

Run: railway run uv run python -m scripts.monitor_abstain_band
"""
import os, asyncio, asyncpg


async def main():
    c = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await c.fetch("""
        select inserted_at, session_id, knowledge_query_raw as q, knowledge_top_similarity as sim
        from session_audit
        where knowledge_abstain = true
          and knowledge_top_similarity >= 0.40 and knowledge_top_similarity < 0.44
          and inserted_at > now() - interval '24 hours'
        order by inserted_at desc
    """)
    print(f"[abstain-band-monitor] {len(rows)} abstained turn(s) in the 0.40-0.44 band, last 24h")
    for r in rows:
        print(f"  {str(r['inserted_at'])[:19]}  sim={r['sim']:.4f}  session={str(r['session_id'])[:8]}  q={r['q']!r}")
    if not rows:
        print("  CLEAN — no in-band abstentions.")
    else:
        print("  REVIEW each: is any a LEGITIMATE query wrongly abstained? If yes -> lower threshold / fail-open 0.0.")
    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
