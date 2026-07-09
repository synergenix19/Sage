# DECISION REQUEST — V2 recall-vs-safety acceptance criterion (Task 5)

**Date:** 2026-07-07 · **To:** product owner + clinical lead · **From:** engineering (command session).
**This is a CRITERION decision, not a waiver request.** V2 does not pass the signed §5 flip gate; the gate's recall rule is strict (`v2.recall >= v1.recall`, no tolerance). Whether to accept the trade or revise the rule is yours — either is a change to signed criteria, so per Absolute Rule 1 it is a **flagged, approved, recorded deviation**, never a quiet reinterpretation.

## The trade, measured (committed corpus `5e6b86e`, validated driver, fp32, positive-control-passed)

| stratum | V1 | V2 | |
|---|---|---|---|
| **id_oos abstain** (safety) | 35.9% | **90.6%** | **+54.7** — over-routing of clinician-territory disclosures collapses **41 → 6 cases** |
| **far_oos abstain** | 100% | 100% | held |
| **in_scope recall** | 56.8% (109/192) | 52.1% (100/192) | **−4.7 (net −9)** |
| **harm gate** (iatrogenic) | **6/9 leak** | **1/9 leak** | V2 closes 5 of 6 live iatrogenic routes |

## What the recall "−9" actually is (the framing that matters)

It is a **net of larger churn**, and the losses are mostly soft:

- **28 lost** (V1 correct → V2 not): **19 → soft ABSTAIN** (V2 routes to Node 3 empathic clarification — recoverable in-conversation, "tell me more") + **9 → wrong route, all in-cluster** (adjacent techniques, e.g. `cbt_thought_record`→`cognitive_restructuring`, `grounding`→`mindfulness_body_scan`).
- **19 gained** (V2 correct, V1 was wrong-routed 15 / abstained 4).
- **Failure mode improves:** in_scope **wrong-routes drop 56 → 24**. V2 abstains (recoverably) where V1 routed to the wrong skill. Clinically, an empathic "tell me more" is a **softer failure than a confidently-wrong technique.**

So the honest read is not "V2 drops 9 users" — it is "V2 converts ~32 wrong-skill routes into recoverable abstains, at the cost of over-abstaining on 19 true in_scope cases and 9 in-cluster near-misses."

**The 9 wrong-routes (the only silent-miss kind), all in-cluster:** cbt→cognitive_restructuring; grounding→mindfulness_body_scan; grounding→box_breathing; dbt_tipp→grounding; mindfulness_body_scan→box_breathing; worry_time→cognitive_restructuring; act→values_clarification; psychoed_stress→PMR; financial_anxiety→worry_time. (The 19 soft-abstains span behavioral_activation ×4, psychoed_anxiety ×2, psychoed_stress ×2, financial_anxiety ×2, assertive_communication ×2, and singles.)

## Can τ fix it? (frontier — input, not a recommendation)

A τ region **exists** that would clear the recall gate: at **τ ≈ −7.0**, in_scope recall recovers to **58.9%** (above V1's 56.8% → `gate_recall` PASS) while id_oos abstain stays **68.8%** (still ~2× V1). **But three reasons τ-tuning is not the answer:**

1. **In-sample overfit.** The sweep scores τ on the same corpus — picking τ to clear the gate here is overfitting. The committed τ (−6.0843) was a held-out/CV Youden point. Any τ move requires the **full model-promotion recalibration** (held-out refit, determinism, both thresholds) — its own gated change, not an in-sample pick.
2. **Harm direction is opposite.** The harm gate needs *more* abstention (higher τ); recall recovery needs *lower* τ. Lowering τ toward −7.0 **keeps and likely adds** iatrogenic/id_oos routes → it does **not** fix the case-5 harm leak and works against the harm escalation. **τ cannot satisfy both gates at once.**
3. far_oos holds 100% across the whole range (not a constraint).

**Implication:** the harm leak is fixed by the **deterministic OCD veto** (see the harm escalation), not by τ; the recall question is a genuine clinical acceptance call, not a tuning problem.

## The decision (one of)

- **(a) Sign an explicit acceptance** of the bounded recall cost (net −9: 19 recoverable soft-abstains + 9 in-cluster near-misses; wrong-routes 56→24) in exchange for id_oos +54.7 and harm 6→1. V2 flips at the committed τ. Recorded as a signed deviation.
- **(b) Revise the gate criterion** from strict `v2.recall >= v1.recall` to **"recall within tolerance T"** (T ≥ 4.7pts clears this cell). Recorded as a signed criterion change to `gate_runner`.
- (c) Authorize a **held-out τ-recalibration** (model-promotion protocol) to seek a point clearing the strict gate — but note it trades against the harm gate and does not close the case-5 leak. Not recommended as the primary path.

## Honest note (reconciling the record)

The offline history called this a "clean per-stratum win" (in_scope 60 vs V1 66 labeled a "TIE"). Under the actual signed gate (strict `>=`), **60 < 66 would also have failed** — the historical narrative and the coded criterion have never agreed. This decision reconciles them: either the strict rule is the standard (and V2, like the offline result, does not pass without a signed acceptance), or the accepted standard is recall-within-tolerance (and it should be committed as such).

## Engineering recommendation (the call is yours)

The trade is **clinically favorable** — V2 fails more gracefully (wrong-routes halved), closes 5 of 6 live iatrogenic routes, and delivers a 2.5× id_oos safety gain — so **(a) or (b)** over (c). But "is −4.7 recall acceptable" is the clinician's to affirm, and the criterion change is the PO's to sign. Precondition for any post-fix re-gate to count: the **G6-signed `HarnessConfig` must be committed** (currently absent — the config is only test fixtures).
