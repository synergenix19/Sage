import asyncio
import json
import logging
from sage_poc.state import SageState
from sage_poc.llm import get_responder, get_fallback_responder
from sage_poc.prompts import compose_prompt, PERSONA  # re-exported for backward compat
from sage_poc.prompts.composer import _sanitize_assistant_turn  # re-exported for backward compat
from sage_poc.resilience import resilient_invoke

__all__ = ["compose_prompt", "PERSONA", "freeflow_respond_node", "_sanitize_assistant_turn", "_knowledge_lookup_fired"]

# W3: latency guard on the empty-result regeneration. resilient_invoke's own timeout is 30s
# (LLM_TIMEOUT_SECONDS) — far past the <3s p95 target — so the one fallback attempt after an
# empty primary response is bounded here. On breach we return "" and output_gate substitutes
# the vetted line: a fast vetted reply beats a slow second LLM round-trip.
EMPTY_RETRY_TIMEOUT_SECONDS: float = 2.5

# v7.1 G2 — the warm-tier (T1) posture frame. Injected on a T1 turn (supportive_posture=True):
# validate first, at most one gentle question, offer-not-force. ~40 words, signed.
_SUPPORTIVE_POSTURE_INSTRUCTION = (
    "SUPPORTIVE POSTURE: they voiced distress, not active crisis. Validate what they feel, in "
    "their own words, before anything else. Ask at most one gentle, open question. Do not alarm "
    "or push. You may offer, once and without pressure, that a support line is there if it helps."
)


