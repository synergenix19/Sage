"""§3 anchor-attribution + anchor-count debias validation.

Attribution (§3.2): per skill, which anchor type won, and which description anchors won on
mis-routes — the prune-workflow input that §2.1 step 3 consumes.

Debias validation (§3.4): does FP rate correlate with anchor count? Gated on the |r| point
estimate + a bootstrap CI, NOT significance (which would trip on noise or rubber-stamp an
underpowered null). When the CI is too wide to separate "removed" from "small residual" —
the N=27 reality — it returns `insufficient_power`, NOT a false green, and ships the debias
precautionarily (§6.1 pre-commit). Same idiom as BC3's `insufficient_to_assert`.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from sage_poc.routing_eval.schema import EvalRecord


# --- attribution -------------------------------------------------------------

@dataclass(frozen=True)
class AttributionStats:
    exemplar_wins: int
    description_wins: int
    description_misroutes: int   # description anchor won AND it was a mis-route → prune candidate

    @property
    def is_prune_candidate(self) -> bool:
        return self.description_misroutes > 0


def anchor_attribution(records: list[EvalRecord]) -> dict[str, AttributionStats]:
    ew: dict[str, int] = {}
    dw: dict[str, int] = {}
    dm: dict[str, int] = {}
    for r in records:
        if not r.scored_candidates:
            continue
        skill = r.scored_candidates[0][0]
        if r.winning_anchor_type == "exemplar":
            ew[skill] = ew.get(skill, 0) + 1
        elif r.winning_anchor_type == "description":
            dw[skill] = dw.get(skill, 0) + 1
            if r.expected_route != skill:
                dm[skill] = dm.get(skill, 0) + 1
    skills = set(ew) | set(dw) | set(dm)
    return {s: AttributionStats(ew.get(s, 0), dw.get(s, 0), dm.get(s, 0)) for s in skills}


# --- anchor-count / FP correlation with bootstrap CI -------------------------

@dataclass(frozen=True)
class CorrelationResult:
    r: float
    ci_low: float
    ci_high: float
    n: int


def anchor_count_fp_correlation(
    points: list[tuple[float, float]],
    *,
    seed: int,
    n_boot: int = 500,
) -> CorrelationResult:
    """Pearson r between per-skill (anchor_count, fp_rate) + a percentile bootstrap CI.
    Undefined inputs (n<3 or zero variance) return a deliberately WIDE CI so the validator
    reads them as underpowered, never as a confident zero."""
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    n = len(points)
    if n < 3 or xs.std() == 0 or ys.std() == 0:
        return CorrelationResult(0.0, -1.0, 1.0, n)

    r = float(np.corrcoef(xs, ys)[0, 1])
    rng = random.Random(seed)
    boots: list[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        bx, by = xs[idx], ys[idx]
        if bx.std() == 0 or by.std() == 0:
            continue
        boots.append(float(np.corrcoef(bx, by)[0, 1]))
    if not boots:
        return CorrelationResult(round(r, 4), -1.0, 1.0, n)
    boots.sort()
    lo = boots[int(0.025 * len(boots))]
    hi = boots[min(int(0.975 * len(boots)), len(boots) - 1)]
    return CorrelationResult(round(r, 4), round(lo, 4), round(hi, 4), n)


# --- debias validation (with the underpowered branch) ------------------------

@dataclass(frozen=True)
class DebiasVerdict:
    status: str          # "pass" | "fail" | "insufficient_power"
    after_r: float
    after_ci_low: float
    after_ci_high: float
    before_r: float
    ship_debias: bool


def validate_anchor_debias(
    before: list[tuple[float, float]],
    after: list[tuple[float, float]],
    *,
    r_max: float = 0.2,
    ci_width_max: float = 0.35,
    seed: int,
    n_boot: int = 500,
) -> DebiasVerdict:
    """Validate the debias mechanism removed the anchor-count/FP correlation.

    - insufficient_power: after-CI too wide to separate removed-vs-residual (e.g. N=27) →
      NOT a false green; ship debias precautionarily and defer the verdict to a powered
      re-measure.
    - pass: |after_r| <= r_max with a tight CI AND not worse than before → mechanism works, ship it.
    - fail: residual correlation survives with a tight CI → this mechanism is wrong; escalate
      (try the other mechanism — normalization vs cap), do not ship it as validated.
    """
    b = anchor_count_fp_correlation(before, seed=seed, n_boot=n_boot)
    a = anchor_count_fp_correlation(after, seed=seed, n_boot=n_boot)
    width = a.ci_high - a.ci_low

    if width > ci_width_max:
        status, ship = "insufficient_power", True
    elif abs(a.r) <= r_max and a.r <= b.r:
        status, ship = "pass", True
    else:
        status, ship = "fail", False

    return DebiasVerdict(
        status=status,
        after_r=a.r, after_ci_low=a.ci_low, after_ci_high=a.ci_high,
        before_r=b.r, ship_debias=ship,
    )
