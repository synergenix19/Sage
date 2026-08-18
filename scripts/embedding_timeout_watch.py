#!/usr/bin/env python3
"""Embedding-timeout degradation watch — the serving-side alert on session_audit.embedding_timeout.

REQUIRED by the owner ruling of 2026-08-18/19 (delta-characterization follow-up (b), R-5):
semantic-tier degradation was user-facing and silent pre-F4; this check is the alert on the
column migration 019 added and PR #463's audit writer populates.

Execution points (wiring):
  1. deploy_prod.sh runs this as a production PRE-FLIGHT GATE — a deploy cannot proceed
     without the alert path executing (or an explicit committed waiver, see the gate).
  2. Post-deploy checklist (deploy_prod.sh NEXT steps) runs it again against the new build.
  3. Continuous/scheduled execution rides the deferred-watchdog lane (production hardening);
     until that lands, every deploy boundary is an enforced alert point.

Exit codes: 0 = quiet (no degradation events in the lookback window);
            1 = ALERT: embedding_timeout events found (rows printed — investigate before deploying;
                each is a turn a real user got keyword-only routing);
            2 = CANNOT CHECK (column absent / DB unreachable) — loud by design: absence of the
                signal is not absence of the degradation.

Usage: python3 scripts/embedding_timeout_watch.py [--days 7]  (railway must be linked: DATABASE_URL)
"""
import argparse
import json
import subprocess
import sys


def _db_url():
    env_call = subprocess.run(
        ["railway", "variables", "--json"], capture_output=True, text=True,
        env={**__import__("os").environ, "RAILWAY_CALLER": "skill:use-railway@1.2.0"},
    )
    if env_call.returncode != 0:
        return None
    try:
        return json.loads(env_call.stdout).get("DATABASE_URL")
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    db = _db_url()
    if not db:
        print("embedding-timeout watch: CANNOT CHECK — DATABASE_URL unavailable (railway link?)", file=sys.stderr)
        return 2

    col = subprocess.run(
        ["psql", db, "-tAc",
         "SELECT 1 FROM information_schema.columns "
         "WHERE table_name='session_audit' AND column_name='embedding_timeout';"],
        capture_output=True, text=True)
    if col.returncode != 0:
        print(f"embedding-timeout watch: CANNOT CHECK — psql failed: {col.stderr.strip()}", file=sys.stderr)
        return 2
    if col.stdout.strip() != "1":
        print("embedding-timeout watch: CANNOT CHECK — column absent (apply migration 019). "
              "Absence of the signal is not absence of the degradation.", file=sys.stderr)
        return 2

    rows = subprocess.run(
        ["psql", db, "-tAc",
         f"SELECT session_id||' turn '||turn_number||' at '||inserted_at FROM session_audit "
         f"WHERE embedding_timeout IS TRUE AND inserted_at > now() - interval '{args.days} days' "
         "ORDER BY inserted_at DESC LIMIT 50;"],
        capture_output=True, text=True)
    if rows.returncode != 0:
        print(f"embedding-timeout watch: CANNOT CHECK — query failed: {rows.stderr.strip()}", file=sys.stderr)
        return 2

    hits = [l for l in rows.stdout.splitlines() if l.strip()]
    # Synthetic-session prefixes (smoke/instrument sessions; purge-managed test assets). A synthetic
    # event still evidences the degradation mechanism (measured live 2026-08-18: two tier-A smoke
    # turns served keyword-only in the post-restart cold-start window while the smoke passed green,
    # the warmup-silent-failure class) but must not abort every deploy, because post-deploy smoke
    # probes the cold-start window by construction. Real-user events are the hard alert.
    SYNTHETIC = ("smoke-", "prodconf-", "confassess-", "n1verify-", "functest-", "canary-")
    real = [h for h in hits if not h.strip().startswith(SYNTHETIC)]
    synth = [h for h in hits if h.strip().startswith(SYNTHETIC)]
    if synth:
        print(f"⚠️  {len(synth)} synthetic-probe embedding-timeout event(s) in the last {args.days} days "
              "(cold-start/warmup window class — mechanism live, no real user affected):")
        for h in synth:
            print(f"  {h}")
    if real:
        print(f"🚨 ALERT: {len(real)} REAL-SESSION embedding-timeout event(s) in the last {args.days} days — "
              "each is a real turn served with keyword-only routing (silent degradation class, "
              "see 2026-08-18-v6-v7-delta-characterization.md):")
        for h in real:
            print(f"  {h}")
        return 1

    if not hits:
        print(f"embedding-timeout watch: quiet — 0 events in the last {args.days} days (semantic tier undegraded).")
    else:
        print("embedding-timeout watch: no real-session events (synthetic-probe events above are informational).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
