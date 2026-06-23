"""§5 gate runner — the V2-vs-V1 flip criteria (§8 gates 1–5), composed PER-STRATUM.

`evaluate_flip` is the decision that gates the eventual live-path wiring: V2's flag flips on
only when it beats the frozen V1 baseline **within every (lang × stratum) cell** AND the
blocking checks pass. Per-stratum composition is load-bearing — a pooled "recall improves"
must not flip when the Khaleeji ar/id_oos worst cell regresses (the F8 composition artifact,
caught here at the flip layer as well as at the AUGRC layer). The per-stratum BC3 result is
folded in directly, so an `insufficient_to_assert` cell blocks the flip rather than reading
as a pass. Gate 5 (reranker latency) is a defined-negative: out of budget → reranker ships
off, gates 1–4 (reranker-independent) still decide the flip.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sage_poc.routing_eval.blocking_checks import BC3Result
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


@dataclass(frozen=True)
class RoutingMetrics:
    misroute_rate: float
    recall: float
    abstain_correctness: float
    override_misroute_count: int
    n: int


def compute_routing_metrics(
    records: list[EvalRecord],
    *,
    routed_of: Callable[[EvalRecord], str],
) -> RoutingMetrics:
    """Metrics over held-out, non-flag rows. `routed_of(record)` returns the chosen skill or
    ABSTAIN — injected so the metrics are decoupled from any specific τ."""
    rows = [r for r in records if r.held_out and not r.flag_bearing]
    n = len(rows)
    skill_expected = [r for r in rows if r.expected_route != ABSTAIN]
    abstain_expected = [r for r in rows if r.expected_route == ABSTAIN]

    recall_hits = misroutes = override_mis = 0
    for r in rows:
        routed = routed_of(r)
        if routed != ABSTAIN and routed != r.expected_route:
            misroutes += 1
            if r.override_fired:
                override_mis += 1
        if r.expected_route != ABSTAIN and routed == r.expected_route:
            recall_hits += 1
    abstain_correct = sum(1 for r in abstain_expected if routed_of(r) == ABSTAIN)

    return RoutingMetrics(
        misroute_rate=misroutes / n if n else 0.0,
        recall=recall_hits / len(skill_expected) if skill_expected else 0.0,
        abstain_correctness=abstain_correct / len(abstain_expected) if abstain_expected else 0.0,
        override_misroute_count=override_mis,
        n=n,
    )


def compute_metrics_by_stratum(
    records: list[EvalRecord],
    *,
    routed_of: Callable[[EvalRecord], str],
) -> dict[tuple[str, str], RoutingMetrics]:
    """Group held-out, non-flag rows by (lang, stratum) and compute metrics per cell — the
    per-stratum inputs evaluate_flip composes over (never pooled)."""
    groups: dict[tuple[str, str], list[EvalRecord]] = {}
    for r in records:
        if not (r.held_out and not r.flag_bearing):
            continue
        groups.setdefault((r.lang, r.stratum), []).append(r)
    return {k: compute_routing_metrics(v, routed_of=routed_of) for k, v in groups.items()}


@dataclass(frozen=True)
class StratumGates:
    gate_misroute: bool      # gate 1: misroute rate does not regress
    gate_override: bool      # gate 2: override mis-route == 0
    gate_recall: bool        # gate 3: recall improves (does not drop)
    gate_abstain: bool       # gate 4: abstain-correctness does not regress
    passed: bool             # all four hold in THIS cell


@dataclass(frozen=True)
class FlipVerdict:
    flip: bool
    per_stratum: dict[tuple[str, str], StratumGates]
    bc3_passed: bool         # per-stratum AUGRC parity incl. insufficient_to_assert → not pass
    path_checks_pass: bool   # BC1 crisis-path-invariance + BC2 referral-exclusion
    reranker_shipped: bool   # gate 5 defined-negative: ships only if in budget


def evaluate_flip(
    v1_by_stratum: dict[tuple[str, str], RoutingMetrics],
    v2_by_stratum: dict[tuple[str, str], RoutingMetrics],
    *,
    bc3_result: BC3Result,
    path_checks_pass: bool,
    reranker_in_budget: bool,
) -> FlipVerdict:
    per: dict[tuple[str, str], StratumGates] = {}
    all_cells_pass = bool(v2_by_stratum)
    for key, v2 in v2_by_stratum.items():
        v1 = v1_by_stratum.get(key)
        if v1 is None:
            # no V1 baseline for this cell → cannot assert improvement → conservative fail.
            per[key] = StratumGates(False, False, False, False, False)
            all_cells_pass = False
            continue
        g_mis = v2.misroute_rate <= v1.misroute_rate
        g_ovr = v2.override_misroute_count == 0
        g_rec = v2.recall >= v1.recall
        g_abs = v2.abstain_correctness >= v1.abstain_correctness
        cell_pass = g_mis and g_ovr and g_rec and g_abs
        per[key] = StratumGates(g_mis, g_ovr, g_rec, g_abs, cell_pass)
        if not cell_pass:
            all_cells_pass = False

    # bc3_result.passed is True only if EVERY stratum is "pass" (a "fail" OR
    # "insufficient_to_assert" cell already makes it False — so underpowered blocks).
    flip = all_cells_pass and bc3_result.passed and path_checks_pass
    return FlipVerdict(
        flip=flip,
        per_stratum=per,
        bc3_passed=bc3_result.passed,
        path_checks_pass=path_checks_pass,
        reranker_shipped=reranker_in_budget,
    )
