import json
import re
from datetime import datetime, timezone
from sage_poc.state import SageState
from sage_poc.language import translate_to_arabic
from sage_poc.config import AUDIT_LOG_ENABLED
from sage_poc.rules import engine as rules_engine

SCOPE_REFUSAL_RESPONSE = (
    "That's a question better answered by a medical professional or licensed therapist. "
    "I want to make sure you get accurate information. I can help you think through "
    "how you're feeling about it, or find some general information. Would either of those help?"
)

_FORMAT_VIOLATIONS = re.compile(
    r"—"                            # em dash
    r"|\*\*"                        # bold markdown
    r"|["
    r"\U0001F300-\U0001F9FF"        # misc symbols, emoticons, transport, flags
    r"\U00002600-\U000027BF"        # misc symbols (weather, chess, etc.)
    r"\U0001FA00-\U0001FAFF"        # extended symbols and pictographs
    r"]"
)

JAILBREAK_RESPONSE = (
    "I'm Sage, a wellness companion here to offer emotional support and evidence-based coping "
    "techniques. That's my role. What's been on your mind today?"
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

    # Cultural output validation — audit-only, non-blocking
    if gate_path not in ("scope_refusal", "jailbreak"):
        cultural_violations = rules_engine.evaluate("cultural_output", {
            "response_text": response_en,
            "message_en": state.get("message_en", ""),
            "clinical_flags": state.get("clinical_flags", []),
        })
        for rule in cultural_violations.fired:
            print(
                f"\n[CULTURAL OUTPUT VIOLATION] {rule.rule_id} v{rule.version}: "
                f"{rule.action.get('message', rule.action.get('type', ''))}"
            )
        cultural_output_violations = [r.rule_id for r in cultural_violations.fired]
    else:
        cultural_output_violations = []

    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        print(f"\n[FORMAT VIOLATION] Disallowed formatting detected: {violations}")

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
            "skill_match_method": state.get("skill_match_method"),
            "semantic_score": state.get("semantic_score"),
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
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": state["turn_count"] + 1,
        "conversation_history": state["conversation_history"] + [
            {"role": "user", "content": state["message_en"]},
            {"role": "assistant", "content": response_en},
        ],
        "cultural_output_violations": cultural_output_violations,
    }
