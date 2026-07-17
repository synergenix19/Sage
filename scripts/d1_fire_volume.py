#!/usr/bin/env python3
"""D1 shadow-window fire-volume read (#338) — the accrual-period check-in instrument.

Run at each deploy-unrelated check-in so the N=40 approach is VISIBLE, not discovered. Reads ONLY the
anonymised shadow audit columns (PDPL-approved: class + route, no message content). Excludes synthetic
verification sessions so N is honest real traffic.

Usage:  DATABASE_URL=$(railway variables ... DATABASE_URL) python scripts/d1_fire_volume.py
Criteria: 2026-07-17-d1-shadow-window-criteria.md — close on N=40 TIPP turns OR 14-day cap, whichever first.
A 14-day cap reached BEFORE N=40 is itself a finding (fire-volume lower than expected → the trigger recall-band
question returns to Vee BEFORE the flip, per RULING 3, not after).
"""
import asyncio, os, asyncpg

_EXCL = ("session_id NOT LIKE 'd1-shadow-verify-%' AND session_id NOT LIKE 'd1-sr-identity-%' "
         "AND session_id NOT LIKE 'd1-graph-%'")
_WINDOW_OPENED = "2026-07-17"  # shadow flag flip; N counts from here


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        tipp = await conn.fetchval(
            f"SELECT count(*) FROM session_audit WHERE active_skill_id='dbt_tipp' "
            f"AND screen_shadow_action IS NOT NULL AND {_EXCL}")
        fired = await conn.fetchval(
            f"SELECT count(*) FROM session_audit WHERE screen_shadow_action='ask_screen' AND {_EXCL}")
        disc = await conn.fetchval(
            f"SELECT count(*) FROM session_audit WHERE screen_shadow_answer_class='contraindication_disclosed' "
            f"AND {_EXCL}")
        by_action = await conn.fetch(
            f"SELECT screen_shadow_action a, count(*) n FROM session_audit "
            f"WHERE screen_shadow_action IS NOT NULL AND {_EXCL} GROUP BY 1 ORDER BY 2 DESC")
        print(f"D1 shadow window (opened {_WINDOW_OPENED}) — fire-volume read")
        print(f"  N (real TIPP-routed shadow turns): {tipp} / 40   [close at 40 or 14-day cap]")
        print(f"  would-fire (ask_screen):           {fired}")
        print(f"  disclosure-population:             {disc}   [the number the old self-screen was missing]")
        if by_action:
            print("  by would-be action: " + ", ".join(f"{r['a']}={r['n']}" for r in by_action))
        if tipp == 0:
            print("  (window empty of real traffic so far — expected shortly after open)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
