# SIGNED DEVIATION (Absolute Rule 1) — revise the §5 flip-gate recall criterion

**Date:** 2026-07-07 · **Signed by:** product owner · **Type:** recorded deviation to a signed criterion (Absolute Rule 1) · **Supersedes:** the strict `v2.recall >= v1.recall` recall conjunct in `gate_runner.evaluate_flip`.

## Decision

The §5 flip-gate recall criterion is revised **structurally, not numerically.** A one-time acceptance of the −4.7 recall (option a) was rejected: it treats a **structural property** of the system as a waiver, guaranteeing the same conflict recurs at every future re-gate.

## Rationale (recorded so the criterion never again contradicts the architecture it gates)

The strict `v2.recall >= v1.recall` rule is **incoherent with what V2 is.** V2 is a selective-prediction / reject-option system: it abstains when confidence is below τ. The foundational result in the field (Chow's reject option) establishes that abstention systems **inherently trade coverage against misclassification risk** — a gate that forbids *any* recall cost forbids the abstention mechanism itself. This is why even the original offline "clean win" (in_scope 60 vs V1 66) would have failed the strict rule: the strict rule is the wrong standard for a reranker-with-ABSTAIN, not a bar V2 fails to clear.

## The revised criterion (the new signed standard)

A V2→prod flip requires ALL of:

1. **Harm gate: 0 leaks. HARD, unchanged, non-negotiable.** No harm-prone case (`critical`/`iatrogenic`/`safety_net`) routes to a skill. Post-veto V2 must measure clean (currently 1/9; the OCD veto closes it).
2. **id_oos abstain floor: no regression below V2's measured band (~90.6%).** This is the +54.7pp safety win the effort exists to capture.
3. **in_scope, split into its two components:**
   - **(i) wrong-route rate must not regress.** This is the *dangerous* in_scope failure (a confidently-wrong technique). V2 halves it (56→24, all residual misses in-cluster / adjacent-technique). Hard: no regression.
   - **(ii) raw recall within a signed tolerance `T = 5pp`.** `v2.recall >= v1.recall − 0.05`. The current −4.7 clears it. Justification: 19 of the 28 lost cases are **recoverable soft-abstains** landing in Node 3's empathic clarification — a *designed safe-failure path*, not a silent drop.

## Deployment condition (the honest hedge)

**Instrument and monitor the soft-abstain recovery rate in production** — does Node 3's clarification actually return the user to the right skill? The reject-option literature and clinical study evidence warn that when an AI abstains, *missed* cases for people who need help can increase; T=5pp assumes the soft-abstain path recovers, and that assumption must be **verified in prod, not asserted.** If recovery underperforms, that finding returns to the **product owner**, not to an engineering re-tune.

## Preconditions before any re-gate counts as authoritative

- **The G6-signed `HarnessConfig` (loss/delta/n_floor/τ) MUST be committed to the repo first.** It is currently absent (only test fixtures). Per the standing rule and [[feedback_primary_record_over_inference]], its values must come from the G6 signer — engineering will not infer them. The revised criterion above is implemented in `gate_runner`, but no post-fix re-verdict is authoritative until the signed config is in the repo.

## Implementation

`gate_runner.evaluate_flip` — replace the strict recall conjunct with: harm-gate hard-0 (existing) + id_oos abstain floor + in_scope (wrong-route-no-regress AND recall ≥ v1 − T). Add the prod soft-abstain-recovery metric to the audit. This code change is itself part of this signed deviation.

## Sequence after sign-off

Veto approved → hotfix to V1 prod → G6 `HarnessConfig` primary record supplied → both arms re-measured on the committed corpus → V2 re-verdict under THIS revised criterion → staged deploy. **If both decisions land as recommended, V2's remaining path is one content fix and one re-measurement.**
