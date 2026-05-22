from sage_poc.state import SageState
from sage_poc.llm import get_responder, get_fallback_responder
from sage_poc.prompts import compose_prompt, PERSONA  # re-exported for backward compat
from sage_poc.prompts.composer import _sanitize_assistant_turn  # re-exported for backward compat
from sage_poc.resilience import resilient_invoke

__all__ = ["compose_prompt", "PERSONA", "freeflow_respond_node", "_sanitize_assistant_turn"]


async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()
    fallback_llm = get_fallback_responder()

    system_str, user_str, prompt_layers = compose_prompt(state)
    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    response = await resilient_invoke(
        llm,
        messages,
        node="freeflow_respond",
        language=state.get("detected_language", "en"),
        fallback_llm=fallback_llm,
    )

    return {
        "response_en":   response,
        "prompt_layers": prompt_layers,
        "token_usage":   {},
        "path":          state["path"] + ["freeflow_respond"],
    }
