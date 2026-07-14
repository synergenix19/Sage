import os
import pytest

from sage_poc.nodes.venting_detect import detect_venting
from sage_poc.graph import _route_after_intent, build_graph
from sage_poc import config as _cfg

_needs_llm = pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="intent_route LLM")


def test_dontfix_signals_detected():
    for m in ("please just listen, I can't handle this anymore",
              "I'm so overwhelmed I just need to get this out, don't try to fix it",
              "I just need to vent", "I don't want advice, just talk"):
        assert detect_venting(m, m, "en") is True, m


def test_non_venting_distress_not_detected():
    # Acute distress WITHOUT a don't-fix signal must NOT be suppressed — the user may want help.
    for m in ("I'm panicking, help me calm down", "my heart is racing, what do I do"):
        assert detect_venting(m, m, "en") is False, m


def _route(**st):
    base = {
        "primary_intent": "general_chat", "emotional_intensity": 8, "intent_confidence": 0.9,
        "crisis_state": "none", "active_skill_id": None, "venting_detected": False,
        "gate_path": None, "offer_response": None, "prepass_matched": [],
    }
    return _route_after_intent({**base, **st})


def test_venting_suppresses_sf2_to_freeflow(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(venting_detected=True, emotional_intensity=8) == "freeflow"


def test_non_venting_high_intensity_still_reaches_skill_select(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(venting_detected=False, emotional_intensity=8) == "skill_select"


def test_flag_off_venting_unchanged(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", False)
    assert _route(venting_detected=True, emotional_intensity=8) == "skill_select"


def test_crisis_still_wins_over_venting(monkeypatch):
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(primary_intent="crisis", venting_detected=True) == "crisis"


def test_new_skill_venting_still_reaches_skill_select(monkeypatch):
    # Over-suppression guard: an explicit skill/help request must NOT be suppressed even if a
    # don't-fix keyword is present. Only general_chat venting is suppressed. (Uses the file's
    # existing _route(...) helper.)
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    assert _route(primary_intent="new_skill", venting_detected=True, emotional_intensity=8) == "skill_select"


# --- End-to-end (full graph, requires OPENROUTER_API_KEY for intent_route) ---

async def _drive(msg, tid):
    from langgraph.checkpoint.memory import MemorySaver
    return await build_graph(MemorySaver()).ainvoke(
        {"raw_message": msg, "path": []},
        config={"configurable": {"thread_id": tid}},
    )


@_needs_llm
@pytest.mark.asyncio
@pytest.mark.parametrize("msg,tid", [
    ("please just listen, I can't handle this anymore, everything is falling apart", "f6-1"),
    ("I'm so overwhelmed I just need to get this out, don't try to fix it", "f6-2"),
])
async def test_high_intensity_venting_no_longer_imposes_skill(monkeypatch, msg, tid):
    # RED on master today: these impose dbt_tipp. Green after Tasks 1-2 with the flag on.
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    r = await _drive(msg, tid)
    assert r.get("active_skill_id") is None, f"venting imposed {r.get('active_skill_id')}"


@_needs_llm
@pytest.mark.asyncio
@pytest.mark.parametrize("msg,tid", [
    ("I'm panicking, help me calm down right now", "f6-help"),   # genuine acute, wants help
])
async def test_non_venting_acute_still_reaches_a_skill(monkeypatch, msg, tid):
    # Do NOT over-suppress: acute distress without a don't-fix signal still gets a skill.
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    r = await _drive(msg, tid)
    assert r.get("active_skill_id") is not None or r.get("offered_skill_ids"), "over-suppressed a help-seeking acute turn"


@_needs_llm
@pytest.mark.asyncio
@pytest.mark.parametrize("msg,tid", [
    ("my mother passed away last week, I just feel numb", "f6-grief"),
    ("I feel so alone right now, I don't have anyone to talk to", "f6-lonely"),
])
async def test_grief_and_loneliness_stay_presence(monkeypatch, msg, tid):
    # Already correct on master; lock it so a future change can't regress it.
    monkeypatch.setattr(_cfg, "VENTING_SUPPRESSION_ENABLED", True)
    r = await _drive(msg, tid)
    assert r.get("active_skill_id") is None
