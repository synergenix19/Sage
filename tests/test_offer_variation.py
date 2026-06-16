import sage_poc.nodes.skill_select as skill_select
from sage_poc.nodes.skill_select import _resolve_entry, _SKILLS


def _base_state():
    return {"path": [], "detected_language": "en", "emotional_intensity": 5,
            "declined_skills": []}


def test_offer_made_sets_offer_count_to_one(monkeypatch):
    # Force the offer path: make the skill_matching rule engine fire nothing,
    # so _resolve_entry falls back to _FALLBACK_OFFER_ACTION (offer).
    class _NoFire:
        fired = []
    monkeypatch.setattr(skill_select.rules_engine, "evaluate", lambda *a, **k: _NoFire())

    candidates = list(_SKILLS.keys())[:2]
    result = _resolve_entry(_base_state(), candidates, "keyword", None)

    assert "skill_offer_made" in result["path"]
    assert result["offered_skill_ids"] == candidates
    assert result["offer_count"] == 1


import pytest
import sage_poc.nodes.intent_route as intent_route


async def _route(monkeypatch, raw_json, state):
    async def _fake_invoke(*a, **k):
        return raw_json
    monkeypatch.setattr(intent_route, "resilient_invoke", _fake_invoke)
    monkeypatch.setattr(intent_route, "get_classifier", lambda: object())
    monkeypatch.setattr(intent_route, "get_fallback_classifier", lambda: object())
    monkeypatch.setattr(intent_route, "detect_directive_request", lambda s: False)
    return await intent_route.intent_route_node(state)


def _offer_state(offer_count):
    return {"path": [], "message_en": "hmm, maybe",
            "offered_skill_ids": ["box_breathing", "grounding_5_4_3_2_1"],
            "offer_count": offer_count, "declined_skills": []}


async def test_unparsed_offer_increments_offer_count(monkeypatch):
    # offer_response field absent -> classifier degradation -> preserve + re-ask
    state = _offer_state(1)
    result = await _route(monkeypatch, '{"primary_intent": "general_chat"}', state)
    assert "offer_unparsed" in result["path"]
    assert result["offer_count"] == 2


async def test_declined_offer_resets_offer_count(monkeypatch):
    state = _offer_state(2)
    result = await _route(monkeypatch, '{"primary_intent": "general_chat", "offer_response": "decline"}', state)
    assert "offer_declined" in result["path"]
    assert result["offer_count"] == 0


async def test_ignored_offer_resets_offer_count(monkeypatch):
    state = _offer_state(2)
    result = await _route(monkeypatch, '{"primary_intent": "general_chat", "offer_response": "other"}', state)
    assert result["offer_count"] == 0


async def test_accepted_offer_resets_offer_count(monkeypatch):
    state = _offer_state(2)
    result = await _route(
        monkeypatch,
        '{"primary_intent": "general_chat", "offer_response": "accept", "offer_choice_skill_id": "box_breathing"}',
        state,
    )
    assert "offer_accepted" in result["path"]
    assert result["offer_count"] == 0
