# Clinical session decision record — Component 2 + crisis-state (D1–D5)

**Date:** 2026-07-09. **Authority:** clinician rulings relayed + endorsed by product owner. **Source thread:** #205 (trace + packet), #210 (the shipped #205 backend fix). This is the primary record; engineering executes against it, does not infer beyond it.

## D1 — TD3 amendment
**APPROVED**, scoped to **continuation-context crisis phrasing only** (positive + negative examples); **no general reopen**. **Dual-clinician labeling** required on ambiguous tiers.
- **Open blank — re-lock date.** Not set here (decoupled from labeling per ruling). Constraint: must close **before Experiment 4.2 Week 8** (MARBERT fine-tune window). Pinned once the labeling working session is scheduled.
- Engineering: candidate phrasing set ships with a tier-ambiguity column for the second labeler. D1 approval unblocks the **process**; labeling is a separate working session, not a sign-off blocker.

## D2 — Rescued-turn templating
Safety floor is **fixed and not reopenable**: any `crisis_response` turn keeps **full helpline + tap-to-call**. Tier-aware variation is **tone/framing only**. **Default: monitoring-rescued `tier=none` turns use the existing T2 script unchanged** until a warmer variant is authored via CMS (optional, no deadline).
- Engineering: the floor is already enforced by the #205 affordance-follows-path fix (`4acecf8`); adding an explicit non-reopenable test `crisis_response ∈ path ⇒ card + tel present`.

## D3 — Session-level sticky crisis state
**ADOPT.** Deterministic write, audited, PDPL-visible.

| param | value (default, accepted) |
|---|---|
| activation | any `crisis_response` fires |
| effect | mandatory monitoring on all subsequent turns this session |
| duration | remainder of session |
| reset | session end |

- Implication (recorded, not a redline): with D2's floor, every subsequent turn this session carries the full crisis card. This is the protective default and is the mechanism that rescued #205.
- Engineering: harden the currently-emergent `crisis_state=monitoring` into an explicit named sticky flag with these exact semantics; audit in `session_audit`; cross-session history remains governed by persisted-flags / flag-lifecycle, not this flag.

## D4 — Review queue
**DEFERRED (not "not required").** L2 flags persist as **logs only**; no monitoring flow now. Conditions:
- (a) **Revisit trigger:** any expansion beyond controlled/demo exposure → a named owner + cadence becomes **mandatory** (hard gate on the expansion checklist).
- (b) **Interim tripwire:** single notification on any L2 flag from a **non-test** user.
- (c) Recorded as **deferred for DPIA** purposes.

## D5 — Continuation-recall KPI
**KPI split ENDORSED.** **System-level** continuation-crisis target = **≥95%** (clinician-owned, same guarantee as first disclosure). **Node-1 sub-target** is engineering-derived + countersigned — and is scoped to the **context-free subset ONLY** (see labeling field 5): a single-utterance classifier cannot be held to context-dependent meaning it cannot see, and doing so sets an unmeetable bar that masks where real coverage comes from. Context-dependent coverage is measured at **system level** (via the D3 sticky-state / monitoring layer), not at Node 1.
- Engineering: continuation-context becomes a separate gated line in the crisis-recall harness; the Node-1 gate runs on the context-free subset, the ≥95% system gate on the full continuation set.

## D1 execution — labeling schema + additive scope (folded from the 2026-07-09 relay)
**Additive, not re-labeling.** The locked TD3 corpus stays as-is; the delta is a NEW continuation-context set labeled from scratch. Re-labeling existing locked items is **ruled out** (scope creep against change-control) unless the session surfaces a direct contradiction. One exception: pull **~20–30 existing TD3 items as calibration anchors** so new tier labels sit on the locked corpus's scale (prevents drift).

**Four sources, one schema.** Sources: (1) the #205 exemplar; (2) every L2-flagged miss the backstop has collected (production misses > synthetic — weight toward these); (3) clinician-authored continuation phrasings (their taxonomy — legitimate); (4) a **negative set** — continuation-shaped non-crisis phrasings ("ما عاد عندي رغبة" completed with mundane objects, disengagement/fatigue, skill-exit requests) to protect precision.

**Per-item schema — 5 fields:** (1) crisis yes/no; (2) tier; (3) dialect validity (native-Khaleeji tick); (4) positive/negative membership; (5) **context-dependency — the critical field: does the crisis reading require the preceding conversation, or is it standalone?**

**Field 5 routing (why it's critical):** MARBERT classifies utterances. Context-required items are only learnable if classifier input includes a context window — training on them without context teaches the model to fire on ambiguous phrasings everywhere (precision disaster). So each item routes by field 5:
- **context-free** → straight into the MARBERT fine-tune (and counts toward the Node-1 sub-target).
- **context-required** → EITHER motivate a context-window input change to Node 1 (an Exp 4.2 architecture decision, with a latency implication against the <50ms Layer-1 budget) OR be formally assigned to the **D3 sticky-state / monitoring** layer as their catch mechanism.

**Session process:** dual-label everything flagged in the tier-ambiguity column; adjudicate disagreements live; record **inter-rater agreement on the tier field** (continuation tiers are exactly where competent clinicians diverge — the disagreement rate itself measures how classifier-learnable this class is). **Volume:** ~100–200 positives + a comparable negative set, weighted toward backstop-collected production misses.

## Status after this record
- Signed/actionable now: **D2, D4, D5** fully; **D3** adopted (implementation ticketed); **D1** approved (process unblocked).
- One open blank: **D1 re-lock date**, gated on scheduling the labeling working session, bounded by Exp 4.2 Week 8.
- Implementation tickets: D3 sticky-flag, D4 non-test tripwire + expansion gate, D5 continuation eval, D2 safety-floor test.
