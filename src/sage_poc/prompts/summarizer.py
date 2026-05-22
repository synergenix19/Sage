import logging
from sage_poc.llm import get_classifier
from sage_poc.resilience import resilient_invoke

_log = logging.getLogger(__name__)

_SUMMARY_SYSTEM = (
    "You are summarising a mental health support conversation for context continuity. "
    "In 2-3 sentences, extract: (1) the key life situation the user described, "
    "(2) the main emotional themes, "
    "(3) anything the user has already shared about their daily life or routines, "
    "(4) any commitments or next steps the assistant offered (e.g. 'we can try that next time', "
    "'let's come back to this', 'we could try a grounding exercise'). "
    "Be factual. Do not advise or evaluate. Do not use bullet points or headers. "
    "Do not include names, phone numbers, or other directly identifying details."
)


async def summarise_history(history: list[dict], llm=None) -> str:
    if llm is None:
        llm = get_classifier()
    turns = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )
    messages = [
        {"role": "system", "content": _SUMMARY_SYSTEM},
        {"role": "user", "content": f"Conversation:\n{turns}"},
    ]
    result = await resilient_invoke(
        llm, messages, node="summariser", language="en"
    )
    return result.strip()
