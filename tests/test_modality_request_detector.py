"""EMR Phase 1 — deterministic explicit-modality-request detector.

Plan: docs/superpowers/plans/2026-07-28-explicit-modality-request-handling.md (Phase 1).
Behavior-anchored per the standing rule: asserts on the detector result, the state
channel, and path markers — never response copy. Fixtures are naturalistic
SUPERSTRINGS of lexicon entries, never entries verbatim (E7 fixture-independence,
enforced by test_fixtures_are_not_lexicon_entries_verbatim below).
"""
import json
import time
from pathlib import Path

import pytest

from sage_poc import config
from sage_poc.matching import (
    BINDING_TABLE,
    REQUEST_PHRASES,
    detect_explicit_modality_request,
)

# Naturalistic request phrasings (superstrings of lexicon entries, not entries).
FIRES = [
    "are there any exercises i can do",                       # the observed transcript turn
    "is there a breathing exercise you could walk me through",
    "can you teach me a way to settle my chest before meetings",
    "i could use a coping tool for when this hits at night",
    "what can i do to calm myself down right now",
    "do you have a grounding exercise for moments like this",
]

# Both-direction guards: curiosity, bare affect, affirmation, gratitude.
DOES_NOT_FIRE = [
    "why does my body react like this?",
    "anxious",
    "I feel a bit anxious",
    "this is helping",
    "thanks, that exercise yesterday helped",   # past reference, no request phrasing
    "my chest feels tight when i think about work",
]


# ---------------------------------------------------------------------------
# Detector unit behavior
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", FIRES)
def test_fires_on_naturalistic_request_phrasings(msg):
    out = detect_explicit_modality_request(msg, msg, "en")
    assert out["requested"] is True, f"expected detection on {msg!r}"


@pytest.mark.parametrize("msg", DOES_NOT_FIRE)
def test_silent_on_curiosity_affect_and_affirmation(msg):
    out = detect_explicit_modality_request(msg, msg, "en")
    assert out["requested"] is False, f"false positive on {msg!r}"
    assert out["modality_hint"] is None


def test_modality_hint_carried_and_generic_requests_unhinted():
    hinted = detect_explicit_modality_request(
        "is there a breathing exercise you could walk me through", "", "en")
    assert hinted == {"requested": True, "modality_hint": "breathing"}
    generic = detect_explicit_modality_request(
        "are there any exercises i can do", "", "en")
    assert generic == {"requested": True, "modality_hint": None}


def test_language_gate_ar_sessions_skip_even_on_translated_en_match():
    """B2: AR sessions reach the detector with translated message_en that WOULD match
    the EN lexicon; the gate is on session language, not on which list matched."""
    out = detect_explicit_modality_request("are there any exercises i can do",
                                           "هل فيه تمارين أقدر أسويها", "ar")
    assert out == {"requested": False, "modality_hint": None}


def test_lexicon_size_and_latency_budget():
    """Plan riders: <=32 entries, one substring pass, <=1ms, no model/embedding call."""
    assert len(REQUEST_PHRASES) <= 32
    msg = "honestly today was rough and i was wondering are there any exercises i can do"
    t0 = time.perf_counter()
    for _ in range(100):
        detect_explicit_modality_request(msg, msg, "en")
    per_call = (time.perf_counter() - t0) / 100
    assert per_call < 0.001, f"detector took {per_call*1000:.3f}ms/call, budget is 1ms"


def test_binding_table_default_is_the_spec_first_line_pair_in_order():
    """DF-1 ordering owner: the binding table's default row IS the section-1a Tier-1
    first-line pair, in spec order. Phase-2 consumers depend on this row's stability."""
    assert BINDING_TABLE["default"] == ["box_breathing", "grounding_5_4_3_2_1"]


def test_no_em_dashes_in_lexicon_or_table():
    raw = json.dumps({"p": [e["phrase"] for e in REQUEST_PHRASES], "b": BINDING_TABLE})
    assert "—" not in raw


# ---------------------------------------------------------------------------
# Fixture independence (E7 lesson, CI-enforced)
# ---------------------------------------------------------------------------

def test_fixtures_are_not_lexicon_entries_verbatim():
    """E7 recall-fixture-independence: neither this file's FIRES set nor the EMR
    conformance family may contain a lexicon entry VERBATIM as a whole message —
    a fixture equal to its pattern is a tautology, not a recall measurement."""
    entries = {e["phrase"] for e in REQUEST_PHRASES}
    for msg in FIRES:
        assert msg.lower().strip() not in entries, f"tautological fixture: {msg!r}"
    family = Path(__file__).parent / "fixtures" / "conformance" / "emr_request_family.json"
    fam = json.loads(family.read_text(encoding="utf-8"))
    for case in fam["cases"]:
        for turn in case["turns"]:
            text = (turn if isinstance(turn, str) else turn.get("message", "")).lower().strip()
            assert text not in entries, (
                f"conformance fixture {case['case_id']} carries lexicon entry verbatim: {text!r}")


# ---------------------------------------------------------------------------
# Channel seam (intent_route write site)
# ---------------------------------------------------------------------------

def _intent_route_state(msg="are there any exercises i can do"):
    return {
        "message_en": msg, "raw_message": msg, "detected_language": "en",
        "path": ["safety_check"], "conversation_history": [],
        "offered_skill_ids": [], "crisis_flags": [],
    }


class _StubLLM:
    """Minimal classifier stub: returns a fixed JSON classification."""
    class _Msg:
        content = json.dumps({"primary_intent": "general_chat", "intent_confidence": 0.9,
                              "emotional_intensity": 4, "engagement": 6})
        response_metadata = {}
    async def ainvoke(self, _messages):
        return self._Msg()


@pytest.mark.asyncio
async def test_channel_written_and_marker_added_when_flag_on(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)
    from sage_poc.nodes.intent_route import intent_route_node
    out = await intent_route_node(_intent_route_state(), llm=_StubLLM())
    assert out["explicit_modality_request"] == {"requested": True, "modality_hint": None}
    assert "modality_request_detected" in out["path"]


@pytest.mark.asyncio
async def test_channel_none_and_no_marker_when_flag_off(monkeypatch):
    """OFF is byte-identical on this surface: channel written as None (per-turn reset
    still holds), no marker, nothing else in the update differs."""
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", False)
    from sage_poc.nodes.intent_route import intent_route_node
    out = await intent_route_node(_intent_route_state(), llm=_StubLLM())
    assert out["explicit_modality_request"] is None
    assert "modality_request_detected" not in out["path"]


@pytest.mark.asyncio
async def test_non_request_turn_writes_unrequested_not_stale(monkeypatch):
    """Per-turn semantics: a non-request turn writes requested=False (flag ON), so a
    prior turn's detection can never leak forward through the checkpoint."""
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)
    from sage_poc.nodes.intent_route import intent_route_node
    out = await intent_route_node(_intent_route_state("I feel a bit anxious"), llm=_StubLLM())
    assert out["explicit_modality_request"] == {"requested": False, "modality_hint": None}
    assert "modality_request_detected" not in out["path"]
