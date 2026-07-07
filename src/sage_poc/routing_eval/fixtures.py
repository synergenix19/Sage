"""Deterministic, adversarial synthetic fixtures for the §1 harness.

Two design rules, both load-bearing:
  1. Deterministic for a given seed (frozen-baseline reproducibility, §6).
  2. Adversarial by construction — the generator ships the cases each blocking check
     must FIRE on, so "the check passes on clean rows" is never mistaken for "the
     check works." (exercise-it-don't-declare-it.)

Scores here are synthetic stand-ins for the real `_semantic_match_with_runner_up`
output; no model is loaded. The adversarial rows use fixed scores so assertions are
stable; filler rows draw from a seeded RNG so different seeds genuinely differ.
"""
from __future__ import annotations

import random

from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.routing_eval.schema import ABSTAIN, NA, EvalRecord

# Non-referral skills usable as synthetic routing targets.
_TARGETS = [s for s in SKILL_REGISTRY if s not in ("psychotic_referral", "post_crisis_check_in")]


# --- adversarial singletons (blocking-check tripwires) ----------------------

def crisis_reaching_scorer() -> EvalRecord:
    """Crisis-invariance row whose path WRONGLY reached skill_select. BC1 must fail."""
    return EvalRecord(
        utterance="crisis-invariance-reached",
        lang="en",
        stratum=NA,
        expected_route=ABSTAIN,
        case_kind="crisis_invariance",
        reached_skill_select=True,
    )


def crisis_intercepted() -> EvalRecord:
    """Crisis-invariance row correctly intercepted by Node 1. BC1 must pass."""
    return EvalRecord(
        utterance="crisis-invariance-intercepted",
        lang="ar",
        stratum=NA,
        expected_route=ABSTAIN,
        case_kind="crisis_invariance",
        reached_skill_select=False,
    )


def referral_routed_to_excluded() -> EvalRecord:
    """Referral-exclusion row whose top candidate is an excluded referral. BC2 must fail."""
    return EvalRecord(
        utterance="referral-routed",
        lang="ar",
        stratum=NA,
        expected_route=ABSTAIN,
        case_kind="referral_exclusion",
        scored_candidates=(("psychotic_referral", 0.71), ("cbt_thought_record", 0.50)),
    )


def referral_not_routed() -> EvalRecord:
    """Referral-exclusion row that routes elsewhere. BC2 must pass."""
    return EvalRecord(
        utterance="referral-not-routed",
        lang="ar",
        stratum=NA,
        expected_route=ABSTAIN,
        case_kind="referral_exclusion",
        scored_candidates=(("cbt_thought_record", 0.68), ("psychotic_referral", 0.30)),
    )


# --- stratified set (AUGRC substrate + BC3 power floor) ---------------------

# Most cells well-powered; ar/far_oos deliberately underpowered to exercise BC3's floor.
_CELL_COUNTS = {
    ("en", "in_scope"): 8,
    ("en", "id_oos"): 8,
    ("en", "far_oos"): 8,
    ("ar", "in_scope"): 8,
    ("ar", "id_oos"): 8,
    ("ar", "far_oos"): 3,   # underpowered
}


def _in_scope_row(lang: str, i: int, rng: random.Random) -> EvalRecord:
    sid = _TARGETS[i % len(_TARGETS)]
    other = _TARGETS[(i + 1) % len(_TARGETS)]
    top = round(0.55 + rng.random() * 0.20, 4)          # 0.55–0.75, clearly routed
    second = round(top - 0.10 - rng.random() * 0.10, 4)  # clear margin
    return EvalRecord(
        utterance=f"{lang}-in_scope-{i}",
        lang=lang, stratum="in_scope", expected_route=sid,
        scored_candidates=((sid, top), (other, second)),
        winning_anchor_type="exemplar",
    )


def _abstain_row(lang: str, stratum: str, i: int, rng: random.Random) -> EvalRecord:
    sid = _TARGETS[i % len(_TARGETS)]
    other = _TARGETS[(i + 1) % len(_TARGETS)]
    hi = 0.50 if stratum == "id_oos" else 0.40           # far_oos sits lower
    top = round(hi - rng.random() * 0.12, 4)
    second = round(top - 0.05 - rng.random() * 0.08, 4)
    return EvalRecord(
        utterance=f"{lang}-{stratum}-{i}",
        lang=lang, stratum=stratum, expected_route=ABSTAIN,
        scored_candidates=((sid, top), (other, second)),
    )


def stratified_set(seed: int) -> list[EvalRecord]:
    """Deterministic stratified eval set covering all (lang × stratum) cells.

    ar/id_oos (the worst cell) carries an override-fired row and a thin-margin
    near-tie; ar/far_oos is underpowered. All held_out=True (gate side).
    """
    rng = random.Random(seed)
    recs: list[EvalRecord] = []
    for (lang, stratum), n in _CELL_COUNTS.items():
        for i in range(n):
            if stratum == "in_scope":
                recs.append(_in_scope_row(lang, i, rng))
            else:
                recs.append(_abstain_row(lang, stratum, i, rng))

    # Inject the worst-cell adversaries into ar/id_oos with fixed scores (stable assertions).
    recs.append(EvalRecord(
        utterance="ar-id_oos-override",
        lang="ar", stratum="id_oos", expected_route=ABSTAIN,
        scored_candidates=(("dbt_tipp", 0.50), ("grounding_5_4_3_2_1", 0.41)),
        override_fired=True,
    ))
    recs.append(EvalRecord(
        utterance="ar-id_oos-thinmargin",
        lang="ar", stratum="id_oos", expected_route=ABSTAIN,
        scored_candidates=(("worry_time", 0.46), ("cognitive_restructuring", 0.44)),  # margin 0.02
    ))
    return recs
