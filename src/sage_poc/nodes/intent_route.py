import json
import re
from sage_poc.state import SageState
from sage_poc.llm import get_classifier

INTENT_SYSTEM = """You are a routing classifier for a mental health assistant.
Analyse the user's message and return ONLY valid JSON with these fields:
- primary_intent: one of "skill_continuation" | "new_skill" | "general_chat" | "crisis" | "info_request" | "exit_skill"
- secondary_intent: the SECOND intent if two are present, or null if only one. Example: user expresses distress AND asks a factual question → primary "new_skill", secondary "info_request".
- emotional_intensity: integer 1-10 (1=calm, 10=extremely distressed)
- engagement: integer 1-10 (1=one-word/dismissive, 10=elaborating/open)
- intent_confidence: float 0.0-1.0

Rules:
- skill_continuation: user is responding to an active therapeutic skill session
- new_skill: user expresses distress, negative thoughts, or needs a therapeutic technique
- general_chat: greeting, small talk, or unrelated question
- crisis: ANY mention of self-harm, suicide, or immediate danger (redundant safety net)
- info_request: user asks a factual question about mental health
- exit_skill: user explicitly asks to stop, leave, or change topic away from the current skill

Return ONLY the JSON object. No explanation."""


def build_intent_prompt(state: SageState) -> str:
    active = f"Active skill: {state['active_skill_id']}" if state["active_skill_id"] else "No active skill."
    history_lines = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in state["conversation_history"][-3:]
    )
    history_block = f"\nRecent history:\n{history_lines}" if history_lines else ""
    return f"{active}{history_block}\n\nUser message: {state['message_en']}"


def intent_route_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_classifier()

    messages = [
        {"role": "system", "content": INTENT_SYSTEM},
        {"role": "user", "content": build_intent_prompt(state)},
    ]
    raw = llm.invoke(messages).content.strip()

    # Extract JSON — handle models that wrap in markdown fences
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    data = json.loads(match.group(0)) if match else {}

    return {
        "primary_intent": data.get("primary_intent", "general_chat"),
        "secondary_intent": data.get("secondary_intent"),
        "intent_confidence": float(data.get("intent_confidence", 0.5)),
        "emotional_intensity": int(data.get("emotional_intensity", 5)),
        "engagement": int(data.get("engagement", 5)),
        "path": state["path"] + ["intent_route"],
    }
