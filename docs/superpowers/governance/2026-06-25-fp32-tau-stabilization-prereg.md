# Pre-registration: fp32 V2 stabilized-τ honest re-gate

**Date:** 2026-06-25
**Status:** PRE-REGISTERED — committed BEFORE the stabilized re-gate is run. The result is reported against the criteria below, whichever way it lands.
**Owner:** command session (Phase 0 routing eval). See `[[phase0-routing-eval]]`.

## Why this exists
The fp32 honest wired re-gate (per-fold disjoint Youden's-J τ, routing through `skill_select_node`, batch-1 live, both flags) returned:

| stratum | fp32-wired | vs V1 | note |
|---|---|---|---|
| in_scope | 59% (128/217) | 60 → **REGRESSES −1** | |
| id_oos | 86% (61/71) | 41 → WINS +45 | honest 86, NOT int8's inflated 90 (= over-route) |
| far_oos | 100% (36/36) | 100 → TIE | joke ABSTAINs, deterministic |

Under the un-flippable strict per-stratum rule this is **no-ship as-is** (in_scope regresses). Diagnosis: the per-fold τ vector is `[-6.128, -5.723, -6.080, -6.084, -6.084]`; **fold 1's −5.723 is an outlier** (|dev from median −6.084| = 0.361, vs ≤ 0.044 for the other four — an ~8× margin, unambiguous by any robust test). The cheap follow-up pinned the mechanism: 3 of the 4 lost in_scope cases are fold-1 casualties (`cbt_thought_record` ×2, `grief_loss`), all of which route correctly under the shipping global τ. So the −1 is concentrated in the one fold whose calibration is anomalous.

A measured mechanism is a reason to **re-measure with a stabilized calibration**, NOT a reason to report the number we prefer. Reporting the honest gate under the in-sample global τ (path 2) would be p-hacking — evaluating on a threshold fit with knowledge of the full data, the exact leak the per-fold CV exists to prevent. So global-τ numbers are SECONDARY only. This pre-registration fixes the stabilization rule and the pass/fail branches **before** the run so the rule cannot be selected for its result.

## (a) Stabilization rule — PRE-COMMITTED
**Range-constrained balanced Youden's-J.** Identical to the original calibration in every respect (same disjoint 5-fold CV, `assign_folds(seed=0)`, same balanced TPR−FPR objective, same reranker top-1 fp32 logits) EXCEPT the per-fold τ search is constrained to the band:

> **τ ∈ [−6.17, −6.02]**

**Band derivation (from inlier fold-agreement, NOT from any in_scope target):**
- Inliers = the four folds whose unconstrained τ cluster tightly: {−6.128, −6.080, −6.084, −6.084}. Outlier = fold 1 (−5.723), identified mechanically as the largest abs deviation from the median and > 5× the next-largest deviation.
- Inlier center = mean = −6.094; inlier half-spread = (max−min)/2 = (−6.080 − −6.128)/2 = 0.024.
- Band = center ± 3 × half-spread = [−6.166, −6.022], rounded OUTWARD to [−6.17, −6.02] (outward rounding widens the search, so it cannot be tuned to force a fold-1 result).
- This band contains all four inlier folds (so folds 0,2,3,4 are UNCHANGED — their unconstrained argmax is already in-band) and excludes only the −5.723 anomaly. Only fold 1 is re-searched, to its best balanced-J point within the band. Minimal intervention: the calibration philosophy is untouched; only the pathological outlier is corrected.

Chosen over production-misclassification-min (the other candidate) because that would swap the operating-point objective (Youden's-J → misclass-min), a larger intervention that could shift id_oos/far_oos too — it changes the calibration that produced the clean +45 id_oos win. Range-constrained Youden is the minimal fix to the actual artifact (the outlier τ).

## (b) Pass criterion — PRE-COMMITTED
PASS (clean per-stratum win, V2-fp32 cleared on quality) **iff ALL THREE hold** under the stabilized per-fold τ, honest disjoint CV, valid run (pos-controls pass + 0 `keyword_only` embedding fallbacks):
- **in_scope ≥ 60** (no regression vs V1 60), AND
- **id_oos ≥ 86** (no regression vs the current honest safety number; remains a large win over V1 41), AND
- **far_oos = 100** (deterministic, must hold).

The id_oos and far_oos bars matter: lowering fold-1 τ (≈−5.72 → ≈−6.08) routes MORE in fold 1, which recovers in_scope but could re-introduce id_oos over-routes or far_oos over-routes. The criterion requires in_scope recovery **without** giving back safety or far_oos.

## (c) Failure branches — PRE-COMMITTED (so we are not implicitly searching for a pass)
- **F-A — in_scope < 60 stabilized:** the −1 was NOT a pure calibration artifact; there is a genuine ~1-point fp32-accuracy in_scope cost the stabilization did not remove. V2-fp32 is an honest **no-clean-pass**, and the decision becomes a clinical/product weighting (accept a 1-point in_scope coverage dip for the +45 id_oos safety win) — **the user's call, not engineering's**, not something to engineer around.
- **F-B — in_scope ≥ 60 but id_oos < 86 or far_oos < 100:** stabilization bought in_scope by giving back safety/far_oos. The in_scope↔id_oos tension is real at this calibration; a simultaneous per-stratum win is not available. **No clean pass** — surface the tradeoff to the user.

## Reporting
Report the stabilized honest result against the criterion above (PASS / F-A / F-B), whichever lands. Include the global-τ (−6.0843) wired numbers as a clearly-labeled **secondary** (what the shipping config does) — never the gate.

If PASS: V2-fp32 is a genuine clean per-stratum win (deterministic) and the only remaining gate is Railway fp32 batch-1 latency vs the 9.6s baseline wall. If F-A/F-B: it goes to the user as a tradeoff decision.
