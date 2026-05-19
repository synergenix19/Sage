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

CRISIS_RESPONSE = (
    "I'm really concerned about what you've shared. "
    "Please reach out to a crisis line immediately — "
    "in the UAE: Tawazun 800-HOPE (4673), or international: 988 (US). "
    "You don't have to face this alone."
)


def _crisis_response_node(state: SageState) -> dict:
    return {
        "is_safe": False,
        "response": CRISIS_RESPONSE,
        "response_en": CRISIS_RESPONSE,
        "path": state["path"] + ["crisis_response"],
    }


def _route_after_safety(state: SageState) -> str:
    return "safe" if state["is_safe"] else "crisis"


def _route_after_intent(state: SageState) -> str:
    intent = state.get("primary_intent", "general_chat")
    confidence = state.get("intent_confidence", 1.0)

    if intent == "crisis":
        return "crisis"
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


def build_graph() -> CompiledStateGraph:
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
    })
    graph.add_edge("low_confidence_respond", "output_gate")

    graph.add_conditional_edges("skill_select", _route_after_skill_select, {
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
    })

    graph.add_edge("skill_executor", "freeflow_respond")
    graph.add_edge("freeflow_respond", "output_gate")
    graph.add_edge("output_gate", END)

    return graph.compile()
