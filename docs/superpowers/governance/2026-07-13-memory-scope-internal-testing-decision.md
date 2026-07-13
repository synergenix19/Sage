# Memory scope during internal testing — decision memo (for Vee: approve / edit)

**Filed:** 2026-07-13 · **Status:** decision recorded as directed, **pending sign-off** · **Owner:** PO / clinical lead (Vee) · **Links:** PR #291 tickets (`therapeutic-profile-persistence-nonfunctional`, `techniques-used-phantom-read`, `guard-clinical-flag-persistence-config`), PR #290 (shipped prod `6e8f713`), memory `profile-persistence-nonfunctional`

## Context (verified, not asserted)
Three independent sweeps (master `a0721c0`/`6e8f713`, direct source re-verification) established: the **cross-session** therapeutic-profile persistence layer is **non-functional end-to-end** — `observations`, `mood_trajectory`, `techniques_used`, `persisted_clinical_flags` are all written-not-read or read-not-written; the repo's own `test_continuation_recall.py` measures `cross_session_residual_rate == 1.0  # EXPECTED-MISS`. What demonstrably works and moves model output (live-LLM `test_a4_gate_full_path.py`): the **within-session window (last 8 turns)** + **honest-absence governance** (L0 memory clause v2.5.0 + absent-memory sentinel). PR #290 (stop the silent `observations` wipe) shipped to prod 2026-07-10.

## Decision (as directed — internal-testing posture)
1. **In-session memory is required and is the priority.** The within-session window + honest-absence governance must be confirmed **working AND activated in the running system**, not assumed from unit tests.
2. **Do NOT build new cross-session capabilities.** No injection path for the dead profile fields; no reliance on session-summary recall as a feature; the cross-session "twin" stays dormant. Ensuring what we already built *works and is on* takes priority over adding surface.
3. **DPO / retention is not a gating concern right now** — we are in internal testing with no real users. The retention/erasure/residency work (findings #3/#4/#5) is acknowledged and **parked**; it re-enters as a hard gate **before any real-user or pilot-cohort exposure**.
4. **Persistence config stays FROZEN.** This is a clinical-safety guardrail (the `psychotic_disclosure`/`_FLAG_DESCRIPTIONS` inconsistency — enabling makes 5 flags model-visible L5 prose and the 6th a silent routing seed), independent of DPO, and holds regardless of testing phase.

## What this means concretely
**IN SCOPE NOW — verify + activate what's built:**
- Behaviorally confirm in-session recall + honest-absence actually fire in prod (drive a disclosure→recall turn and an absent-recall turn against `6e8f713`), not just green unit tests.
- Fix the `techniques_used` within-session defect **iff** any skill exercises `prior_exposure` (it is a built-but-broken *within-session* behavior — squarely "make what we built work"). Otherwise log-and-defer stating that condition.

**DORMANT — do not build or activate:**
- Cross-session profile injection, session-summary-recall-as-feature, flag cross-session persistence. Leave the writes dormant (no urgent rip-out — DPO is parked), do **not** wire the reads, do **not** flip the config.

**DEFERRED (re-enters before real users):**
- Retention / erasure / data-residency (findings #3/#4/#5).

## Follow-on when internal testing → real users
DPO/retention becomes a gate again. At that point the fork returns: either build cross-session properly (injection + present-side eval + flag lifecycle + clinical sign-off) **or** stop writing the unused sensitive fields and close the retention gap by not-collecting. Not a decision for today.

## Sign-off
- [ ] **Vee (PO / clinical lead):** approve / edit the internal-testing posture above.
- The frozen-config guardrail needs no sign-off to *remain*; *unfreezing* later requires clinical sign-off + CF-006 reconciliation into `_FLAG_DESCRIPTIONS` + a flag-lifecycle (expiry/active-vs-historical) model + residency.
