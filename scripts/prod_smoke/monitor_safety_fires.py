"""Post-deploy heightened-monitoring window — day 1-3 after the 2026-07-17 safety relay (a3ca60f7).

The relay added ~26 new safety keywords across EN+AR. The NEW harm mode is the FALSE POSITIVE: a
benign Arabic idiom tripping the 998 medical prompt or the OCD veto — which the run #001 probes cannot
find (probes don't speak in the wild's phrasing). This tool surfaces the real fires for HUMAN review.

SCOPE (PDPL + clinical boundary): this reports AGGREGATE fire COUNTS and the session_ids to review in
the clinician_review_queue. It does NOT read/classify real user transcript content — that is the
clinician's job (D4 logs-only ruling was signed against LOW exposure; these detectors writing flags
is the strongest reason yet for a human to read that queue this week, even informally).

Run: python scripts/prod_smoke/monitor_safety_fires.py [--hours 24]
"""
import argparse, json, subprocess, sys

def _db():
    return json.loads(subprocess.check_output(["railway", "variables", "--json"], text=True))["DATABASE_URL"]

def q(db, sql):
    return subprocess.run(["psql", db, "-tAc", sql], capture_output=True, text=True).stdout.strip()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--hours", type=int, default=24); a = ap.parse_args()
    db = _db(); w = f"turn_started_at > now() - interval '{a.hours} hours'"
    # Exclude our own synthetic drives so counts reflect REAL traffic only.
    real = "session_id NOT LIKE 'prodsuite-%' AND session_id NOT LIKE 'live-replay-%'"
    print(f"=== safety-fire monitor · last {a.hours}h · real traffic (excl. prodsuite-*) ===\n")

    med = q(db, f"SELECT count(*) FROM session_audit WHERE gate_path='medical' AND {w} AND {real};")
    ocd = q(db, f"SELECT count(*) FROM session_audit WHERE node_path::text LIKE '%ocd_compulsion_veto%' AND {w} AND {real};")
    print(f"  medical-guard fires (998 prompt): {med or 0}")
    print(f"  OCD-compulsion veto fires:        {ocd or 0}")

    # session_ids for the clinician_review_queue (ids only — NOT content). Human reads the transcripts.
    for label, pred in (("medical-guard", "gate_path='medical'"),
                        ("ocd-veto", "node_path::text LIKE '%ocd_compulsion_veto%'")):
        ids = q(db, f"SELECT DISTINCT session_id FROM session_audit WHERE {pred} AND {w} AND {real} LIMIT 50;")
        n = len([x for x in ids.splitlines() if x])
        print(f"\n  {label}: {n} session(s) → CLINICIAN to review in clinician_review_queue for FALSE POSITIVES")
        if n:
            print("    " + ", ".join(ids.split()[:10]) + (" …" if n > 10 else ""))

    # crisis fire rate as a stability sanity-check (should be steady; a spike alongside new keywords is a flag)
    cr = q(db, f"SELECT count(*) FROM session_audit WHERE crisis_tier IS NOT NULL AND crisis_tier != 'T0' AND {w} AND {real};")
    print(f"\n  crisis fires (context/sanity): {cr or 0}")

    print("\n  ACTIONS (day 1-3): (1) clinician reads each medical/ocd fire above for FPs — a benign Arabic")
    print("  idiom tripping 998 or the veto is NEW harm. (2) Any FP → boundary case into the Tier-2 packet")
    print("  for V. (3) Rollback SHA if a systemic FP pattern emerges: 5b33a0e (minutes-decision).")
    print("  NOTE: near-miss band (utterances scoring close to firing) is where Tier-2 Gulf-vocab should aim;")
    print("  add a scored-but-not-fired log if the detector path supports it (follow-up).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
