"""§5 gate runner — the V2-vs-V1 flip criteria (§8 gates 1–5).

`evaluate_flip` is the decision that gates the eventual live-path wiring: V2's flag flips
on only when it beats the frozen V1 baseline on the §8 gates AND the blocking checks pass.
Gate 5 (reranker latency) is a defined-negative — if the rerank hop isn't in budget it ships
OFF and gates 1–4 must still hold. This is built before the live path is touched so the
wiring has a gate to be measured against, not the other way round.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


@dataclass(frozen=True)
class RoutingMetrics:
    misroute_rate: float           # routed to a wrong skill (incl. routing an abstain-expected) / n
    recall: float                  # of expected-skill rows, fraction routed to the right skill
    abstain_correctness: float     # of expected-ABSTAIN rows, fraction correctly abstained
    override_misroute_count: int   # override-fired mis-routes (the unrecoverable class)
    n: int


def compute_routing_metrics(
    records: list[EvalRecord],
    *,
    routed_of: Callable[[EvalRecord], str],
) -> RoutingMetrics:
    """Metrics over the held-out, non-flag rows. `routed_of(record)` returns the skill the
    router chose, or ABSTAIN — injected so the metrics are decoupled from any specific τ."""
    rows = [r for r in records if r.held_out and not r.flag_bearing]
    n = len(rows)
    skill_expected = [r for r in rows if r.expected_route != ABSTAIN]
    abstain_expected = [r for r in rows if r.expected_route == ABSTAIN]

    recall_hits = misroutes = override_mis = 0
    for r in rows:
        routed = routed_of(r)
        is_misroute = routed != ABSTAIN and routed != r.expected_route
        if is_misroute:
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


@dataclass(frozen=True)
class FlipVerdict:
    flip: bool
    gate_misroute: bool      # gate 1: misroute rate does not regress
    gate_override: bool      # gate 2: override mis-route == 0
    gate_recall: bool        # gate 3: recall improves (does not drop)
    gate_abstain: bool       # gate 4: abstain-correctness does not regress
    reranker_shipped: bool   # gate 5 (defined-negative): ships only if in budget


def evaluate_flip(
    v1: RoutingMetrics,
    v2: RoutingMetrics,
    *,
    v2_blocking_pass: bool,
    reranker_in_budget: bool,
) -> FlipVerdict:
    g_misroute = v2.misroute_rate <= v1.misroute_rate
    g_override = v2.override_misroute_count == 0
    g_recall = v2.recall >= v1.recall
    g_abstain = v2.abstain_correctness >= v1.abstain_correctness
    # Gate 5 is a defined-negative: the reranker just ships off if out of budget; gates 1–4
    # (which are reranker-independent) decide the flip regardless.
    flip = g_misroute and g_override and g_recall and g_abstain and v2_blocking_pass
    return FlipVerdict(
        flip=flip,
        gate_misroute=g_misroute,
        gate_override=g_override,
        gate_recall=g_recall,
        gate_abstain=g_abstain,
        reranker_shipped=reranker_in_budget,
    )
