# Phase 0 — POC Working Assumptions

**Date:** 2026-06-23
**Authorized:** product owner (POC velocity decision) — make sensible defaults, demonstrate in the POC, gather test-user feedback, finalize numbers after. These are **assumptions, not final values**; all are revisited post-feedback.

## Assumptions adopted

1. **G6 #4 mis-route bar → POC-phased arm.** Accept "0 observed, ≤4.6% upper bound @ N≈65" for the POC; the ≤1% (~300-case) bar is deferred to pre-pilot. **→ `ar/id_oos` cell sizes to ~65.** Schedule gate released on this basis.
2. **A1 §3a crisis-adjacent dialect → conservative-escalate default STANDS (POC safety posture).** Routing does not attempt crisis-adjacent dialect; those over-escalate via Node 1 / task #21. The precise native-dialect line is deferred to post-POC. **This is the *safe* simplification (over-escalation, never under-routing).** Must be finalized by a native-dialect clinician + task #21 before any pilot.
3. **A2 eval set → engineering/AI-drafted POC-grade.** Native review (F6) + clinical sign-off deferred to post-test-user-feedback. **Any baseline number from this set is POC-indicative, NOT certified** — it demonstrates the harness and the routing delta, it does not certify gate 6.

## Invariants preserved (not relaxed for the POC)

- **Crisis path (Node 1) untouched.** The routing change is `skill_select`-only; crisis never enters it.
- **Routing improvement ships behind `SKILL_ROUTING_V2` (default off in prod)** until the POC demonstrates the delta. Production routing is unchanged until we flip it deliberately.
- **No silent defaults in the harness** still holds — the assumed values above are *recorded* values, not absent ones.

## What "finalize after feedback" means

Test users exercise the improved routing in the POC; their sessions surface real misroutes and ABSTAIN cases. Those become the signal to (a) finalize #4's arm, (b) commission the native-dialect §3a determination, (c) replace the POC eval set with a native-reviewed + clinically-signed one. Until then, we build and demonstrate.
