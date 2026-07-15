"""Deterministic OCD-compulsion iatrogenic-routing veto (Node 4 skill_select).

Approved expedited hotfix (escalation 2026-07-07-v1-iatrogenic-ocd-routing-escalation.md).
The veto is ARM-INDEPENDENT (not gated on SKILL_ROUTING_V2): a disclosed compulsion/ritual must
ABSTAIN (defer to Node 3) instead of routing to a self-help skill, which is iatrogenic.

Two directions, both required by the acceptance gate:
  * OCD-compulsion utterances  -> vetoed / ABSTAIN
  * ordinary worry/rumination  -> NOT vetoed (a false-positive veto that drops a real worry case
    is a defined failure)
"""
import asyncio

import pytest

from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion
from sage_poc.nodes.skill_select import skill_select_node


# The 9 clinician-confirmed iatrogenic cases + one further OCD disclosure, across all 5 families.
COMPULSION_UTTERANCES = [
    "I keep mentally replaying conversations to check I didn't accidentally offend God, then silently repeat a prayer until it feels clean.",
    "Whenever a bad number like 13 pops into my head I have to picture a good number four times to cancel it.",
    "My books must face the exact same way or a sick feeling builds until I realign every spine perfectly.",
    "I count every step in even numbers and if I lose track I have to start the whole walk over.",
    "I keep getting horrible thoughts I might've left the stove on, so I check it twenty times.",
    "Whenever a bad thought pops up I have to tap the door three times or something terrible happens.",
    "I wash my hands until they're raw because I can't shake the feeling I'm contaminated.",
    "I keep texting my partner to ask if they still love me, the doubt won't quiet down.",
    "I reread my emails over and over counting the words so nothing bad will happen.",
    "Do you think I have OCD? I keep checking the locks like ten times before I leave.",
]

# Ordinary worry / rumination — must NOT be vetoed (worry_time / thought-record legitimately own these).
ORDINARY_WORRY_UTTERANCES = [
    "I keep worrying about my presentation tomorrow.",
    "Is there a way to box up all this fretting into one part of my day so it stops bleeding into everything?",
    "I'd love some structure to stop my mind running endless worst-case scenarios about things that never happen.",
    "My mind won't stop and I'm caught in a loop of anxious thoughts going round and round.",
    "I keep thinking everything is my fault and I want to write it down and look at the evidence.",
    "The worry about money has taken over every waking thought I have.",
]


@pytest.mark.parametrize("utterance", COMPULSION_UTTERANCES)
def test_compulsion_is_detected(utterance):
    assert is_ocd_compulsion(utterance) is True


@pytest.mark.parametrize("utterance", ORDINARY_WORRY_UTTERANCES)
def test_ordinary_worry_is_not_detected(utterance):
    assert is_ocd_compulsion(utterance) is False


def test_empty_and_none_are_not_detected():
    assert is_ocd_compulsion("") is False
    assert is_ocd_compulsion(None) is False


def _ss_state(**overrides):
    base = {
        "raw_message": "", "detected_language": "en", "message_en": "", "is_safe": True,
        "crisis_flags": [], "clinical_flags": [], "crisis_state": "none", "primary_intent": None,
        "secondary_intent": None, "intent_confidence": 1.0, "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "path": [], "turn_count": 0,
        "conversation_history": [], "skill_match_method": None, "semantic_score": None,
    }
    base.update(overrides)
    # For an EN session raw_message IS the input (no translation); mirror it so the veto — which
    # now reads raw via safety_text() per the #330 language contract — sees the utterance.
    if not base["raw_message"] and base["message_en"]:
        base["raw_message"] = base["message_en"]
    return base


@pytest.mark.parametrize("utterance", COMPULSION_UTTERANCES)
def test_node_vetoes_compulsion_to_abstain(utterance):
    """skill_select ABSTAINS (no skill, no offer) on a compulsion, before either routing tier.
    Deterministic: the veto returns before Tier 2, so no model is loaded. Driven via asyncio.run
    so the test runs without pytest-asyncio."""
    result = asyncio.run(skill_select_node(_ss_state(message_en=utterance)))
    assert result["active_skill_id"] is None
    assert result.get("offered_skill_ids") in (None, [], (),)
    assert result["path"][-1] == "ocd_compulsion_veto"
    assert result["skill_match_method"] is None
