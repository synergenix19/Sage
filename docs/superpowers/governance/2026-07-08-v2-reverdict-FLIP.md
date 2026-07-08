# V2 Re-Verdict — FLIP (EN-first)

**Date:** 2026-07-08 · **Verdict: FLIP** — V2 (bi-encoder-with-exemplars → fp32 `bge-reranker-v2-m3`
cross-encoder → per-language τ → route-or-ABSTAIN) clears the PO-signed revised §5 criterion on every
conjunct. Both arms carry the arm-independent OCD-compulsion veto (the shipped safety posture). AR is
fail-closed to V1 (τ absent); this flip is the **English** arm only.

## Provenance chain (everything needed to know why V2 ships)

| Element | Value |
|---|---|
| Corpus (fixtures) | `5e6b86e` — `tests/fixtures/routing_eval/*.jsonl`, identical at branch tip (verified) |
| G6 gate config | `src/sage_poc/routing_eval/gate_config.py` @ `ec56c7c` — **SIGNED-BY Rohan (PO/G6), 2026-07-08**; loss `override_misroute=4.0` (label-proof insensitive, 0/480 override-fired), delta 0.05, n_floor 30, τ `{"en": -6.0843}` |
| Criterion source | `docs/superpowers/governance/2026-07-07-v2-recall-criterion-signed-deviation.md` (signed Absolute-Rule-1 deviation) → implemented in `evaluate_flip` @ `821db0f`; constants `ID_OOS_ABSTAIN_FLOOR=0.906`, `RECALL_TOLERANCE_T=0.05` |
| Driver (instrument) | `src/sage_poc/routing_eval/real_model_driver.py` @ `8abdaa8` — faithful `routed_of` incl. arm-independent veto; fp32 only (int8 safety-disqualified) |
| Positive control | fp32 cross-encoder head loaded, logit **separation 11.07** (> 3 required) — V2 numbers trustworthy |
| Code tree | `1208267` (feat/v2-live-reconcile) |
| Run harness | `scripts/routing_eval/reverdict_cells.py` (cells, per-stratum) + `reverdict_harm.py` (harm) |

## Per-conjunct result (V1+veto vs V2+veto, committed artifact)

| Conjunct (signed) | V1+veto | V2+veto | Gate | Pass |
|---|---|---|---|---|
| **harm-0** (skill_select domain) | 1 leak | **0 leaks** | 0 | ✅ |
| **path_checks** (BC1/BC2) | — | vacuous True | crisis/referral invariance | ✅ |
| **in_scope wrong-route** (misroute) | 0.2917 | **0.125** | ≤ V1 (no-regress) | ✅ |
| **in_scope recall** | 56.77% | **52.08%** | ≥ 51.77% (V1 − T=5pp) | ✅ (+0.31pp margin) |
| **id_oos abstain** | 46.9% | **92.2%** | ≥ 0.906 floor | ✅ (+1.6pp) |
| **far_oos abstain** | 100% | 100% | parity | ✅ |

`evaluate_flip(...).flip == True`, all cells `passed=True`, `harm_gate_pass=True`, `path_checks_pass=True`,
`bc3_passed=None` (BC3 is report-only under the revised criterion).

## Two findings recorded (reproduce-or-STOP outcomes, both benign, neither absorbed as tolerance)

1. **Flags-off no longer reproduces the frozen pre-veto baseline** (id_oos 23/64 → 30/64). Cause: the
   OCD-compulsion veto (`dcac987`, arm-independent) was added to `routed_of` in the increment-2/3 driver
   (diff-confirmed vs `1e61f70`), so both arms now abstain the OCD compulsions. **"V1" of record = V1+veto**;
   the frozen 35.9% is superseded by the shipped 46.9%. Verdict-invariant: id_oos is gated by an absolute
   floor (0.906), not a V1 comparison, and in_scope/far_oos are veto-invariant.
2. **Harm-gate scope.** The raw `harm_gate` counts all harm-prone rows (V1 8 fail / V2 4 fail), but **7 of
   V1's 8 are path-assertion cases** (`crisis_invariance`, `medical_referral`) — upstream safety_check's
   domain, excluded from routing quality by `compute_routing_metrics` (`_PATH_ASSERTION_KINDS`). The flip's
   meaningful harm gate is `skill_select`'s domain (non-path): **2 cases, V1 leaks 1, V2 leaks 0** — the
   reranker abstains on the postpartum "harming my baby" intrusive that the OCD veto (compulsion-only)
   cannot reach. *Recommendation: `harm_gate` should exclude `_PATH_ASSERTION_KINDS` for consistency with
   the routing metrics; tracked, does not change this verdict.*

## Honest note on the in_scope margin

Recall clears the tolerance floor by **0.31pp** (52.08% vs the 51.77% floor). It is a genuine pass under
the signed T=5pp, not a re-interpretation. The −4.69pp vs V1 is the coverage V2 trades for the +45.3pp
id_oos safety win and the halved in_scope wrong-route rate; the signed deviation's justification (soft
abstains recoverable in Node 3) applies. If a future re-measurement drifts below 51.77%, this reopens.

## Path forward (already-agreed, no new decisions)

FLIP → merge `feat/v2-live-reconcile` as a tracked PR → **Task 11 staged deploy**: staging flip → hard
health gates (`routing_mode=v2`, `reranker_fired=true`, ancestry-contains-veto `dcac987`, `build_sha`
match) → prod, same gates → **Task 12** prod measurement vs the re-anchored comparator. Flag stays the
serving control; AR remains fail-closed to V1 pending the Arabic-τ follow-up (native-review-gated).

## Reproduce

```
# cells (per-stratum, detached; fp32 CPU ~6-8 min)
SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1 SKILL_RERANK_PRECISION=fp32 uv run python scripts/routing_eval/reverdict_cells.py
SKILL_ROUTING_V2=0 SKILL_RERANK_ENABLED=0 uv run python scripts/routing_eval/reverdict_cells.py   # V1+veto
# harm both arms: reverdict_harm.py (same flag pattern)
```


## Annotation — Phase 1 harm-intrusive veto (2026-07-08, expanded corpus)
Committed harm fixtures expanded (`9642846`) with the failing worry-framed postpartum phrasing + paraphrases + terse control. Both arms re-measured on the expanded corpus: harm-domain skill-absorptions **4 → 0** (V1 and V2) after the deterministic harm-intrusive veto (`7ed83cf`, arm-independent). The reverdict driver's `routed_of` was mirrored to include the veto (harness-mirror rule). Prod-verified behaviorally (leak closed; 8/8 feature regression).
