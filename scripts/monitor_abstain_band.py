"""Thin-margin abstain monitor (interim cosine gate, 2026-07-03).

The gate threshold (0.42) sits only ~0.008 above the weakest calibrated positive
(0.4283, khaleeji/lexical). This checks whether any LEGITIMATE query is being
falsely abstained in that danger band. Read-only.

OWNER: scheduled daily (first week) — see routine 'abstain-band-monitor'.
EXIT CRITERION: 7 consecutive days with 0 legitimate-query abstentions in-band
  -> drop to weekly, note in memory. Any legitimate in-band abstention ->
  lever: nudge SAGE_COSINE_ABSTAIN_THRESHOLD down or fail-open at 0.0 (no code deploy).
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
        print("  CLEAN — no in-band abstentions. (7 clean days -> drop to weekly.)")
    else:
        print("  REVIEW each: is any a LEGITIMATE query wrongly abstained? If yes -> lower threshold / fail-open.")
    await c.close()

if __name__ == "__main__":
    asyncio.run(main())
