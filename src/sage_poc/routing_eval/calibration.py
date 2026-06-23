"""§2 calibration — per-route, per-language base thresholds (§5.4 ordering).

Produces the per-route operating points τ that **6b / BC4 point metrics** read at. It does
NOT touch 6a / BC3 parity, which is a curve area over the whole sweep and therefore
calibration-independent (C1) — there is deliberately no τ argument anywhere near BC3.

§5.4 base step: calibrate on the calibration set (held_out=False) with `prior_state=None`
ONLY (utterance-only); the state-folding contribution is a separate later step that may not
reopen these base thresholds. Per-skill min-N gates own-threshold eligibility; below it a
route falls back to its cluster threshold (§6.3).

The τ values produced here against fixtures are TEST ARTIFACTS — regenerated each call, never
frozen into a module constant. A defensible operating point comes only from the real
held_out=False eval (A2 + pilot signal), not from synthetic fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass

from sage_poc.routing_eval.schema import EvalRecord


@dataclass(frozen=True)
class ThresholdTable:
    per_route: dict[tuple[str, str], float]       # (lang, route) -> own τ
    cluster: dict[tuple[str, str], float]         # (lang, cluster) -> fallback τ
    route_cluster: dict[str, str]                 # route -> cluster (for fallback resolution)
    fallback: frozenset[tuple[str, str]]          # (lang, route) using cluster fallback

    def threshold(self, lang: str, route: str) -> float:
        if (lang, route) in self.per_route:
            return self.per_route[(lang, route)]
        cluster = self.route_cluster.get(route, route)
        return self.cluster[(lang, cluster)]

    def is_fallback(self, lang: str, route: str) -> bool:
        return (lang, route) in self.fallback

    def cluster_threshold(self, lang: str, cluster: str) -> float:
        return self.cluster[(lang, cluster)]


def _separating_threshold(tp: list[float], fp: list[float]) -> float:
    """Operating point separating a route's true-positive scores (cover, ≥τ) from its
    false-positive scores (abstain, <τ). Clean separation → midpoint; overlap → the τ
    minimising misclassification, ties broken toward the HIGHER τ (abstain-leaning, the
    safe direction given the over-firing failure mode)."""
    tp = sorted(tp)
    fp = sorted(fp)
    if not tp:
        return 1.0                                   # no positives → never route (degenerate)
    if not fp:
        return max(0.0, round(tp[0] - 0.01, 6))      # cover all positives
    if fp[-1] < tp[0]:
        return round((fp[-1] + tp[0]) / 2, 6)        # clean separation
    best = None
    best_err = None
    for c in sorted(set(tp + fp)):                    # overlap: minimise misclassification
        err = sum(1 for s in fp if s >= c) + sum(1 for s in tp if s < c)
        if best_err is None or err < best_err or (err == best_err and c > best):
            best_err, best = err, c
    return round(best, 6)


def calibrate_base_thresholds(
    records: list[EvalRecord],
    *,
    min_n: int,
    cluster_of: dict[str, str],
) -> ThresholdTable:
    """Calibrate per-route, per-language base thresholds on the prior_state=None slice.

    A route earns its own threshold only with >= min_n true positives; otherwise it falls
    back to its cluster threshold. Returns a freshly-computed table (never a frozen constant).
    """
    # §5.4 + §2.1: base uses the calibration set (held_out=False) AND utterance-only rows.
    base = [r for r in records if (not r.held_out) and r.prior_state is None and r.scored_candidates]

    # Per (lang, top-route): collect TP (expected==route) and FP (expected!=route) top-scores.
    tp: dict[tuple[str, str], list[float]] = {}
    fp: dict[tuple[str, str], list[float]] = {}
    for r in base:
        route, score = r.scored_candidates[0]
        key = (r.lang, route)
        bucket = tp if r.expected_route == route else fp
        bucket.setdefault(key, []).append(score)

    routes = set(tp) | set(fp)

    # Cluster-level TP/FP (so fallback routes have a threshold to inherit).
    ctp: dict[tuple[str, str], list[float]] = {}
    cfp: dict[tuple[str, str], list[float]] = {}
    for (lang, route) in routes:
        cluster = cluster_of.get(route, route)
        ctp.setdefault((lang, cluster), []).extend(tp.get((lang, route), []))
        cfp.setdefault((lang, cluster), []).extend(fp.get((lang, route), []))

    cluster_tau = {
        key: _separating_threshold(ctp.get(key, []), cfp.get(key, []))
        for key in set(ctp) | set(cfp)
    }

    per_route: dict[tuple[str, str], float] = {}
    fallback: set[tuple[str, str]] = set()
    for (lang, route) in routes:
        if len(tp.get((lang, route), [])) >= min_n:
            per_route[(lang, route)] = _separating_threshold(
                tp.get((lang, route), []), fp.get((lang, route), [])
            )
        else:
            fallback.add((lang, route))

    return ThresholdTable(
        per_route=per_route,
        cluster=cluster_tau,
        route_cluster=dict(cluster_of),
        fallback=frozenset(fallback),
    )
