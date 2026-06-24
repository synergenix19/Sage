"""Deterministic detection of explicit advice-delegation and question-fatigue.

This is intentionally NOT part of the LLM intent classifier (intent_route's
INTENT_SYSTEM), which carries a documented single-point-of-failure warning. The
signal here is keyword-detectable and a conversation-state repair pattern, so it is
computed deterministically and sets the `directive_posture` flag. The composer then
selects a stronger directive L2 variant; output_gate strips any trailing question.

House style mirrors skill_executor.L1_EXIT_PHRASES: module-level phrase list +
substring match on lowercased text.
"""
from sage_poc.state import SageState

# High-precision: explicit handing-over of the decision, OR explicit objection to
# being questioned. Deliberately excludes genuine first questions ("how do I...",
# "what should I think about") which warrant one round of exploration.
_DIRECTIVE_PHRASES = [
    "just tell me what to do",
    "just tell me",
    "you tell me",
    "you decide",
    "you pick",
    "you choose",
    "tell me what to do",
    "give me answers",
    "i want answers",
    "i need answers",
    "answers not questions",
    "answers, not questions",
    "stop asking me questions",
    "stop asking questions",
    "stop asking me",
    "quit asking",
    "no more questions",
    "enough questions",
    "i don't need more questions",
    "i dont need more questions",
    "you need to guide me",
    "guide me, not ask me",
    "guide me not ask me",
    "you're the one with the answers",
    "youre the one with the answers",
    "you are the one with the answers",
    "i thought you were the one with the answers",
]

# Repair-signal pushback markers: short objections to being questioned that only count
# when the PRIOR assistant turn actually asked a question.
_REPAIR_PUSHBACK = [
    "why do you keep asking",
    "what do you keep asking",
    "why do you keep questioning",
    "you keep asking",
    "you keep questioning",
    "more questions",
    "again with the questions",
    "another question",
]


def _last_assistant_asked_question(history: list[dict]) -> bool:
    for msg in reversed(history or []):
        if msg.get("role") == "assistant":
            return msg.get("content", "").rstrip().endswith("?")
    return False


def detect_directive_request(state: SageState, primary_intent: str | None = None) -> bool:
    """True when the user has explicitly delegated the decision to Sage, or is
    objecting to being questioned after Sage asked a question, OR when the
    current-turn intent is info_request (answer-first mode). Deterministic, no LLM.

    NOTE: there is deliberately NO bare question-mark (? or Arabic question mark)
    trigger. A question mark does not disambiguate an info request from an emotional
    disclosure ("am I broken?"); firing directive_posture on those would let
    _strip_trailing_question remove the earned open question from a Reflect-mode reply.
    Genuine factual/list questions already classify as info_request via the LLM
    classifier, so the intent trigger covers them without the false positive.
    """
    text = (state.get("message_en") or "").lower()
    if not text:
        return False
    # D4: intent-gated answer-first trigger. Intent-only, no punctuation shortcut.
    if primary_intent == "info_request":
        return True
    if any(phrase in text for phrase in _DIRECTIVE_PHRASES):
        return True
    if _last_assistant_asked_question(state.get("conversation_history") or []):
        if any(marker in text for marker in _REPAIR_PUSHBACK):
            return True
    return False
