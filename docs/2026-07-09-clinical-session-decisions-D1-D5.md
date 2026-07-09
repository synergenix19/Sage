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
**KPI split ENDORSED.** System-level continuation-crisis target = **≥95%** (same guarantee as first disclosure). Node-1 recall and system-level recall reported separately; continuation broken out.
- Engineering: continuation-context becomes a separate gated line in the crisis-recall harness at the ≥95% bar.
- _Note: the clinician's "three mechanics" detail was truncated in relay; confirm if substantive beyond process notes._

## Status after this record
- Signed/actionable now: **D2, D4, D5** fully; **D3** adopted (implementation ticketed); **D1** approved (process unblocked).
- One open blank: **D1 re-lock date**, gated on scheduling the labeling working session, bounded by Exp 4.2 Week 8.
- Implementation tickets: D3 sticky-flag, D4 non-test tripwire + expansion gate, D5 continuation eval, D2 safety-floor test.
