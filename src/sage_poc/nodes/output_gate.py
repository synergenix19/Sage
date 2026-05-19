import json
from datetime import datetime, timezone
from sage_poc.state import SageState
from sage_poc.language import translate_to_arabic


def output_gate_node(state: SageState) -> dict:
    response_en = state["response_en"] or ""
    lang = state["detected_language"]

    if lang == "ar":
        final_response = translate_to_arabic(response_en)
    else:
        final_response = response_en

    path = state["path"] + ["output_gate"]

    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "turn": state["turn_count"],
        "path": path,
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
