"""#311 — acute-distress TIPP reachability, red-first.

Two coupled routing defects surfaced by the 2026-07-14 conformance register (prod 43b9b62):

  1. KEYWORD tier: grounding_5_4_3_2_1's Tier-1 trigger list captures acute distress-tolerance
     language ("emotions out of control, need to calm down fast") before the semantic anchors
     compete, so dbt_tipp's bi-encoder edge is never used.
  2. SEMANTIC tier: box_breathing's §1e anticipatory-nerves anchor (commit 9bdcac4) out-scores
     dbt_tipp by +0.0071 on textbook TIPP language ("shock my system / burn this off"), displacing
     the acute skill.

The deciding bi-encoder margins are ±0.004-0.007 (noise territory), so the fix must be validated
against the FULL acute-skill probe set, not tuned to the two register probes. This module encodes:

  * RED (must flip with the fix): both register probes + all 8 construct-labeled dbt_tipp cases
    must route to dbt_tipp. TIPP must become reachable across its own canonical set.
  * GUARD (must not regress): box_breathing / grounding / stop_technique correct-route counts must
    not drop below their PRE-FIX baseline. The grounding 3/8 and stop 6/8 baselines bake in
    SEPARATE, pre-existing defects (grounding dissociation = SG-7 domain; stop impulse-urge keyword)
    that are OUT OF #311 SCOPE — the guard only prevents the #311 fix from making them worse.

Prod-faithful V1 arm (reranker not flipped on prod; register shows match_method=semantic) with the
full prod candidate set (exclude_skills empty; mindfulness_meditation is routable on prod).
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest

# MODE must be pinned BEFORE importing the driver (it reads the flags at import time).
os.environ.setdefault("SKILL_ROUTING_V2", "0")
os.environ.setdefault("SKILL_RERANK_ENABLED", "0")

import sage_poc  # noqa: E402
from sage_poc.routing_eval.real_model_driver import make_routed_of  # noqa: E402
from sage_poc.routing_eval.schema import EvalRecord  # noqa: E402

# Real embeddings, CPU-pinned via conftest's _warm_bge_m3_once (matches the Azure UAE prod target
# and removes ANE/MPS margin variance). The deciding box_breathing<->dbt_tipp margins are ±0.004-0.007
# — inside the band conftest documents as ANE-unstable — so this MUST run on the real CPU model, not
# the zero-vector stub that unmarked tests get.
pytestmark = pytest.mark.slow

_FIXTURE = (
    pathlib.Path(sage_poc.__file__).resolve().parents[2]
    / "tests/fixtures/routing_eval/acute_tipp_reachability_311.jsonl"
)

# Pre-fix baselines captured on origin/master 79912e7 (2026-07-15). The #311 fix must not lower
# these. box_breathing is fully clean and must STAY clean. grounding/stop carry out-of-scope
# pre-existing misses; the guard freezes their correct-count floor, it does not bless the misses.
_GUARD_BASELINE_CORRECT = {
    "box_breathing": 8,        # 8/8 — must stay perfect
    "grounding_5_4_3_2_1": 3,  # 3/8 — 5 dissociation misses are SG-7 scope, not #311
    "stop_technique": 6,       # 6/8 — 2 impulse-urge misses are a separate keyword defect
}


def _load():
    return [json.loads(l) for l in _FIXTURE.read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture(scope="module")
def routed_of():
    # prod-faithful candidate set: exclude nothing (matches live prod, incl. mindfulness_meditation)
    return make_routed_of(exclude_skills=frozenset())


def _route(routed_of, utterance):
    return routed_of(EvalRecord(utterance=utterance, lang="en", stratum="in_scope", expected_route="dbt_tipp"))


_RED = [d for d in _load() if d["probe_role"] == "red_311"]
_TIPP_CANON = [d for d in _load() if d["probe_role"] == "cross_route" and d["expected_route"] == "dbt_tipp"]


@pytest.mark.parametrize("probe", _RED, ids=[d["defect_tier"] for d in _RED])
def test_register_probe_routes_to_tipp(routed_of, probe):
    """Each register probe must reach dbt_tipp. Separate cases (keyword-tier, semantic-tier) so a
    fix cannot green one path and declare done."""
    got = _route(routed_of, probe["utterance"])
    assert got == "dbt_tipp", (
        f"{probe['defect_tier']}-tier defect unfixed: {probe['utterance']!r} routed to {got!r}, "
        f"expected dbt_tipp. {probe['defect_note']}"
    )


def test_tipp_reachable_across_canonical_set(routed_of):
    """All construct-labeled dbt_tipp utterances must route to dbt_tipp (TIPP fully reachable)."""
    misses = [(d["utterance"], _route(routed_of, d["utterance"])) for d in _TIPP_CANON]
    misses = [(u, g) for u, g in misses if g != "dbt_tipp"]
    assert not misses, "dbt_tipp unreachable on its own canonical cases:\n" + "\n".join(
        f"  got {g!r}: {u[:80]!r}" for u, g in misses
    )


@pytest.mark.parametrize("skill,floor", sorted(_GUARD_BASELINE_CORRECT.items()))
def test_no_cross_route_regression(routed_of, skill, floor):
    """The #311 fix must not lower any other acute skill's correct-route count below its pre-fix
    floor ('TIPP flips while nobody else's does')."""
    cases = [d for d in _load() if d["probe_role"] == "cross_route" and d["expected_route"] == skill]
    correct = sum(1 for d in cases if _route(routed_of, d["utterance"]) == skill)
    assert correct >= floor, (
        f"{skill} regressed: {correct}/{len(cases)} correct, below pre-fix floor {floor}. "
        f"The #311 fix must not degrade {skill} routing."
    )
