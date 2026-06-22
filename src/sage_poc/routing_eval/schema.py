"""Eval-record schema for the routing-eval harness (§1.1).

One frozen record per case. Track A authors the ground-truth + stratification
columns; the runner fills the prediction columns. Frozen + tuple-valued so records
are equality-comparable and hashable, which the determinism check (§6 baseline)
relies on.
"""
from __future__ import annotations

from dataclasses import dataclass

# Controlled vocabularies (§1.1).
LANGS = ("en", "ar")
STRATA = ("in_scope", "id_oos", "far_oos")
CASE_KINDS = ("normal", "crisis_invariance", "referral_exclusion", "stale_state")
ABSTAIN = "ABSTAIN"

# Referral/after-care pathways excluded as skill_select targets (brief A1 / A2.8).
EXCLUDED_REFERRALS = ("psychotic_referral", "post_crisis_check_in")

# Sentinel stratum for non-AUGRC rows (crisis/referral path-assertion cases). The
# AUGRC sweep (§1.3) consumes only rows whose stratum is in STRATA, so these are
# naturally excluded from the curve.
NA = "n/a"


@dataclass(frozen=True)
class EvalRecord:
    utterance: str
    lang: str
    stratum: str
    expected_route: str                      # a skill_id, or ABSTAIN
    # Prediction columns (filled by the runner; synthetic in §1 fixtures):
    scored_candidates: tuple[tuple[str, float], ...] = ()  # ranked (skill_id, score) desc
    held_out: bool = True
    flag_bearing: bool = False               # flag-bearing ID-OOS (brief F3) — excluded from pure-routing scoring
    case_kind: str = "normal"
    override_fired: bool = False
    reached_skill_select: bool = False       # path trace; only meaningful for crisis_invariance
    winning_anchor_type: str | None = None   # "exemplar" | "description"
