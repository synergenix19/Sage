"""EMR Phase 2 surface 1 — executor exit-and-rehand (the observed turn-3 defect).

The original transcript: "are there any exercises i can do" mid-psychoed advanced the
active skill's exploration step instead of honoring the request (active-skill
absorption, mechanism memo branch (d)). Now: request-for-alternative = L1 family,
evaluated before step advancement, exit with the skill's own L1 text, rehand to
skill_select.
"""
import pytest

from sage_poc import config
from sage_poc.graph import _route_after_skill_executor
from sage_poc.nodes.skill_executor import skill_executor_node


def _state(msg, *, emr, skill="psychoed_anxiety", step="connect_to_experience", intent="skill_continuation"):
    return {
        "message_en": msg, "raw_message": msg, "detected_language": "en",
        "primary_intent": intent, "path": ["safety_check", "intent_route"],
        "active_skill_id": skill, "active_step_id": step,
        "conversation_history": [], "clinical_flags": [], "new_clinical_flags_turn": [],
        "crisis_flags": [], "offered_skill_ids": [], "declined_skills": [],
        "explicit_modality_request": emr,
        "engagement": 6, "emotional_intensity": 5,
    }


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)


@pytest.mark.asyncio
async def test_request_mid_skill_exits_before_step_advancement_and_rehands():
    """The observed defect turn, exactly: request mid-psychoed. The skill exits with
    its own L1 instruction (no step advancement), the escalation record carries the
    rehand action, and the router sends the turn to skill_select."""
    out = await skill_executor_node(_state(
        "are there any exercises i can do",
        emr={"requested": True, "modality_hint": None}))
    assert out["active_skill_id"] is None
    assert out["escalation_triggered"]["action"] == "exit_with_rehand"
    assert out["escalation_triggered"]["reason"] == "modality_request:request_for_alternative"
    assert out["step_instruction"].startswith("[L1]")
    assert "modality_request_routed:executor" in out["path"]
    assert _route_after_skill_executor({**out}) == "skill_select"


@pytest.mark.asyncio
async def test_affirmation_mid_skill_never_triggers_advances_normally():
    """Both-direction guard (C3 positive): 'this is helping' carries requested=False;
    the skill stays active and the step machinery runs (positive: an executed step
    comes back, no escalation record)."""
    out = await skill_executor_node(_state(
        "this is helping", emr={"requested": False, "modality_hint": None}))
    assert out.get("escalation_triggered") is None
    assert out.get("active_skill_id") != None or "executed_step_id" in out  # noqa: E711
    assert "modality_request_routed:executor" not in out["path"]


@pytest.mark.asyncio
async def test_explicit_stop_wins_over_alternative_request_plain_exit_no_rehand():
    """A user asking to STOP is honored as a plain L1 exit even when the same turn
    also asks for an alternative — no re-offer rides an exit (conservative order:
    the real L1 evaluates first)."""
    out = await skill_executor_node(_state(
        "i want to stop this, are there any exercises i can do instead",
        emr={"requested": True, "modality_hint": None}, intent="exit_skill"))
    assert out["active_skill_id"] is None
    assert out["escalation_triggered"]["action"] != "exit_with_rehand"
    assert "modality_request_routed:executor" not in out["path"]
    assert _route_after_skill_executor({**out}) == "freeflow"


@pytest.mark.asyncio
async def test_crisis_reescalation_outranks_rehand_in_router():
    assert _route_after_skill_executor({
        "re_escalation_within_monitoring": True,
        "escalation_triggered": {"action": "exit_with_rehand"},
    }) == "crisis"


@pytest.mark.asyncio
async def test_flag_off_absorption_shape_unchanged(monkeypatch):
    """OFF is byte-identical: the request turn runs the normal step machinery (the
    pre-fix absorption shape) — this is the regression the Phase-3 re-measure
    quantifies, deliberately preserved until the flip."""
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", False)
    out = await skill_executor_node(_state(
        "are there any exercises i can do",
        emr={"requested": True, "modality_hint": None}))
    assert "modality_request_routed:executor" not in out["path"]
    assert (out.get("escalation_triggered") or {}).get("action") != "exit_with_rehand"
