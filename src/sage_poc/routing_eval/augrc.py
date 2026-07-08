"""§1.3 multi-threshold AUGRC sweep, per (lang × stratum).

AUGRC = mean selective risk over coverage levels k=1..N, with records ordered by
descending router confidence (top-candidate score). A record's loss when covered is 0
if it routes correctly, else the misroute weight (override-fired misroutes weigh more).
Lower is better; a perfectly-routing cell scores 0.

There is deliberately NO pooled-AUGRC function: the worst-cell inflation (F8) makes a
pooled AR-vs-EN comparison a composition artifact, so parity is asserted per-stratum only.
The loss weights are required config (no silent defaults, §2.4) — callers must pass them.
"""
from __future__ import annotations

from dataclasses import dataclass

from sage_poc.routing_eval.schema import ABSTAIN, STRATA, EvalRecord


@dataclass(frozen=True)
class LossWeights:
    """Generalized-risk loss vector (§1.3). Track-A signed; no default — must be passed."""
    misroute: float
    override_misroute: float


@dataclass(frozen=True)
class CellAUGRC:
    lang: str
    stratum: str
    n: int
    augrc: float


def _covered_loss(r: EvalRecord, loss: LossWeights) -> float:
    """Loss of a routed (covered) record. 0 iff it routes to the expected skill."""
    routed = r.scored_candidates[0][0] if r.scored_candidates else None
    correct = r.expected_route != ABSTAIN and routed == r.expected_route
    if correct:
        return 0.0
    return loss.override_misroute if r.override_fired else loss.misroute


def augrc(records: list[EvalRecord], loss: LossWeights) -> float:
    """AUGRC over one cell's records (caller groups by cell). Excludes flag_bearing rows."""
    rows = [r for r in records if not r.flag_bearing]
    if not rows:
        return 0.0
    # Order by descending confidence (top-candidate score): most-confident covered first.
    ordered = sorted(rows, key=lambda r: r.scored_candidates[0][1] if r.scored_candidates else 0.0,
                     reverse=True)
    losses = [_covered_loss(r, loss) for r in ordered]
    n = len(losses)
    cumulative = 0.0
    selective_risks = []
    for k in range(1, n + 1):
        cumulative += losses[k - 1]
        selective_risks.append(cumulative / k)   # mean loss over the k most-confident
    return sum(selective_risks) / n


def per_cell_augrc(records: list[EvalRecord], loss: LossWeights) -> dict[tuple[str, str], CellAUGRC]:
    """AUGRC per (lang × stratum). Ignores rows whose stratum is not an AUGRC stratum
    (crisis/referral path-assertion rows) and flag_bearing rows."""
    cells: dict[tuple[str, str], list[EvalRecord]] = {}
    for r in records:
        if r.stratum not in STRATA or r.flag_bearing:
            continue
        cells.setdefault((r.lang, r.stratum), []).append(r)
    return {
        key: CellAUGRC(lang=key[0], stratum=key[1], n=len(rows), augrc=augrc(rows, loss))
        for key, rows in cells.items()
    }
