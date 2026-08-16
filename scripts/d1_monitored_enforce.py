#!/usr/bin/env python3
"""D1 monitored-enforce window read (#338) — the honesty-clause instrument. Answer-class distribution is
DESCRIPTIVE (not thresholded) until n supports more; the two zero-tolerance rows are absolute halts.
Reads only anonymised enforce audit columns (screen_asked/answer_class/branch). Excludes synthetic sessions.
Usage: DATABASE_URL=... python scripts/d1_monitored_enforce.py"""
import asyncio, os, asyncpg
_EXCL = ("session_id NOT LIKE 'accept-%' AND session_id NOT LIKE '%reflip%' AND session_id NOT LIKE 'flip-%' "
         "AND session_id NOT LIKE 'd1-%' AND session_id NOT LIKE 'gate3-%'")
async def main():
    c = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        served = await c.fetchval(f"SELECT count(*) FROM session_audit WHERE screen_asked=true AND {_EXCL}")
        dist = await c.fetch(f"SELECT screen_answer_class a, count(*) n FROM session_audit "
                             f"WHERE screen_answer_class IS NOT NULL AND {_EXCL} GROUP BY 1 ORDER BY 2 DESC")
        disc = await c.fetchval(f"SELECT count(*) FROM session_audit WHERE screen_answer_class='contraindication_disclosed' AND {_EXCL}")
        print("D1 monitored-enforce read (real traffic; DESCRIPTIVE until n supports)")
        print(f"  screens served (screen_asked): {served}")
        print("  answer-class distribution:" + (" (none yet)" if not dist else ""))
        for r in dist: print(f"    {r['a']}: {r['n']}")
        print(f"  contraindication_disclosed (the population the old self-screen missed): {disc}")
        print("  ZERO-TOLERANCE (absolute halts — must stay 0):")
        print("    crisis-in-answer mishandled: monitor via crisis audit on screen-pending turns")
        print("    audit swallow (ScreenAuditError): monitor logs; a swallowed screen decision halts")
    finally:
        await c.close()
if __name__ == "__main__":
    asyncio.run(main())
