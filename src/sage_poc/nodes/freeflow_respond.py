from sage_poc.state import SageState
from sage_poc.llm import get_responder, get_fallback_responder
from sage_poc.prompts import compose_prompt, PERSONA  # re-exported for backward compat
from sage_poc.prompts.composer import _sanitize_assistant_turn  # re-exported for backward compat
from sage_poc.resilience import resilient_invoke

__all__ = ["compose_prompt", "PERSONA", "freeflow_respond_node", "_sanitize_assistant_turn", "_knowledge_lookup_fired"]


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


def _knowledge_lookup_fired(messages: list) -> bool:
    """Check if knowledge_lookup was invoked in the completed tool-call message list."""
    for msg in messages:
        if hasattr(msg, "tool_calls"):
            for tc in (msg.tool_calls or []):
                if tc.get("name") == "knowledge_lookup":
                    return True
    return False


async def _invoke_with_tool_loop(
    llm,
    messages: list[dict],
    tools: list,
    *,
    node: str,
    language: str,
    fallback_llm,
    _tool_messages: list | None = None,
) -> str:
    """Invoke LLM, executing any tool calls until a plain text response is returned.

    When tools is empty, falls back to resilient_invoke (identical to prior behaviour).
    If _tool_messages is provided (a mutable list), all AI messages that contain tool
    calls will be appended to it so callers can inspect which tools fired.
    """
    if not tools:
        return await resilient_invoke(
            llm, messages, node=node, language=language, fallback_llm=fallback_llm
        )
    # Deviation from v7 §5.6.2: tools are bound per-invocation, not at graph construction,
    # because user_id and session_id are injected via closure and unavailable at build time.
    # bind_tools() attaches schemas at the model API level, not in prompt text, so this
    # does not consume prompt tokens — the intent of §5.6.2 is preserved.
    llm_with_tools = llm.bind_tools(tools)
    MAX_ITERATIONS = 5
    for _ in range(MAX_ITERATIONS):
        ai_message = await llm_with_tools.ainvoke(messages)
        if not getattr(ai_message, "tool_calls", None):
            return ai_message.content or ""
        messages = list(messages) + [ai_message]
        if _tool_messages is not None:
            _tool_messages.append(ai_message)
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
    user_id = state.get("user_id")
    session_id = state.get("session_id")

    prior_context = await _get_prior_context(state)

    system_str, user_str, prompt_layers = compose_prompt(state)

    if prior_context:
        system_str = system_str + "\n\nPRIOR SESSION CONTEXT (share naturally, not verbatim):\n" + prior_context
        prompt_layers = list(prompt_layers) + ["prior_session_context"]

    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    # --- LLM tool binding: knowledge_lookup + flag_for_review + record_observation ---
    llm_tools = []
    # knowledge_lookup is always available — no user identity required (v7 §6.5.2)
    try:
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup  # noqa: PLC0415
        llm_tools.append(knowledge_lookup)
    except ImportError:
        pass
    if user_id and session_id:
        try:
            from server import app  # noqa: PLC0415
            pool = getattr(app.state, "_db_pool", None)
            if pool:
                from sage_poc.nodes.tools.flag_for_review import make_flag_tool  # noqa: PLC0415
                from sage_poc.nodes.tools.record_observation import make_record_tool  # noqa: PLC0415
                llm_tools.extend([
                    make_flag_tool(user_id=user_id, session_id=session_id),
                    make_record_tool(user_id=user_id, pool=pool, session_id=session_id),
                ])
        except ImportError:
            pass
        except Exception as exc:
            import logging; logging.getLogger(__name__).warning("[freeflow] tool setup failed: %s", exc)

    tool_ai_messages: list = []
    response = await _invoke_with_tool_loop(
        llm,
        messages,
        llm_tools,
        node="freeflow_respond",
        language=state.get("detected_language", "en"),
        fallback_llm=fallback_llm,
        _tool_messages=tool_ai_messages,
    )

    if not response:
        # Tool loop exhausted MAX_ITERATIONS without producing text — fall back to
        # resilient_invoke on the original 2-message prompt so the user always gets
        # a response. A blank response to a user in distress is a clinical incident.
        response = await resilient_invoke(
            llm, messages,
            node="freeflow_respond",
            language=state.get("detected_language", "en"),
            fallback_llm=fallback_llm,
        )

    # Determine knowledge_source: if knowledge_lookup tool was invoked, override with "tool_lookup"
    knowledge_source_update = {}
    if _knowledge_lookup_fired(tool_ai_messages):
        knowledge_source_update = {"knowledge_source": "tool_lookup"}

    return {
        "response_en":    response,
        "prompt_layers":  prompt_layers,
        "token_usage":    {},
        "path":           (state.get("path") or []) + ["freeflow_respond"],
        "stale_skill_id": None,   # consumed by re-entry prompt; clear so it doesn't re-fire
        **knowledge_source_update,
    }
