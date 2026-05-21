from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge
from sage_poc.rules import engine as rules_engine

PERSONA = """You are Sage, a warm and empathetic wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). You are conversational, never clinical or cold. You listen deeply, reflect back what you hear, and gently guide users toward insight.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2–4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."""


def compose_prompt(state: SageState) -> tuple[str, str]:
    """Return (system_str, user_str) for role-separated LLM invocation.

    system_str: persona + culturally-triggered injections + clinical adaptations.
    user_str:   history + intent + secondary-intent framing + skill instruction +
                knowledge snippet + user message.
    """
    message_en = state.get("message_en", "")
    language = state.get("detected_language", "en")
    clinical_flags = state.get("clinical_flags", [])
    primary_intent = state.get("primary_intent")
    secondary_intent = state.get("secondary_intent")

    # ── System role ────────────────────────────────────────────────────────────
    system_parts = [PERSONA]

    # Cultural injections (Islamic framing, collectivist framing)
    cultural_result = rules_engine.evaluate("cultural", {
        "text": message_en,
        "language": language,
    })
    for action in cultural_result.actions:
        if action.get("target") == "system":
            system_parts.append(action["content"])

    # Prompt injection: clinical flag adaptations + secondary intent (system-targeted)
    injection_result = rules_engine.evaluate("prompt_injection", {
        "text": message_en,
        "clinical_flags": clinical_flags,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
    })
    system_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "system"
    ]
    if system_injections:
        system_parts.append(
            "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
            + "\n".join(f"- {c}" for c in system_injections)
        )

    system_str = "\n\n".join(system_parts)

    # ── User role ──────────────────────────────────────────────────────────────
    user_parts = []

    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in history
        )
        user_parts.append(f"CONVERSATION HISTORY:\n{history_text}")

    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {primary_intent or 'general_chat'}"
    if secondary_intent:
        intent_line += f" + {secondary_intent} (blended)"
    user_parts.append(f"{intent_line} | Emotional intensity: {intensity}/10")

    # Prompt injection: user-targeted injections (dialectical framing for secondary intent)
    user_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "user"
    ]
    for content in user_injections:
        user_parts.append(content)

    if state.get("step_instruction"):
        user_parts.append(f"SKILL INSTRUCTION:\n{state['step_instruction']}")

    intent_set = {primary_intent, secondary_intent}
    if "info_request" in intent_set:
        snippet = lookup_knowledge(message_en)
        if snippet:
            user_parts.append(
                f"KNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )

    user_parts.append(f"USER: {message_en}")
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