async def _bounded_empty_retry(llm, messages, *, node: str, language: str, fallback_llm) -> str:
    """One latency-bounded regeneration attempt after an empty primary response.

    Returns the retry text, or "" on timeout so output_gate emits the vetted fallback
    (never blank to the user). Bounded by EMPTY_RETRY_TIMEOUT_SECONDS, not the 30s default.
    """
    try:
        return await asyncio.wait_for(
            resilient_invoke(llm, messages, node=node, language=language, fallback_llm=fallback_llm),
            timeout=EMPTY_RETRY_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logging.getLogger(__name__).warning(
            "[freeflow] empty-result retry exceeded %.1fs budget; deferring to vetted fallback",
            EMPTY_RETRY_TIMEOUT_SECONDS,
        )
        return ""


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


def _knowledge_lookup_trace(messages: list) -> dict:
    """Extract query_raw/query_searched from the knowledge_lookup tool RESULT.

    The tool loop records both the AIMessage requests (which carry the tool
    name in .tool_calls) and the ToolMessage results (which carry the JSON
    content, keyed by tool_call_id). We map the knowledge_lookup call ids to
    their result message and parse the last one.
    """
    kl_call_ids = set()
    for msg in messages or []:
        for tc in (getattr(msg, "tool_calls", None) or []):
            if tc.get("name") == "knowledge_lookup":
                cid = tc.get("id")
                if cid:
                    kl_call_ids.add(cid)
    if not kl_call_ids:
        return {}
    for msg in reversed(messages or []):
        cid = getattr(msg, "tool_call_id", None)
        if cid in kl_call_ids:
            try:
                data = json.loads(getattr(msg, "content", "") or "")
            except (TypeError, ValueError):
                return {}
            return {
                "knowledge_query_raw": data.get("query_raw", ""),
                "knowledge_query_searched": data.get("query_searched", ""),
                "knowledge_top_similarity": data.get("top_similarity"),
            }
    return {}


def _accumulate_usage(acc: dict, msg) -> None:
    """Add an AI message's token usage into `acc` ({input,output,total}). Robust to a
    missing/non-dict usage_metadata (e.g. mocks or providers that omit it) — then it's a no-op,
    so token_usage stays {} rather than crashing (matches the missing-usage contract)."""
    um = getattr(msg, "usage_metadata", None)
    if not isinstance(um, dict):
        return
    acc["input"] = acc.get("input", 0) + int(um.get("input_tokens") or 0)
    acc["output"] = acc.get("output", 0) + int(um.get("output_tokens") or 0)
    acc["total"] = acc.get("total", 0) + int(um.get("total_tokens") or 0)


async def _invoke_with_tool_loop(
    llm,
    messages: list[dict],
    tools: list,
    *,
    node: str,
    language: str,
    fallback_llm,
    _tool_messages: list | None = None,
    _usage: dict | None = None,
) -> str:
    """Invoke LLM, executing any tool calls until a plain text response is returned.

    When tools is empty, falls back to resilient_invoke (identical to prior behaviour).
    If _tool_messages is provided (a mutable list), all AI messages that contain tool
    calls will be appended to it so callers can inspect which tools fired, and the
    corresponding ToolMessage tool RESULTS are also appended so callers can inspect
    what the tools returned (e.g. to correlate a tool_call_id to its result content).
    If _usage is provided, each generation's token usage is accumulated into it (the
    string-fallback path below carries no usage, so token_usage stays {} on that path).
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
        try:
            ai_message = await llm_with_tools.ainvoke(messages)
        except Exception as exc:
            import logging  # noqa: PLC0415
            logging.getLogger(__name__).warning(
                "[freeflow] tool-loop ainvoke failed (%s); returning empty to trigger fallback", exc
            )
            return ""  # caller substitutes a warm reply via resilient_invoke; never blank to user
        if _usage is not None:
            _accumulate_usage(_usage, ai_message)  # per generation (tool-loop calls accumulate)
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
            tool_message = ToolMessage(content=str(result), tool_call_id=tc["id"])
            messages.append(tool_message)
            if _tool_messages is not None:
                _tool_messages.append(tool_message)
    # Safety: exceeded iteration limit — return empty to trigger graceful fallback
    return ""


def _build_llm_tools(state: SageState, user_id, session_id) -> list:
    """Bind freeflow tools. knowledge_lookup is available EXCEPT when knowledge_retrieve
    (Node 6) already retrieved for THIS turn — binding it then lets the model re-retrieve, a
    redundant RAG + extra LLM round-trip (RC-3, measured on info_request).

    The gate is the PER-TURN path ("knowledge_retrieve" in state["path"], which _build_state
    resets each turn) — deliberately NOT the intent. A mid-conversation factual question that
    did not route through Node 6 (e.g. a fact asked inside a skill or general_chat turn) still
    binds knowledge_lookup, so the model can retrieve evidence instead of answering from
    parametric memory (v7 §6.5.2). Narrowing it to intent would close that evidence-grounding
    door and the failure mode would be hallucination (the <5% floor), not latency.
    """
    llm_tools: list = []
    node6_already_retrieved = "knowledge_retrieve" in (state.get("path") or [])
    if not node6_already_retrieved:
        try:
            from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool  # noqa: PLC0415
            llm_tools.append(make_knowledge_lookup_tool(language=state.get("detected_language", "en")))
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
    return llm_tools


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
    else:
        # Absent-side A4 fix: empty retrieval carries no signal, so on a recall turn the model
        # fabricates into the silence. Inject an explicit "no record found" anchor (mirrors the
        # knowledge path). Fires only on self_reference + genuinely-empty grounding; see composer.
        from sage_poc.prompts.composer import memory_absent_sentinel  # noqa: PLC0415
        _sentinel = memory_absent_sentinel(state, prior_context_present=False)
        if _sentinel:
            system_str = system_str + "\n\n" + _sentinel
            prompt_layers = list(prompt_layers) + ["memory_absent_sentinel"]

    # v7.1 T1 (warm concern) posture — G2. Set only when supportive_posture is True, which
    # safety_check sets only for a T1 turn under the flag; flag OFF => never injected (byte-identical).
    if state.get("supportive_posture"):
        system_str = system_str + "\n\n" + _SUPPORTIVE_POSTURE_INSTRUCTION
        prompt_layers = list(prompt_layers) + ["supportive_posture"]

    messages = [
        {"role": "system", "content": system_str},
        {"role": "user", "content": user_str},
    ]

    llm_tools = _build_llm_tools(state, user_id, session_id)

    tool_ai_messages: list = []
    token_usage: dict = {}
    response = await _invoke_with_tool_loop(
        llm,
        messages,
        llm_tools,
        node="freeflow_respond",
        language=state.get("detected_language", "en"),
        fallback_llm=fallback_llm,
        _tool_messages=tool_ai_messages,
        _usage=token_usage,
    )

    if not response:
        # Tool loop exhausted MAX_ITERATIONS without producing text — one latency-bounded
        # regeneration on the original 2-message prompt (W3). If it breaches the budget or
        # is itself empty, output_gate substitutes the vetted line — never blank to the user.
        response = await _bounded_empty_retry(
            llm, messages,
            node="freeflow_respond",
            language=state.get("detected_language", "en"),
            fallback_llm=fallback_llm,
        )

    # Determine knowledge_source: if knowledge_lookup tool was invoked, override with "tool_lookup"
    knowledge_source_update = {}
    if _knowledge_lookup_fired(tool_ai_messages):
        knowledge_source_update = {"knowledge_source": "tool_lookup"}
        knowledge_source_update.update(_knowledge_lookup_trace(tool_ai_messages))

    return {
        "response_en":              response,
        "prompt_layers":            prompt_layers,
        "token_usage":              token_usage,
        "path":                     (state.get("path") or []) + ["freeflow_respond"],
        "stale_skill_id":           None,   # consumed by re-entry prompt; clear so it doesn't re-fire
        "banned_opener_correction": None,
        **knowledge_source_update,
    }
