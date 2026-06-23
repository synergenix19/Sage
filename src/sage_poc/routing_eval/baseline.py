"""§6 frozen-baseline management (CRADLE-style).

A signed gate-6 baseline is frozen to a JSON-able artifact + content hash; CI re-runs the
harness and `detect_regression` fails the build if the current result drifts below it. Drift
is computed PER (lang × stratum) cell — never pooled — so a strong English cell can never
mask a regressed Khaleeji ar/id_oos cell (the F8 artifact's fourth and final layer). The real
frozen baseline is populated from the held_out=False eval (A2 + pilot); the mechanism here is
that artifact's manager.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sage_poc.routing_eval.gate_runner import RoutingMetrics


@dataclass(frozen=True)
class FrozenBaseline:
    cells: dict[tuple[str, str], RoutingMetrics]

    def to_jsonable(self) -> list[dict]:
        return [
            {
                "lang": lang, "stratum": stratum,
                "misroute_rate": m.misroute_rate, "recall": m.recall,
                "abstain_correctness": m.abstain_correctness,
                "override_misroute_count": m.override_misroute_count, "n": m.n,
            }
            for (lang, stratum), m in sorted(self.cells.items())
        ]

    @classmethod
    def from_jsonable(cls, data: list[dict]) -> "FrozenBaseline":
        cells = {
            (d["lang"], d["stratum"]): RoutingMetrics(
                d["misroute_rate"], d["recall"], d["abstain_correctness"],
                d["override_misroute_count"], d["n"],
            )
            for d in data
        }
        return cls(cells)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_jsonable(), sort_keys=True).encode()
        ).hexdigest()


def freeze_baseline(metrics_by_stratum: dict[tuple[str, str], RoutingMetrics]) -> FrozenBaseline:
    return FrozenBaseline(dict(metrics_by_stratum))


@dataclass(frozen=True)
class RegressionReport:
    regressed: bool
    cells: dict[tuple[str, str], list[str]]   # (lang, stratum) -> reasons


def detect_regression(
    current: dict[tuple[str, str], RoutingMetrics],
    frozen: FrozenBaseline,
    *,
    misroute_tol: float = 0.0,
    recall_tol: float = 0.0,
    abstain_tol: float = 0.0,
) -> RegressionReport:
    """Per-cell drift check against the frozen baseline. Any cell that regressed beyond
    tolerance (or went missing) is flagged; improvements in other cells never offset it."""
    regressed_cells: dict[tuple[str, str], list[str]] = {}
    for key, fm in frozen.cells.items():
        cm = current.get(key)
        if cm is None:
            regressed_cells[key] = ["cell_missing"]
            continue
        reasons: list[str] = []
        if cm.misroute_rate > fm.misroute_rate + misroute_tol:
            reasons.append("misroute_up")
        if cm.recall < fm.recall - recall_tol:
            reasons.append("recall_down")
        if cm.abstain_correctness < fm.abstain_correctness - abstain_tol:
            reasons.append("abstain_down")
        if cm.override_misroute_count > fm.override_misroute_count:
            reasons.append("override_up")
        if reasons:
            regressed_cells[key] = reasons
    return RegressionReport(regressed=bool(regressed_cells), cells=regressed_cells)
