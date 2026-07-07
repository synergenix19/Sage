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
from sage_poc.routing_eval.schema import EvalRecord

# Dispositions that must block a freeze: an unsigned/unresolved clinical route.
_BLOCKING_DISPOSITIONS = ("borderline_pending",)


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


@dataclass(frozen=True)
class FreezeReadiness:
    ready: bool
    unresolved: dict[tuple[str, str], tuple[str, ...]]   # (lang, stratum) -> blocking utterances


def check_freeze_readiness(records: list[EvalRecord]) -> FreezeReadiness:
    """A held-out cell is freeze-ready only if NONE of its rows carry a blocking (unsigned)
    disposition. Mirrors BC3's insufficient_to_assert: a count gate ('N>=30 ok') must never let
    a cell freeze while it still encodes an unresolved clinical judgment. Non-held-out rows are
    not freeze cells, so they don't gate."""
    unresolved: dict[tuple[str, str], list[str]] = {}
    for r in records:
        if r.held_out and r.disposition in _BLOCKING_DISPOSITIONS:
            unresolved.setdefault((r.lang, r.stratum), []).append(r.utterance)
    return FreezeReadiness(
        ready=not unresolved,
        unresolved={k: tuple(v) for k, v in unresolved.items()},
    )


class UnresolvedDispositionError(Exception):
    """Raised by freeze_baseline when a cell still carries a borderline_pending row. Freeze is a
    terminal commit; a RAISE (not a returnable verdict) makes a dishonest freeze impossible
    rather than merely discouraged — the caveat can't decay into a thing a human must remember."""

    def __init__(self, readiness: FreezeReadiness):
        self.readiness = readiness
        cells = ", ".join(
            f"{lang}/{stratum}({len(u)})"
            for (lang, stratum), u in sorted(readiness.unresolved.items())
        )
        super().__init__(f"cannot freeze: unresolved borderline_pending dispositions in {cells}")


def freeze_baseline(
    metrics_by_stratum: dict[tuple[str, str], RoutingMetrics],
    records: list[EvalRecord],
) -> FrozenBaseline:
    """Freeze the signed gate-6 baseline. REFUSES (raises UnresolvedDispositionError) if any
    held-out cell still carries an unsigned (borderline_pending) disposition. `records` is
    required — no silent default — so every freeze site must present the set being frozen."""
    readiness = check_freeze_readiness(records)
    if not readiness.ready:
        raise UnresolvedDispositionError(readiness)
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
