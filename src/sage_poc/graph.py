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

CRISIS_RESPONSE = (
    "I'm really concerned about what you've shared. "
    "Please reach out to a crisis line now — "
    "in the UAE: 800 4673 (800-HOPE), or emergency: 999. "
    "You don't have to face this alone."
    # 800-HOPE verified correct UAE number; "Tawazun" removed (no UAE service by this name);
    # 988 removed (US-only, unreachable from UAE); 999 added (24/7 UAE emergency)
)

CRISIS_RESPONSE_AR = (
    "أنا مهتم جداً بسلامتك وبما شاركته معي. "
    "أرجوك تواصل مع خط دعم الصحة النفسية الآن — "
    "في الإمارات: 800 4673 (800-HOPE)، أو رقم الطوارئ: 999. "
    "أنت لست وحدك."
    # 800-HOPE verified correct UAE number; 988 removed (US-only, unreachable from UAE);
    # "توازن" removed (no UAE service by this name); 999 added (24/7 UAE emergency)
)

# For E5-type queries: user is asking about resources proactively, not in acute crisis.
# Richer list than the acute crisis response; no "immediate danger" framing.
CRISIS_RESPONSE_EXTENDED = (
    "Here are crisis and mental health resources in the UAE:\n"
    "- CDA Mental Health Support: 800-4888\n"
    "- National Lifeline (Estijaba): 800-HOPE (800-4673)\n"
    "- Emergency Services: 999\n"
    "- Al Amal Psychiatric Hospital: in-person psychiatric support\n"
    "- Lighthouse Arabia, Camali Clinic, American Center for Psychiatry and Neurology: "
    "therapy in Dubai\n\n"
    "If you're in immediate danger, please call 999 or go to your nearest emergency room."
)


def _crisis_response_node(state: SageState) -> dict:
    lang = state.get("detected_language", "en")
    response = CRISIS_RESPONSE_AR if lang == "ar" else CRISIS_RESPONSE

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
        }
        print(f"\n[AUDIT:CRISIS] {json.dumps(audit, indent=2)}")

    history = state.get("conversation_history", []) + [
        {"role": "user", "content": state.get("message_en", state.get("raw_message", ""))},
        {"role": "assistant", "content": CRISIS_RESPONSE},
    ]

    return {
        "is_safe": False,
        "active_skill_id": None,
        "active_step_id": None,
        "response": response,
        "response_en": CRISIS_RESPONSE,
        "path": path,
        "conversation_history": history,
        "turn_count": state.get("turn_count", 0) + 1,
    }


def _route_after_safety(state: SageState) -> str:
    return "safe" if state["is_safe"] else "crisis"


def _route_after_intent(state: SageState) -> str:
    intent = state.get("primary_intent", "general_chat")
    confidence = state.get("intent_confidence", 1.0)

    if intent == "crisis":
        return "crisis"
    if intent == "scope_refusal":
        return "gate"
    if intent == "jailbreak":
        return "gate"
    if confidence < 0.6:
        return "low_confidence"
    if intent == "exit_skill":
        return "skill_executor" if state.get("active_skill_id") else "freeflow"
    if intent == "new_skill":
        return "skill_select"
    if intent == "skill_continuation" and state.get("active_skill_id"):
        return "skill_executor"
    return "freeflow"


def _set_gate_path_node(state: SageState) -> dict:
    """Intermediate node: stamps gate_path from primary_intent before output_gate."""
    intent = state.get("primary_intent", "standard")
    gate_path = intent if intent in ("scope_refusal", "jailbreak") else "standard"
    return {"gate_path": gate_path, "path": state["path"] + ["gate_path_set"]}


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
    graph.add_node("gate_path_set", _set_gate_path_node)

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
        "gate": "gate_path_set",
    })
    graph.add_edge("gate_path_set", "output_gate")
    graph.add_edge("low_confidence_respond", "output_gate")

    graph.add_conditional_edges("skill_select", _route_after_skill_select, {
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
    })

    graph.add_edge("skill_executor", "freeflow_respond")
    graph.add_edge("freeflow_respond", "output_gate")
    graph.add_edge("output_gate", END)

    return graph.compile()
