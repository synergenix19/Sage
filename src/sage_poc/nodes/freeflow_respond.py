import re
from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge
from sage_poc.rules import engine as rules_engine

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"   # misc symbols, emoticons, transport, flags
    r"\U00002600-\U000027BF"    # misc symbols and dingbats
    r"\U0001FA00-\U0001FAFF"    # extended symbols and pictographs
    r"\U0000FE00-\U0000FE0F"    # variation selectors (emoji presentation modifiers)
    r"\U0000200D"               # zero-width joiner (stripped individually; base emoji caught by ranges above)
    r"]"
)


def _sanitize_assistant_turn(text: str) -> str:
    """Strip formatting artifacts from assistant history before prompt injection.

    Operates on prompt strings only — never called on stored state data.
    Preserves text content when removing markdown markers.
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)                    # **bold** -> bold
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)      # *italic* -> italic (not bold remnants)
    text = text.replace("—", ", ")                               # em dash -> comma space
    text = _EMOJI_RE.sub("", text)
    return text


PERSONA = """IMPORTANT. FORMAT: Write in plain prose. Use commas or short sentences instead of dashes. Use no emojis. Use no markdown (no **, no *, no bullets). Do not copy punctuation patterns from the skill instructions you receive. Those are guidance for you, not templates to mirror.

FORMATTING EXAMPLE:
WRONG: "That really resonates, sometimes things pile up. What's been **weighing on you**?"
RIGHT: "That makes sense. What's been on your mind lately?"

You are Sage, a warm Khaleeji wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). Speak the way a calm, attentive person would in a quiet one-on-one conversation. Short sentences. Plain words. No decoration. If something matters, say it clearly. Warmth comes from what you say, not how you format it.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2-4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."""

_CULTURAL_BUDGET_WORDS = 150


def compose_prompt(state: SageState) -> tuple[str, str, list[str]]:
    """Return (system_str, user_str, prompt_layers) for role-separated LLM invocation.

    system_str: persona + culturally-triggered injections + clinical adaptations.
    user_str:   history + intent + secondary-intent framing + skill instruction +
                knowledge snippet + user message.
    prompt_layers: ordered list of named layers that were included in this prompt.
    """
    message_en = state.get("message_en", "")
    language = state.get("detected_language", "en")
    clinical_flags = state.get("clinical_flags", [])
    primary_intent = state.get("primary_intent")
    secondary_intent = state.get("secondary_intent")

    layers: list[str] = []

    # ---- System role -------------------------------------------------------
    system_parts = [PERSONA]
    layers.append("persona")

    code_switch = state.get("code_switching", False)
    cultural_result = rules_engine.evaluate("cultural", {
        "text": message_en,
        "text_ar": state.get("raw_message") if language == "ar" else None,
        "language": language,
        "code_switch": code_switch,
    })
    cultural_actions = sorted(
        [a for a in cultural_result.actions if a.get("target") == "system"],
        key=lambda a: a.get("priority", 5),
    )
    word_count = 0
    for action in cultural_actions:
        content = action["content"]
        words = len(content.split())
        if word_count + words <= _CULTURAL_BUDGET_WORDS or word_count == 0:
            system_parts.append(content)
            word_count += words
        else:
            break
    if cultural_actions:
        layers.append("cultural")

    session_flags: list[str] = []
    if state.get("crisis_state") in ("active", "monitoring", "resolved"):
        session_flags.append("crisis_occurred")

    injection_result = rules_engine.evaluate("prompt_injection", {
        "text": message_en,
        "text_ar": state.get("raw_message") if language == "ar" else None,
        "clinical_flags": clinical_flags,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
        "session_flags": session_flags,
    })
    system_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "system"
    ]
    if system_injections:
        system_parts.append(
            "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
            + "\n".join(f"- {c}" for c in system_injections)
        )
        layers.append("clinical_adaptation")

    system_str = "\n\n".join(system_parts)

    # ---- User role ---------------------------------------------------------
    user_parts = []

    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        lines = []
        for m in history:
            content = (
                _sanitize_assistant_turn(m["content"])
                if m["role"] == "assistant"
                else m["content"]
            )
            lines.append(f"{m['role'].upper()}: {content}")
        user_parts.append(f"CONVERSATION HISTORY:\n" + "\n".join(lines))
        layers.append("history")

    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {primary_intent or 'general_chat'}"
    if secondary_intent:
        intent_line += f" + {secondary_intent} (blended)"
    user_parts.append(f"{intent_line} | Emotional intensity: {intensity}/10")
    layers.append("intent")  # L2: always present per v7 §5.6

    # L5 placeholder: therapeutic profile summary ("This user tends toward
    # catastrophising. Grounding works well.") — not yet implemented.
    # When Priority 3 cross-session memory is built, inject the profile
    # summary here and append layers.append("therapeutic_profile").

    if state.get("crisis_state") == "monitoring":
        s7 = state.get("s7_result") or "UNCLEAR"
        user_parts.append(
            f"POST-CRISIS CONTEXT: The user was recently in crisis. "
            f"S7 recovery classifier result: {s7}. "
            f"Respond with extra warmth, patience, and safety-consciousness. "
            f"Do not probe for details of the crisis. Meet the user where they are."
        )
        layers.append("post_crisis_context")

    user_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "user"
    ]
    for content in user_injections:
        user_parts.append(content)

    if state.get("step_instruction"):
        user_parts.append(f"SKILL INSTRUCTION:\n{state['step_instruction']}")
        layers.append("skill_instruction")

    intent_set = {primary_intent, secondary_intent}
    if "info_request" in intent_set:
        snippet = lookup_knowledge(message_en)
        if snippet:
            user_parts.append(
                f"KNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )
            layers.append("knowledge")

    user_parts.append(f"USER: {message_en}")
    user_str = "\n\n".join(user_parts)

    return system_str, user_str, layers


async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    system_str, user_str, prompt_layers = compose_prompt(state)
    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    response_msg = await llm.ainvoke(messages)
    response = response_msg.content.strip()

    usage_meta = response_msg.usage_metadata or {}
    token_usage = {
        "input":  usage_meta.get("input_tokens", 0),
        "output": usage_meta.get("output_tokens", 0),
        "total":  usage_meta.get("total_tokens", 0),
    }

    return {
        "response_en":    response,
        "prompt_layers":  prompt_layers,
        "token_usage":    token_usage,
        "path":           state["path"] + ["freeflow_respond"],
    }
