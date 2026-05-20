import json
from datetime import datetime, timezone
from sage_poc.state import SageState
from sage_poc.language import translate_to_arabic
from sage_poc.config import AUDIT_LOG_ENABLED

SCOPE_REFUSAL_RESPONSE = (
    "That's a question that's better answered by a medical professional or licensed therapist — "
    "I want to make sure you get accurate information. What I can do is help you think through "
    "how you're feeling about it, or find some general information. Would either of those help?"
)

JAILBREAK_RESPONSE = (
    "I'm Sage — a wellness companion built to offer emotional support and evidence-based coping "
    "techniques. That's my role, and it's what I'm here for. What's been on your mind today?"
)


def output_gate_node(state: SageState) -> dict:
    gate_path = state.get("gate_path")
    lang = state["detected_language"]
    path = state["path"] + ["output_gate"]

    # 3-path gate: scope_refusal and jailbreak bypass the LLM response entirely
    if gate_path == "scope_refusal":
        response_en = SCOPE_REFUSAL_RESPONSE
    elif gate_path == "jailbreak":
        response_en = JAILBREAK_RESPONSE
    else:
        response_en = state["response_en"] or ""

    if lang == "ar":
        final_response = translate_to_arabic(response_en)
    else:
        final_response = response_en

    if AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": state["turn_count"],
            "path": path,
            "gate_path": gate_path or "standard",
            "detected_language": lang,
            "primary_intent": state.get("primary_intent"),
            "active_skill": state.get("active_skill_id"),
            "executed_step": state.get("executed_step_id"),
            "next_step": state.get("active_step_id"),
            "emotional_intensity": state.get("emotional_intensity"),
            "engagement": state.get("engagement"),
            "is_safe": state.get("is_safe"),
            "clinical_flags": state.get("clinical_flags", []),
            "escalation": state.get("escalation_triggered"),
        }
        print(f"\n[AUDIT] {json.dumps(audit, indent=2)}")

        if state.get("clinical_flags"):
            print(f"\n[CLINICAL FLAGS] {', '.join(state['clinical_flags'])}")
        if state.get("escalation_triggered"):
            esc = state["escalation_triggered"]
            print(f"\n[ESCALATION {esc['level']}] {esc['reason']}")

    return {
        "response": final_response,
        "path": path,
        "turn_count": state["turn_count"] + 1,
        "conversation_history": state["conversation_history"] + [
            {"role": "user", "content": state["message_en"]},
            {"role": "assistant", "content": response_en},
        ],
    }
