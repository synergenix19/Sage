from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge

PERSONA = """You are Sage, a warm and empathetic wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). You are conversational, never clinical or cold. You listen deeply, reflect back what you hear, and gently guide users toward insight.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2–4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful.

ISLAMIC CULTURAL CONTEXT: When a user frames hardship through a religious lens, honour that framing. Use concepts of sabr (صبر — patient perseverance), tawakkul (توكّل — trust in God), and ibtila (ابتلاء — trial/test) where appropriate. Frame hardship as ibtila — a test, not a punishment. Never pathologise religious belief or suggest faith is the cause of distress.

COLLECTIVIST CULTURAL CONTEXT: Many users hold collectivist family values where individual desires and family obligations are both real and intertwined. Avoid framing like "your own needs come first" or "set yourself free from family expectations." Instead use language like "finding a path that honours both you and your family." Do not default to Western individualist framing."""

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


def compose_prompt(state: SageState) -> tuple[str, str]:
    """Return (system_str, user_str) for proper role-separated LLM invocation.

    system_str: static behavioral guidance (persona + clinical adaptations).
    user_str:   dynamic contextual content (history, intent, skill instruction,
                knowledge snippet, current user message).
    """
    # --- System role: persona + clinical behavioral constraints ---
    system_parts = [PERSONA]

    clinical = state.get("clinical_flags", [])
    if clinical:
        adaptations = [_CLINICAL_ADAPTATIONS[f] for f in clinical if f in _CLINICAL_ADAPTATIONS]
        if adaptations:
            system_parts.append(
                "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
                + "\n".join(f"- {a}" for a in adaptations)
            )

    system_str = "\n".join(system_parts)

    # --- User role: context + current turn ---
    user_parts = []

    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
        user_parts.append(f"CONVERSATION HISTORY:\n{history_text}")

    intent = state.get("primary_intent") or "general_chat"
    secondary = state.get("secondary_intent")
    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {intent}"
    if secondary:
        intent_line += f" + {secondary} (blended)"
    user_parts.append(f"{intent_line} | Emotional intensity: {intensity}/10")

    if state.get("step_instruction"):
        user_parts.append(f"SKILL INSTRUCTION:\n{state['step_instruction']}")

    # P2-8: inject knowledge for primary OR secondary info_request intent
    intent_set = {state.get("primary_intent"), state.get("secondary_intent")}
    if "info_request" in intent_set:
        snippet = lookup_knowledge(state["message_en"])
        if snippet:
            user_parts.append(
                f"KNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )

    user_parts.append(f"USER: {state['message_en']}")
    user_str = "\n\n".join(user_parts)

    return system_str, user_str


async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    system_str, user_str = compose_prompt(state)
    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    chunks: list[str] = []
    async for chunk in llm.astream(messages):
        if isinstance(chunk.content, str) and chunk.content:
            chunks.append(chunk.content)
    response = "".join(chunks).strip()

    return {
        "response_en": response,
        "path": state["path"] + ["freeflow_respond"],
    }
