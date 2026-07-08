"""Per-cell mis-route tolerance — the rule-of-three bound, configured per (lang, stratum).

Three risk profiles (clinician, 2026-06-24), deliberately NOT a single global number:
  - easy cells (in_scope, far_oos, both langs): <=10%  (POC stable-estimate bound)
  - worst cell (ar/id_oos): <=4.6% under Arm A      (dialect x ID-OOS compounds)
  - path-assertion cells (n/a stratum): no percentage tolerance -> judged by the harm gate

A uniform floor would silently relax the worst cell from 4.6% to 10% — the F8-shaped error of
a single number masking the cell that needs the tightest one. This module is intentionally
separate from BC3 (blocking_checks.py): BC3 answers "is the cell powered enough to render an
AUGRC parity verdict"; this answers "is the mis-route point estimate within the cell's bound".
A cell can be powered-enough-to-judge yet over-tolerance, or under-powered yet zero-error.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Per-cell mis-route tolerance. A cell absent from this map (e.g. n/a path-assertion strata)
# has NO percentage tolerance and is judged by the harm gate instead.
# NOTE: ("en","id_oos") is set to the tight id_oos-class bound as a fail-closed RECOMMENDATION
# pending sign-off — id_oos is where the safety-relevant over-route (route-when-should-ABSTAIN)
# failure lives, language-independent. Confirm or relax to 0.10; see the G6 #4 doc.
CELL_MISROUTE_TOLERANCE: dict[tuple[str, str], float] = {
    ("en", "in_scope"): 0.10, ("ar", "in_scope"): 0.10,
    ("en", "far_oos"): 0.10,  ("ar", "far_oos"): 0.10,
    ("ar", "id_oos"): 0.046,
    ("en", "id_oos"): 0.046,   # RECOMMENDED tight (pending confirm) — see note above
}


def tolerance_for(lang: str, stratum: str) -> float | None:
    """The cell's mis-route tolerance, or None = no percentage tolerance (harm-gate territory)."""
    return CELL_MISROUTE_TOLERANCE.get((lang, stratum))


def n_floor_for(tolerance: float) -> int:
    """Minimum zero-error N to bound the rate at `tolerance` (rule of three: n = ceil(3/tol)).
    Ties the power requirement to the stated effect size: 0.10 -> 30, 0.046 -> 66 (~65)."""
    return math.ceil(3.0 / tolerance)


def misroute_upper_bound(misroutes: int, n: int) -> float:
    """One-sided ~95% upper bound on the cell mis-route rate.

    Zero events -> rule of three (3/n), the bound the per-cell N is derived from. Once an error
    appears, a Wilson upper bound, so the first mis-route meaningfully raises the bound
    (1/65 -> ~0.082, not 0.015). The jump at 0->1 IS the stopping rule: a single mis-route can
    fail a cell whose point estimate still looks tiny.
    """
    if n <= 0:
        return 1.0
    if misroutes == 0:
        return 3.0 / n
    z = 1.96
    p = misroutes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center + half


@dataclass(frozen=True)
class ToleranceVerdict:
    status: str               # "pass" | "fail" | "insufficient_n" | "no_tolerance"
    cell: tuple[str, str]
    tolerance: float | None
    misroutes: int
    n: int
    upper_bound: float


def misroute_tolerance_gate(cell: tuple[str, str], *, misroutes: int, n: int) -> ToleranceVerdict:
    """Per-cell verdict. `no_tolerance` for path-assertion cells (harm gate decides them);
    `insufficient_n` when N is below the rule-of-three floor for the cell's bound (not a silent
    pass); else `pass`/`fail` on whether the upper bound clears the tolerance."""
    tol = tolerance_for(*cell)
    if tol is None:
        return ToleranceVerdict("no_tolerance", cell, None, misroutes, n, float("nan"))
    ub = misroute_upper_bound(misroutes, n)
    if n < n_floor_for(tol):
        status = "insufficient_n"
    elif ub <= tol:
        status = "pass"
    else:
        status = "fail"
    return ToleranceVerdict(status, cell, tol, misroutes, n, ub)
