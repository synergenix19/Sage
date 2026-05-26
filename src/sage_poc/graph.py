import json
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from sage_poc.state import SageState
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.nodes.intent_route import intent_route_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node
from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.nodes.skill_executor import skill_executor_node
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.output_gate import output_gate_node
from sage_poc.config import AUDIT_LOG_ENABLED

def _crisis_response_node(state: SageState) -> dict:
    from sage_poc.rules import engine as rules_engine

    lang = state.get("detected_language", "en")

    crisis_result = rules_engine.evaluate("crisis_content", {
        "language": lang,
        "crisis_level": "acute",
    })

    if crisis_result.fired:
        response_text = crisis_result.fired[0].action["response_text"]
    else:
        # Hard fallback: should never fire if JSON files are present
        response_text = (
            "Please reach out for support now. UAE: MoHAP Counselling Line 800 46342 (free, 24/7) or emergency: 999."
            if lang != "ar"
            else "أرجوك تواصل مع خط وزارة الصحة 800 46342 أو الطوارئ 999 الآن."
        )

    path = state["path"] + ["crisis_response"]

    if AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "CRISIS_RESPONSE",
            "turn": state.get("turn_count"),
            "detected_language": lang,
            "crisis_flags": state.get("crisis_flags", []),
            "clinical_flags": state.get("clinical_flags", []),
            "active_skill_cleared": state.get("active_skill_id"),
            "crisis_content_rule": crisis_result.fired[0].rule_id if crisis_result.fired else "fallback",
        }
        print(f"\n[AUDIT:CRISIS] {json.dumps(audit, indent=2)}")

    history = state.get("conversation_history", []) + [
        {"role": "user", "content": state.get("message_en", state.get("raw_message", ""))},
        {"role": "assistant", "content": response_text},
    ]

    return {
        "is_safe": False,
        "active_skill_id": None,
        "active_step_id": None,
        "gate_path": "crisis",
        "response": response_text,
        "response_en": response_text,
        "path": path,
        "conversation_history": history,
        "turn_count": state.get("turn_count", 0) + 1,
        "crisis_state": "monitoring",
        "s7_result": None,
        "s7_method": None,
    }


def _route_after_safety(state: SageState) -> str:
    if state.get("crisis_state") == "monitoring":
        # In monitoring: only re-escalate if S1-S6 fired directly or S7 classified a new crisis
        if not state["is_safe"] or state.get("s7_result") == "NEW_CRISIS":
            return "crisis"
        return "safe"
    return "safe" if state["is_safe"] else "crisis"


def _route_after_intent(state: SageState) -> str:
    intent = state.get("primary_intent", "general_chat")
    confidence = state.get("intent_confidence", 1.0)

    if intent == "crisis":
        return "crisis"
    if intent == "scope_refusal":
        return "gate"
    if intent == "jailbreak":
        # NOTE: jailbreak in monitoring state: persona reassertion takes priority.
        # crisis_state remains 'monitoring' — S7 will re-evaluate on the next turn.
        return "gate"
    # Post-crisis monitoring takes priority over confidence gating — short or fragmented
    # messages are expected after a crisis; route to skill_select regardless of confidence.
    if state.get("crisis_state") == "monitoring":
        return "skill_select"
    if confidence < 0.6:
        return "low_confidence"
    if intent == "exit_skill":
        return "skill_executor" if state.get("active_skill_id") else "freeflow"
    if intent == "new_skill":
        return "skill_select"
    if intent == "skill_continuation" and state.get("active_skill_id"):
        return "skill_executor"
    return "freeflow"


def _route_after_skill_select(state: SageState) -> str:
    return "skill_executor" if state.get("active_skill_id") else "freeflow"


def build_graph(checkpointer=None) -> CompiledStateGraph:
    graph = StateGraph(SageState)

    graph.add_node("safety_check", safety_check_node)
    graph.add_node("intent_route", intent_route_node)
    graph.add_node("low_confidence_respond", low_confidence_respond_node)
    graph.add_node("skill_select", skill_select_node)
    graph.add_node("skill_executor", skill_executor_node)
    graph.add_node("freeflow_respond", freeflow_respond_node)
    graph.add_node("output_gate", output_gate_node)
    graph.add_node("crisis_response", _crisis_response_node)

    graph.set_entry_point("safety_check")

    graph.add_conditional_edges("safety_check", _route_after_safety, {
        "safe": "intent_route",
        "crisis": "crisis_response",
    })
    graph.add_edge("crisis_response", END)

    graph.add_conditional_edges("intent_route", _route_after_intent, {
        "skill_select": "skill_select",
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
        "crisis": "crisis_response",
        "low_confidence": "low_confidence_respond",
        "gate": "output_gate",
    })
    graph.add_edge("low_confidence_respond", "output_gate")

    graph.add_conditional_edges("skill_select", _route_after_skill_select, {
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
    })

    graph.add_edge("skill_executor", "freeflow_respond")
    graph.add_edge("freeflow_respond", "output_gate")
    graph.add_edge("output_gate", END)

    return graph.compile(checkpointer=checkpointer)
