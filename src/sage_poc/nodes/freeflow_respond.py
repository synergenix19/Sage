from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge

PERSONA = """You are Sage, a warm and empathetic wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). You are conversational, never clinical or cold. You listen deeply, reflect back what you hear, and gently guide users toward insight.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2–4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."""

_CLINICAL_ADAPTATIONS = {
    "substance_use": (
        "The user has disclosed substance use. Use motivational interviewing language. "
        "Do NOT judge or suggest immediate cessation. Explore ambivalence gently."
    ),
    "trauma_indicator": (
        "The user has disclosed trauma. Use trauma-sensitive language. "
        "Do NOT push for details. Prioritise emotional safety and containment."
    ),
    "eating_concern": (
        "The user has disclosed eating concerns. Avoid all body or weight comments. "
        "Be sensitive. Gently encourage professional support if appropriate."
    ),
    "medication_mention": (
        "The user mentioned medication. Do NOT advise on dosage or medication changes. "
        "Encourage speaking with their prescriber for any medication questions."
    ),
}


def compose_prompt(state: SageState) -> str:
    parts = [f"SYSTEM: {PERSONA}"]

    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
        parts.append(f"\nCONVERSATION HISTORY:\n{history_text}")

    intent = state.get("primary_intent") or "general_chat"
    secondary = state.get("secondary_intent")
    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {intent}"
    if secondary:
        intent_line += f" + {secondary} (blended)"
    parts.append(f"\n{intent_line} | Emotional intensity: {intensity}/10")

    if state.get("step_instruction"):
        parts.append(f"\nSKILL INSTRUCTION:\n{state['step_instruction']}")

    if state.get("secondary_intent") == "info_request":
        snippet = lookup_knowledge(state["message_en"])
        if snippet:
            parts.append(
                f"\nKNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )

    clinical = state.get("clinical_flags", [])
    if clinical:
        adaptations = [_CLINICAL_ADAPTATIONS[f] for f in clinical if f in _CLINICAL_ADAPTATIONS]
        if adaptations:
            parts.append(
                "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
                + "\n".join(f"- {a}" for a in adaptations)
            )

    parts.append(f"\nUSER: {state['message_en']}\n\nSAGE:")
    return "\n".join(parts)


def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    prompt = compose_prompt(state)
    response = llm.invoke(prompt).content.strip()

    return {
        "response_en": response,
        "path": state["path"] + ["freeflow_respond"],
    }
