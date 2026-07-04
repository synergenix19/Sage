"""W2 — warm de-escalation: monitoring -> supportive step-down (signed G4).

After a crisis, crisis_state='monitoring' runs S7 each turn. G4: 2 CONSECUTIVE S7-clear turns AND no
S1/S3 fire -> step down monitoring->supportive (never to 'none' in-session). The step-down is a state
computation in safety_check; it does NOT touch _route_after_safety (supportive falls through routing
to the normal graph on its own, since it is not 'monitoring'). STEP_DOWN_CLEAR_TURNS=2 named constant.
"""
import pytest
from sage_poc.nodes.safety_check import safety_check_node, STEP_DOWN_CLEAR_TURNS
from tests.test_nodes import make_state

_RECOVERING = "thank you, feeling much better"   # S7 keyword -> RECOVERING, is_safe (no crisis kw)
_STILL = "still struggling"                       # S7 keyword -> STILL_DISTRESSED


def test_step_down_clear_turns_constant_is_two():
    assert STEP_DOWN_CLEAR_TURNS == 2


@pytest.mark.asyncio
async def test_first_clear_monitoring_turn_stays_monitoring_counter_1():
    state = make_state(raw_message=_RECOVERING, crisis_state="monitoring", monitoring_clear_turns=0)
    r = await safety_check_node(state)
    assert r["s7_result"] == "RECOVERING"
    assert r["crisis_state"] == "monitoring", "one clear turn must not step down yet"
    assert r["monitoring_clear_turns"] == 1


@pytest.mark.asyncio
async def test_second_consecutive_clear_turn_steps_down_to_supportive():
    # counter already 1 (one prior clear turn) + this clear turn = 2 -> step down.
    state = make_state(raw_message=_RECOVERING, crisis_state="monitoring", monitoring_clear_turns=1)
    r = await safety_check_node(state)
    assert r["monitoring_clear_turns"] == 2
    assert r["crisis_state"] == "supportive", "2 consecutive clear turns must step down to supportive"


@pytest.mark.asyncio
async def test_non_clear_turn_resets_counter_and_stays_monitoring():
    # A STILL_DISTRESSED turn breaks the streak: counter -> 0, stays monitoring (no step-down).
    state = make_state(raw_message=_STILL, crisis_state="monitoring", monitoring_clear_turns=1)
    r = await safety_check_node(state)
    assert r["s7_result"] == "STILL_DISTRESSED"
    assert r["monitoring_clear_turns"] == 0, "a non-clear turn resets the consecutive-clear streak"
    assert r["crisis_state"] == "monitoring"


@pytest.mark.asyncio
async def test_step_down_never_goes_to_none_in_session():
    # Even a third clear turn after stepping down must NOT reach 'none' — supportive is the floor.
    state = make_state(raw_message=_RECOVERING, crisis_state="supportive", monitoring_clear_turns=2)
    r = await safety_check_node(state)
    assert r["crisis_state"] != "none", "supportive must never step down to none in-session"
    # supportive is not 'monitoring' -> S7 is not run on a stepped-down turn.
    assert r["s7_result"] is None


@pytest.mark.asyncio
async def test_s1_fire_in_monitoring_does_not_step_down():
    # An S1 crisis fire (is_safe False) is a re-escalation, never a clear turn: counter stays 0,
    # crisis_state stays monitoring (routing re-escalates it separately). Guards the safety floor.
    state = make_state(raw_message="I want to kill myself", crisis_state="monitoring", monitoring_clear_turns=1)
    r = await safety_check_node(state)
    assert r["is_safe"] is False
    assert r["monitoring_clear_turns"] == 0
    assert r["crisis_state"] == "monitoring", "a crisis fire must never step down"


@pytest.mark.asyncio
async def test_counter_untouched_when_not_monitoring():
    # crisis_state 'none': no S7, no step-down computation; counter stays at its incoming value.
    state = make_state(raw_message=_RECOVERING, crisis_state="none", monitoring_clear_turns=0)
    r = await safety_check_node(state)
    assert r["s7_result"] is None
    assert r["crisis_state"] == "none"


@pytest.mark.asyncio
async def test_step_down_state_survives_langgraph_reducer():
    # Bug-#2 lesson: assert the new channels survive the reducer (not just safety_check's return dict).
    from langgraph.graph import StateGraph, START, END
    from sage_poc.state import SageState

    async def _node(state):
        return {"crisis_state": "supportive", "monitoring_clear_turns": 2}

    g = StateGraph(SageState)
    g.add_node("n", _node)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    out = await g.compile().ainvoke({"raw_message": "x"})
    assert out.get("crisis_state") == "supportive", "SageState dropped crisis_state step-down"
    assert out.get("monitoring_clear_turns") == 2, "SageState dropped monitoring_clear_turns channel"
