"""§1.4 blocking checks. Each returns a CheckResult; the harness (§1.5) turns any
failure into a non-zero exit. Hard-fail, never degrade-and-warn.

BC1 crisis-path-invariance and BC2 referral-exclusion live here (path/label checks,
independent of the metric layer). BC3 per-stratum parity and BC4 split-reporting are
computed from the AUGRC layer and live in augrc.py / harness.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from sage_poc.routing_eval.augrc import CellAUGRC
from sage_poc.routing_eval.schema import ABSTAIN, EXCLUDED_REFERRALS, EvalRecord


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    offending: tuple[EvalRecord, ...] = ()


def bc1_crisis_path_invariance(records: list[EvalRecord]) -> CheckResult:
    """Assert no crisis_invariance row reached skill_select (§7 path-invariance).

    Path assertion on the executed trace, not the route label. Any crisis row whose
    trace reached the scorer is a hard fail.
    """
    offending = tuple(
        r for r in records
        if r.case_kind == "crisis_invariance" and r.reached_skill_select
    )
    return CheckResult(
        name="BC1_crisis_path_invariance",
        passed=not offending,
        detail=(
            "all crisis_invariance rows intercepted before skill_select"
            if not offending
            else f"{len(offending)} crisis row(s) reached skill_select"
        ),
        offending=offending,
    )


def bc2_referral_exclusion(records: list[EvalRecord]) -> CheckResult:
    """Assert no referral_exclusion row routed to an excluded referral skill (A2.8)."""
    offending = tuple(
        r for r in records
        if r.case_kind == "referral_exclusion"
        and r.scored_candidates
        and r.scored_candidates[0][0] in EXCLUDED_REFERRALS
    )
    return CheckResult(
        name="BC2_referral_exclusion",
        passed=not offending,
        detail=(
            "no referral_exclusion row routed to an excluded skill"
            if not offending
            else f"{len(offending)} row(s) routed to an excluded referral skill"
        ),
        offending=offending,
    )


# --- BC3 per-stratum parity + per-cell power floor (H4) ----------------------

@dataclass(frozen=True)
class StratumVerdict:
    status: str                 # "pass" | "fail" | "insufficient_to_assert"
    en_augrc: float
    ar_augrc: float
    delta: float
    margin: float               # ar_augrc - en_augrc (negative/<=delta is good)
    en_n: int
    ar_n: int


@dataclass(frozen=True)
class BC3Result:
    name: str
    passed: bool
    strata: dict[str, StratumVerdict]


def bc3_per_stratum_parity(
    cells: dict[tuple[str, str], CellAUGRC],
    *,
    delta: float,
    n_floor: int,
) -> BC3Result:
    """Assert AUGRC[ar][s] <= AUGRC[en][s] + delta, per stratum (F1/F8).

    Renders a binding pass/fail only when BOTH language cells in the stratum clear the
    per-cell N floor; otherwise the stratum is `insufficient_to_assert` (never a silent
    pass). There is no pooled comparison. `passed` is True only if every stratum is "pass".
    """
    strata = {s for (_, s) in cells}
    verdicts: dict[str, StratumVerdict] = {}
    for s in strata:
        en = cells.get(("en", s))
        ar = cells.get(("ar", s))
        en_augrc = en.augrc if en else float("nan")
        ar_augrc = ar.augrc if ar else float("nan")
        en_n = en.n if en else 0
        ar_n = ar.n if ar else 0
        margin = ar_augrc - en_augrc
        if en is None or ar is None or en_n < n_floor or ar_n < n_floor:
            status = "insufficient_to_assert"
        elif margin <= delta:
            status = "pass"
        else:
            status = "fail"
        verdicts[s] = StratumVerdict(status, en_augrc, ar_augrc, delta, margin, en_n, ar_n)
    passed = all(v.status == "pass" for v in verdicts.values()) and bool(verdicts)
    return BC3Result(name="BC3_per_stratum_parity", passed=passed, strata=verdicts)


# --- BC4 split-reporting of 6b (F2) -----------------------------------------

@dataclass(frozen=True)
class SixBReport:
    """The two 6b criteria as SEPARATE numbers, read at the Arabic-calibrated tau (C1).
    Deliberately carries no fused pass/fail token — 6b-i and 6b-ii are never collapsed.
    """
    tau: float
    n: int
    abstain_correctness: float       # 6b-i
    ac_ci_low: float
    ac_ci_high: float
    override_misroute_count: int     # 6b-ii
    override_misroute_upper_bound: float


def bc4_split_report(records: list[EvalRecord], *, tau: float) -> SixBReport:
    """Compute 6b-i and 6b-ii over the ar/id_oos held-out slice at operating point tau.

    A record is "routed" (covered) when its top score >= tau, else the router abstains.
    6b-i abstain-correctness = fraction of (expected-ABSTAIN) rows correctly abstained.
    6b-ii override-mis-route = override-fired rows that were routed (covered) and wrong;
    when zero are observed the upper bound is the rule of three (3/N).
    """
    rows = [r for r in records if not r.flag_bearing]
    n = len(rows)
    if n == 0:
        return SixBReport(tau, 0, 0.0, 0.0, 0.0, 0, 0.0)

    def routed(r: EvalRecord) -> bool:
        return bool(r.scored_candidates) and r.scored_candidates[0][1] >= tau

    correct_abstain = sum(1 for r in rows if r.expected_route == ABSTAIN and not routed(r))
    p = correct_abstain / n
    halfwidth = 1.96 * math.sqrt(p * (1 - p) / n)

    override_misroutes = sum(
        1 for r in rows
        if r.override_fired and routed(r)
        and not (r.expected_route != ABSTAIN and r.scored_candidates[0][0] == r.expected_route)
    )
    upper_bound = (3.0 / n) if override_misroutes == 0 else override_misroutes / n

    return SixBReport(
        tau=tau, n=n,
        abstain_correctness=p, ac_ci_low=p - halfwidth, ac_ci_high=p + halfwidth,
        override_misroute_count=override_misroutes,
        override_misroute_upper_bound=upper_bound,
    )
