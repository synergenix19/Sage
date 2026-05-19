from sage_poc.state import SageState
from sage_poc.llm import get_responder

_SYSTEM = (
    "You are Sage, a warm wellness companion. "
    "The user's message was ambiguous and you are not sure what they need. "
    "Ask ONE gentle, open-ended clarifying question to understand better. "
    "Be warm and non-judgmental. Maximum 2 sentences."
)


def low_confidence_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": state["message_en"]},
    ]
    response = llm.invoke(messages).content.strip()

    return {
        "response_en": response,
        "path": state["path"] + ["low_confidence_respond"],
    }
