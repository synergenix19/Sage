from sage_poc.state import SageState
from sage_poc.llm import get_responder, get_fallback_responder
from sage_poc.prompts import compose_prompt, PERSONA  # re-exported for backward compat
from sage_poc.prompts.composer import _sanitize_assistant_turn  # re-exported for backward compat
from sage_poc.resilience import resilient_invoke

__all__ = ["compose_prompt", "PERSONA", "freeflow_respond_node", "_sanitize_assistant_turn"]


async def _get_prior_context(state: SageState) -> str:
    """Fetch prior session context for the current user, or return empty string.

    Extracted as a named helper so tests can patch it directly without fighting
    deferred-import mechanics.  Non-fatal: any exception yields empty string.
    """
    user_id = state.get("user_id")
    if not user_id:
        return ""
    try:
        # Deferred imports prevent circular import (server imports sage_poc.graph)
        from server import app  # noqa: PLC0415
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
        from sage_poc.nodes.tools.check_user_history import retrieve_prior_context  # noqa: PLC0415
        pool = app.state._db_pool
        if pool is None:
            return ""
        repo = PostgresMemoryRepository(pool)
        return await retrieve_prior_context(
            user_id, state.get("message_en", ""), repo
        )
    except Exception:
        return ""  # non-fatal — degrade gracefully if pool unavailable


async def _invoke_with_tool_loop(
    llm,
    messages: list[dict],
    tools: list,
    *,
    node: str,
    language: str,
    fallback_llm,
) -> str:
    """Invoke LLM, executing any tool calls until a plain text response is returned.

    When tools is empty, falls back to resilient_invoke (identical to prior behaviour).
    """
    if not tools:
        return await resilient_invoke(
            llm, messages, node=node, language=language, fallback_llm=fallback_llm
        )
    llm_with_tools = llm.bind_tools(tools)
    MAX_ITERATIONS = 5
    for _ in range(MAX_ITERATIONS):
        ai_message = await llm_with_tools.ainvoke(messages)
        if not getattr(ai_message, "tool_calls", None):
            return ai_message.content or ""
        messages = list(messages) + [ai_message]
        for tc in ai_message.tool_calls:
            # find the tool matching tc["name"]
            fn = next((t for t in tools if t.name == tc["name"]), None)
            if fn is not None:
                try:
                    result = await fn.ainvoke(tc["args"])
                except Exception as exc:
                    result = f"error: {exc}"
            else:
                result = "unknown tool"
            from langchain_core.messages import ToolMessage  # noqa: PLC0415
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
    # Safety: exceeded iteration limit — return empty to trigger graceful fallback
    return ""


async def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()
    fallback_llm = get_fallback_responder()

    prior_context = await _get_prior_context(state)

    system_str, user_str, prompt_layers = compose_prompt(state)

    if prior_context:
        system_str += f"\n\n{prior_context}"
        prompt_layers = list(prompt_layers) + ["prior_session_context"]

    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    response = await _invoke_with_tool_loop(
        llm,
        messages,
        [],  # empty tool list — populated by Task 4.3/4.4
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
