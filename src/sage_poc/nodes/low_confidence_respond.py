from sage_poc.state import SageState
from sage_poc.llm import get_responder, get_fallback_responder
from sage_poc.resilience import resilient_stream
from sage_poc.prompts import compose_prompt


async def low_confidence_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()
    fallback_llm = get_fallback_responder()

    # v7 §5.6.3: compose L0 + the low_confidence L2 template rather than a
    # hardcoded system prompt (which bypassed L0 entirely). low_confidence is a
    # confidence-routing outcome, not a primary_intent, so the L2 template is
    # selected via explicit override. The one-gentle-question / max-two-sentences
    # behaviour is now carried by the low_confidence L2 template content.
    system_str, user_str, prompt_layers = compose_prompt(
        state, l2_intent_override="low_confidence"
    )

    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
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
        "prompt_layers": prompt_layers,
        "path": state["path"] + ["low_confidence_respond"],
    }
