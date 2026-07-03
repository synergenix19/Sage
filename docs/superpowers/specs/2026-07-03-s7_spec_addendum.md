# S7 Spec Addendum — Post-Crisis Classifier (2026-07-03)

Spec artifact riding `feat/crisis-tiering`. S7 is a POC extension beyond the v7 S1–S6 set; this
records what it is and the invariant that keeps it safe under tiering + de-escalation (W2).

## What S7 is
- **Module:** `src/sage_poc/nodes/post_crisis_classifier.py` (`evaluate_s7`).
- **When it runs:** only while `crisis_state == "monitoring"` (post-T2), once per turn, from `safety_check`.
- **Type:** LLM classification (not deterministic). Labels include `NEW_CRISIS` (re-escalate) and de-escalation readings.
- **Latency:** an LLM call on monitoring turns; must not gate the deterministic path.

## Invariant (Cardinal Rule 4) — binding, and tested
Deterministic detection (S1/S2/S3) runs **every turn, independent of `crisis_tier` and S7**. S7 is **additive only**:
1. It MAY re-escalate within monitoring (`NEW_CRISIS` → `crisis_response`) — an *additional* escalation signal, never the *only* one.
2. It gates **relaxation / step-down** (W2: `monitoring → supportive` needs S7-clear **AND** no S1/S3 fire for `STEP_DOWN_CLEAR_TURNS`).
3. It is **never the sole path to escalation**, and an **S7 failure/timeout can never suppress or downgrade a same-turn S1/S3 fire** — that turn still resolves T2.

## Tests (the three Cardinal-Rule-4 assertions — land with gate plumbing)
- S7 timeout **and** a same-turn S1 keyword fire → still routes **T2** (S7 failure cannot suppress S1).
- Step-down requires S7-clear **AND** no deterministic fire — S7-clear with an S1/S3 hit stays `monitoring`.
- `NEW_CRISIS` can escalate, but is never the only signal consulted on the turn.

These are forcing tests (inject the timeout + the fire), not stubbed-return assertions.
