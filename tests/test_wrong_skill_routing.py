# tests/test_wrong_skill_routing.py
"""Wrong-skill routing test suite.

125 colloquial phrases — 5 per matchable skill — that should route to a specific skill
but use emotional/everyday language rather than clinical keywords.

Two test layers:

  test_tier1_snapshot   Fast sync check. For each phrase that hits any Tier 1 keyword,
                        asserts the matched skill is the correct one (or within the same
                        semantic cluster). Does NOT fail on phrases with zero keyword
                        coverage — those are expected Tier 2 cases.

  test_full_routing     Slow async check. Runs full skill_select_node pipeline (including
                        BGE-M3 embedding). Asserts active_skill_id == expected_skill_id.
                        Within-cluster psychoed mismatches are logged but do not fail CI
                        (see PSYCHOED_CLUSTER in cases.py).

SKILL_REGISTRY ORDER NOTE
  Tier 1 scan iterates SKILL_REGISTRY order. Any edit to target_presentations that adds a
  new keyword must be followed by running test_tier1_snapshot before committing. A new
  keyword that is a substring of an existing longer keyword in a later-scanned skill
  creates a shadow collision — this test suite will catch it.

_ss_state ASSUMPTION
  emotional_intensity=5 and engagement=7 are hardcoded throughout. This is safe because
  skill_select_node (Node 4) currently routes based on intent and message content only;
  it does not read emotional signals for routing decisions (those are Node 5 concerns).
  If Node 4 is later extended to use therapeutic profile or clinical flags for skill
  selection, parametrised variants over those fields will be needed.
"""
from __future__ import annotations

import pytest

from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.nodes.skill_select import _SKILLS
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

from tests.fixtures.wrong_skill.cases import WRONG_SKILL_CASES, PSYCHOED_CLUSTER


# ── state helper ─────────────────────────────────────────────────────────────

def _ss_state(**overrides) -> dict:
    """Minimal state dict for skill_select_node.

    Mirrors the helper in test_skill_select.py. emotional_intensity=5 and
    engagement=7 are hardcoded — see module docstring for the assumption this rests on.
    """
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


# ── Tier 1 mirror ─────────────────────────────────────────────────────────────

def _tier1_match(phrase: str) -> str | None:
    """Mirror production Tier 1 scan without async overhead.

    Iterates SKILL_REGISTRY order, skips KEYWORD_SEMANTIC_SKIP, returns the first
    skill whose keyword is a substring of phrase (case-insensitive). Logic is
    identical to test_skill_routing_ba_pd._tier1_match — kept local to avoid
    cross-test coupling.
    """
    phrase_lower = phrase.lower()
    for sid in SKILL_REGISTRY:
        if sid not in _SKILLS or sid in KEYWORD_SEMANTIC_SKIP:
            continue
        for kw in _SKILLS[sid].target_presentations:
            if kw.lower() in phrase_lower:
                return sid
    return None


# ── Tier 1 snapshot (fast, synchronous) ──────────────────────────────────────

@pytest.mark.parametrize("expected_skill,phrase", WRONG_SKILL_CASES)
def test_tier1_snapshot(expected_skill: str, phrase: str) -> None:
    """Tier 1 collision gate: if a phrase matches ANY keyword it must route to the
    correct skill (or the same semantic cluster for psychoed skills).

    Does NOT fail on phrases with no keyword match — those rely on Tier 2 (semantic).
    Only fails when a phrase hits a keyword belonging to a different skill, which is
    always a bug.

    Within the PSYCHOED_CLUSTER (psychoed_anxiety / psychoed_depression /
    psychoed_stress) a within-cluster Tier 1 match is acceptable: all three skills
    share psychoeducation vocabulary and the correct fix is Tier 1 expansion on the
    target skill, not a test failure.

    Run with:
        pytest tests/test_wrong_skill_routing.py -k "test_tier1_snapshot" -v
    """
    actual_tier1 = _tier1_match(phrase)
    if actual_tier1 is None:
        return  # no keyword match — Tier 2 will handle it; not a failure here

    if actual_tier1 == expected_skill:
        return  # correct keyword match — pass

    # Within-cluster psychoed mismatch: acceptable ambiguity, not a CI failure
    if expected_skill in PSYCHOED_CLUSTER and actual_tier1 in PSYCHOED_CLUSTER:
        return

    assert False, (
        f"Tier 1 COLLISION: '{phrase}'\n"
        f"  Expected skill : {expected_skill}\n"
        f"  Tier 1 matched : {actual_tier1}\n"
        f"  A keyword in {actual_tier1!r} is a substring of this phrase and is scanned\n"
        f"  before {expected_skill!r} in SKILL_REGISTRY. Fix options:\n"
        f"    1. Remove the shadowing keyword from {actual_tier1!r}.target_presentations\n"
        f"    2. Reorder SKILL_REGISTRY (requires full collision audit)\n"
        f"    3. Rewrite the test phrase to avoid the colliding keyword\n"
        f"  Check _KNOWN_SUBSTRING_SHADOWS in test_skill_routing_ba_pd.py first —\n"
        f"  this may already be a documented pre-existing collision."
    )


# ── Full pipeline correctness (slow, async) ───────────────────────────────────

@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.parametrize("expected_skill,phrase", WRONG_SKILL_CASES)
async def test_full_routing(expected_skill: str, phrase: str) -> None:
    """Full routing assertion: phrase must reach the correct skill via either tier.

    Marked slow because Tier 2 requires BGE-M3 embedding inference. Run with:
        pytest tests/test_wrong_skill_routing.py -m slow -v

    A failure means the phrase routed to the wrong skill or to None. Each failure is
    a documented gap — either Tier 1 keyword coverage is missing, or Tier 2 semantic
    match is too weak / dominated by a different skill's embedding. The correct fix is
    Tier 1 keyword expansion (see docs/SKILL_AUTHORING_CONVENTIONS.md).

    PSYCHOED_CLUSTER exception: within-cluster routing (psychoed_anxiety ↔
    psychoed_depression ↔ psychoed_stress) is logged but does not fail CI.
    The three skills are semantically near-identical; correct routing within the cluster
    depends on Tier 1 keyword expansion, not semantic tuning.
    """
    state = _ss_state(
        message_en=phrase,
        raw_message=phrase,
        detected_language="en",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    actual_skill = result.get("active_skill_id")
    method = result.get("skill_match_method")
    score = result.get("semantic_score")

    if actual_skill == expected_skill:
        return  # exact match — pass

    # Within-cluster psychoed mismatch: log for manual review, do not fail CI
    if expected_skill in PSYCHOED_CLUSTER and actual_skill in PSYCHOED_CLUSTER:
        print(
            f"\n  [psychoed-cluster] '{phrase[:70]}'\n"
            f"    expected={expected_skill!r}, got={actual_skill!r}, score={score}"
        )
        return

    assert actual_skill == expected_skill, (
        f"ROUTING MISS: '{phrase}'\n"
        f"  Expected : {expected_skill}\n"
        f"  Got      : {actual_skill!r}  (method={method!r}, score={score})\n"
        f"  Fix options:\n"
        f"    Tier 1: Add a colloquial phrase to {expected_skill} target_presentations\n"
        f"    Tier 2: Verify semantic_description is technique-identity only (see RT-4)\n"
        f"    Ref   : docs/SKILL_AUTHORING_CONVENTIONS.md"
    )
