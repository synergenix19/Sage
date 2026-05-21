from __future__ import annotations

_RECOVERY_KEYWORDS = frozenset([
    "feeling better", "feel better", "better now", "much better", "a lot better",
    "calmer", "calm now", "calmed down",
    "okay now", "i'm okay", "im okay", "i am okay",
    "thank you", "thanks for", "that helped", "that was helpful",
    "relieved", "feel relieved", "feeling relieved",
    "safer", "feel safe", "feeling safe",
    "not thinking about", "stopped thinking about",
    "going to call", "called the", "reached out", "got support", "got help",
])

_STILL_DISTRESSED_KEYWORDS = frozenset([
    # Non-crisis distress signals only — phrases that overlap with S1–S6 crisis lexicon are
    # intentionally excluded. If a message contains "want to die" or "going to end it",
    # S1–S6 set is_safe=False and _route_after_safety routes to crisis before S7 is relevant.
    "still not okay", "still not well", "still not good",
    "still feel down", "still feeling down", "still feel low", "still feeling low",
    "still struggling", "still the same", "still upset",
    "nothing has changed", "nothing changed", "nothing is different",
    "doesn't help", "does not help", "doesn't work", "does not work",
    "nothing helps", "nothing works",
    "same as before", "same as always",
    "can't stop thinking", "cannot stop thinking",
    "still can't", "haven't been able to",
])

S7_SYSTEM = (
    "You are a clinical triage classifier. A user was recently in acute crisis. "
    "Classify their CURRENT message ONLY (ignore any prior context) using one of four labels:\n\n"
    "RECOVERING       — user shows relief, improved mood, gratitude, or reduced distress\n"
    "STILL_DISTRESSED — user remains in active distress but without new explicit harm intent\n"
    "UNCLEAR          — insufficient information to classify\n"
    "NEW_CRISIS       — user shows new or escalating explicit harm intent\n\n"
    "Respond with exactly one word: RECOVERING, STILL_DISTRESSED, UNCLEAR, or NEW_CRISIS."
)

_VALID_LABELS = frozenset({"RECOVERING", "STILL_DISTRESSED", "UNCLEAR", "NEW_CRISIS"})


def evaluate_s7(message_en: str, llm=None) -> tuple[str, str]:
    """Return (label, method) where method is 'keyword' or 'llm'.

    Deterministic keyword tier runs first; STILL_DISTRESSED checked before RECOVERING.
    LLM is called only when keywords produce no match.
    Evaluates the current message in isolation — no conversation history passed to LLM.
    """
    text = message_en.lower()

    for kw in _STILL_DISTRESSED_KEYWORDS:
        if kw in text:
            return "STILL_DISTRESSED", "keyword"

    for kw in _RECOVERY_KEYWORDS:
        if kw in text:
            return "RECOVERING", "keyword"

    if llm is None:
        from sage_poc.llm import get_classifier
        llm = get_classifier()

    messages = [
        {"role": "system", "content": S7_SYSTEM},
        {"role": "user", "content": message_en},
    ]
    response = llm.invoke(messages)
    label = response.content.strip().upper()
    if label not in _VALID_LABELS:
        return "UNCLEAR", "llm"
    return label, "llm"
