from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.prompts import compose_prompt, PERSONA  # re-exported for backward compat
from sage_poc.prompts.composer import _sanitize_assistant_turn  # re-exported for backward compat

__all__ = ["compose_prompt", "PERSONA", "freeflow_respond_node", "_sanitize_assistant_turn"]


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
