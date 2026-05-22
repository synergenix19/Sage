from sage_poc.state import SageState
from sage_poc.llm import get_responder, get_fallback_responder
from sage_poc.resilience import resilient_stream

_SYSTEM = (
    "You are Sage, a warm wellness companion. "
    "The user's message was ambiguous and you are not sure what they need. "
    "Ask ONE gentle, open-ended clarifying question to understand better. "
    "Be warm and non-judgmental. Maximum 2 sentences."
)


async def low_confidence_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()
    fallback_llm = get_fallback_responder()

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": state["message_en"]},
    ]

    chunks: list[str] = []
    async for chunk in resilient_stream(
        llm,
        messages,
        node="low_confidence_respond",
        language=state.get("detected_language", "en"),
        fallback_llm=fallback_llm,
    ):
        chunks.append(chunk)

    return {
        "response_en": "".join(chunks).strip(),
        "path": state["path"] + ["low_confidence_respond"],
    }
