# Re-home Ticket: Skill-Routing Offer-Confidence Floor (deferred from feedback quick-wins)

**Opened:** 2026-06-24 · **Status:** OPEN · **Owner:** routing + clinical lead
**Origin:** PR `fix/2026-06-24-feedback-quick-wins`, Task 6. The offer-floor was implemented (commit 893b3a3) then reverted (commit 3bd739e) after it suppressed a legitimate match. This ticket re-homes it as a measured change.

## Why it was deferred (the evidence)
Task 6 added an offer-confidence floor: any semantic skill match scoring below `SKILL_OFFER_CONFIDENCE_FLOOR` (default 0.50) was routed to freeflow instead of being offered. Intent: stop off-target single offers (the "money worry / grief" mis-offers in the 58-user feedback).

It over-suppressed. The phrase **"I feel like there is something inherently broken in the way I am built"** scores **0.4843** for `cbt_thought_record` — **above** the calibrated routing threshold (`SEMANTIC_THRESHOLD = 0.4593`) but **below** the 0.50 floor. It is a legitimate, on-target CBT match (a self-critical-schema disclosure with no keyword overlap), encoded by the existing `@slow` test `test_skill_select.py::test_semantic_cbt_inherently_broken_phrase`. The floor sent it to freeflow = a crisis-adjacent **recall regression** on a clinical path.

Root cause: a **blanket score floor cannot separate "on-target but modest score" (0.4843) from "off-target noise."** BGE-M3 legitimately scores some good matches in the 0.46–0.50 band — the `skill_select.py` calibration note even warns *"do not raise threshold into the somatic noise band (0.46–0.47)."* So 0.50 was a guess, not a calibrated value.

## What ships instead (this PR)
Only the **runner-up tightening** (Task 6 Step 3) ships: a second/runner-up skill is offered only when it is both strong (`SKILL_RUNNER_UP_MIN`) and close to the primary (`SKILL_RUNNER_UP_MARGIN`). That alone fixes the reported **double-offer** symptom (money + grief), which was a runner-up problem. The single off-target-primary case is left to this ticket.

## Requirements for the re-homed change
1. **Calibrate, don't guess.** Derive the floor (or a better mechanism) from `scripts/calibrate_threshold.py` — the **skill-routing** calibration tool (NOT `scripts/calibrate_retrieval_threshold.py`, which is the knowledge-retrieval abstain tool Task 5 used; different subsystem). Re-run it after any change, per the in-file convention.
2. **First labeled fixture:** the 0.4843 CBT case above is an **in-scope (should-offer)** label. Add it to the calibration/eval set so any candidate floor must keep offering it. Pair it with confirmed **off-target** cases (e.g. the money/grief mis-offers from the feedback) as out-of-scope labels.
3. **A blanket score floor is likely insufficient** (it cannot separate the two classes that overlap in 0.46–0.50). Evaluate alternatives: per-cluster floors, a rerank/precision gate on the offer decision, or an abstain signal distinct from the routing score. The acceptance bar is: suppresses the off-target labels without dropping any in-scope label.
4. **Light clinical confirm** of the final value/mechanism before deploy (it changes whether skills are offered).
5. Reintroduce the `SKILL_OFFER_CONFIDENCE_FLOOR` config knob (removed in 3bd739e) only alongside the calibrated value, so there is no orphaned constant.

## Acceptance criteria
- Calibrated routing-offer gate that, on the labeled set, suppresses the off-target offers AND offers the 0.4843 CBT case (and the existing `@slow` semantic-offer tests stay green, unmodified).
- Clinical sign-off recorded.
- Recalibration step documented.

## Links
- Plan: `docs/superpowers/plans/2026-06-24-feedback-quick-wins.md` (Task 6)
- Evidence + decision: progress ledger `.superpowers/sdd/progress.md` (Task 6 FIX / OPEN ISSUE entries)
- Related: skill-routing calibration note in `src/sage_poc/nodes/skill_select.py` (SEMANTIC_THRESHOLD provenance)
