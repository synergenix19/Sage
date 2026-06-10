"""
Pilot deployment gate: blocks while any crisis-recall gap remains unresolved.

This is NOT a pytest test. It is a hard deployment pre-check that must be wired
into CI as a separate step before any user-facing pilot deployment.

The three gaps in _TP_PASSIVE_SI_RECALL_GAPS are registered in the test suite
with known_fn=True, which causes pytest to mark them as xfail — they pass green
while the system keeps missing. That is correct for regression tracking (the test
flips to XPASS when detection starts working), but a passing test suite is NOT
evidence the system is safe to pilot. This script is the loud gate that blocks
deployment while any recall gap is unresolved.

Resolving a gap means:
  1. The SK-EN-002 fix has clinical sign-off.
  2. The fix ships and the probe now detects correctly.
  3. The known_fn=True marker is removed from the test case.

All three conditions must be met before this gate clears.

Usage:
  uv run python scripts/check_pilot_gate.py

Exit codes:
  0 — no unresolved crisis-recall gaps; gate clears
  1 — unresolved gaps found; pilot deployment blocked

See: docs/superpowers/escalations/2026-06-10-node1-crisis-recall-gap.md
"""
from __future__ import annotations
import sys

sys.path.insert(0, ".")

from tests.fixtures.safety.cases import _TP_PASSIVE_SI_RECALL_GAPS

ESCALATION_DOC = "docs/superpowers/escalations/2026-06-10-node1-crisis-recall-gap.md"

unresolved = [c for c in _TP_PASSIVE_SI_RECALL_GAPS if c.known_fn]

if not unresolved:
    print("PILOT GATE: PASS — all Node 1 crisis-recall gaps resolved.")
    sys.exit(0)

SEP = "=" * 70
print(SEP)
print("PILOT GATE: BLOCKED")
print()
print(f"  {len(unresolved)} unresolved Node 1 crisis-recall gap(s).")
print()
print("  These are recall misses on the highest-stakes detection path.")
print("  A user expressing veiled suicidal ideation receives a warm")
print("  empathic response instead of crisis detection and escalation.")
print()
for case in unresolved:
    gap_id = case.note.split(":")[0] if case.note else "unknown"
    print(f"  [{gap_id}]")
    print(f"    phrase : {case.phrase!r}")
    print(f"    rule   : {case.rule_hint}")
    print()
print("  To clear this gate:")
print("  1. Obtain clinical sign-off on the SK-EN-002 fix for each gap.")
print("  2. Ship the fix and verify the probe now detects correctly.")
print("  3. Remove the known_fn=True marker from the test case.")
print()
print(f"  Escalation doc: {ESCALATION_DOC}")
print(SEP)
sys.exit(1)
