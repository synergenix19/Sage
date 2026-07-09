"""G6-signed HarnessConfig — the primary record.

This file IS the primary record that the 2026-07-07 signed-deviation
(`2026-07-07-v2-recall-criterion-signed-deviation.md`) names as the precondition for an
AUTHORITATIVE re-verdict. It is loaded by the §5 gate runner / `run_baseline`. Frozen; no
defaults; a truly-unset field hard-errors (`HarnessConfig.validate`, §2.4). Provenance travels
WITH the artifact (third recorded control on lost provenance — after prod SHA and the comparator
corpus): the authority derives from the signature below, and the corpus/method for each value is
in-line so a reader never has to reconstruct it.

SIGNED-BY: Rohan (Product Owner / G6)      DATE: 2026-07-08      ROLE: PO / G6
"""
from __future__ import annotations

from sage_poc.routing_eval.augrc import LossWeights
from sage_poc.routing_eval.harness import HarnessConfig

# G6-signed gate config. Every value settled; none pending.
G6_CONFIG = HarnessConfig(
    # LOSS — feeds AUGRC/BC3 only. `override_misroute` weights ONLY records with `override_fired=True`
    #   (`augrc.py:_covered_loss`). On the corpus of record (`5e6b86e`) **0 of 480 records are
    #   override_fired**, so this weight acts on zero records: AUGRC is bit-identical at
    #   override_misroute ∈ {2,4,8} BY CONSTRUCTION. The value is therefore signable, not blind —
    #   the "don't sign a sensitive value blind" gate is satisfied by a label-level PROOF of
    #   insensitivity, not an empirical run. Re-check ONLY if a future corpus introduces
    #   override_fired cases (then run per_cell_augrc → bc3 at the three weights before re-signing).
    loss=LossWeights(misroute=1.0, override_misroute=4.0),
    # DELTA — BC3 AUGRC per-stratum parity tolerance (AUGRC[ar][s] ≤ AUGRC[en][s] + delta).
    #   DECOUPLED from the §5 recall tolerance T=5pp: independent checks on different quantities;
    #   numerically equal today, NOT coupled.
    delta=0.05,
    # N_FLOOR — minimum per-language held-out n before a stratum's parity is asserted. > 1/delta (=20)
    #   plus margin (standard small-sample proportion floor). On `5e6b86e` (held-out, non-flag) EVERY
    #   stratum clears it: en in_scope 222 / id_oos 71 / far_oos 36; ar in_scope 32 / id_oos 69 /
    #   far_oos 31 (min = ar far_oos 31). So ALL strata are assertable — there is NO in_scope-parity
    #   deferral (an earlier draft mis-counted ar in_scope as 26; the committed corpus has 32).
    n_floor=30,
    # TAU — per-language reranker operating point on the cross-encoder logits, balanced Youden-J,
    #   held-out/CV fit on corpus `5e6b86e`. Only `en` is calibrated. `ar` is DELIBERATELY ABSENT
    #   (uncalibrated, native-review-gated) → absent key = abstention-not-asserted → AR fails closed
    #   to V1 (mirrors the live `_rerank_tau` fail-closed and Task-6b). NEVER put the fixtures'
    #   placeholder tau=0.50 here.
    tau={"en": -6.0843},
)
