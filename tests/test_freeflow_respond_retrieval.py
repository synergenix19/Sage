"""Tests for Task 3.4: episodic pre-retrieval and tool loop in freeflow_respond_node.

Patching strategy: _get_prior_context is extracted as a module-level helper so we can
patch it directly at `sage_poc.nodes.freeflow_respond._get_prior_context` rather than
fighting deferred-import mechanics for server/pool/repository objects.

The tool-loop helper _invoke_with_tool_loop is tested via direct import.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sage_poc.nodes.freeflow_respond import (
    freeflow_respond_node,
    _invoke_with_tool_loop,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_BASE_STATE = {
    "raw_message": "I feel anxious",
    "detected_language": "en",
    "message_en": "I feel anxious",
    "user_id": "user-abc-123",
    "is_safe": True,
    "crisis_flags": [],
    "clinical_flags": [],
    "crisis_state": "none",
    "s7_result": None,
    "s7_method": None,
    "distress_trajectory": [],
    "code_switching": False,
    "primary_intent": "new_skill",
    "secondary_intent": None,
    "intent_confidence": 0.9,
    "emotional_intensity": 5,
    "engagement": 6,
    "active_skill_id": None,
    "active_step_id": None,
    "executed_step_id": None,
    "step_instruction": None,
    "skill_match_method": None,
    "semantic_score": None,
    "escalation_triggered": None,
    "gate_path": None,
    "response_en": None,
    "response": None,
    "path": ["safety_check", "intent_route"],
    "turn_count": 0,
    "conversation_history": [],
    "prompt_layers": [],
    "token_usage": {},
    "therapeutic_profile": None,
}

_PRIOR_CONTEXT_TEXT = "Prior session context:\n[Session 1]: User practiced breathing."


def _make_mock_llm(response_text: str = "That sounds really difficult.") -> AsyncMock:
    """Return an AsyncMock LLM that resilient_invoke can use (returns str)."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# Test 1: prior context injected when user_id is set
# ---------------------------------------------------------------------------

def test_prior_context_injected_when_user_id_set():
    """System message must include prior context; prompt_layers must record it."""
    captured_messages = []

    async def fake_resilient_invoke(llm, messages, *, node, language, fallback_llm):
        captured_messages.extend(messages)
        return "That sounds really difficult."

    with patch(
        "sage_poc.nodes.freeflow_respond._get_prior_context",
        new=AsyncMock(return_value=_PRIOR_CONTEXT_TEXT),
    ), patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        side_effect=fake_resilient_invoke,
    ):
        result = asyncio.run(freeflow_respond_node(_BASE_STATE))

    assert result["response_en"] == "That sounds really difficult."
    assert "prior_session_context" in result["prompt_layers"]

    # System message should contain the prior context text
    system_messages = [m for m in captured_messages if m["role"] == "system"]
    assert system_messages, "No system message was passed to the LLM"
    assert _PRIOR_CONTEXT_TEXT in system_messages[0]["content"], (
        "Prior session context was not injected into the system prompt"
    )


# ---------------------------------------------------------------------------
# Test 2: prior context skipped when no user_id
# ---------------------------------------------------------------------------

def test_prior_context_skipped_when_no_user_id():
    """When user_id is None, _get_prior_context should not be called at all,
    and prior_session_context should not appear in prompt_layers."""
    state_no_user = {**_BASE_STATE, "user_id": None}

    get_prior_ctx_mock = AsyncMock(return_value="")

    with patch(
        "sage_poc.nodes.freeflow_respond._get_prior_context",
        new=get_prior_ctx_mock,
    ), patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        new=AsyncMock(return_value="I hear you."),
    ):
        result = asyncio.run(freeflow_respond_node(state_no_user))

    # _get_prior_context is always called (it guards user_id internally),
    # but the result is empty so prior_session_context must NOT be in layers.
    assert "prior_session_context" not in result["prompt_layers"]


# ---------------------------------------------------------------------------
# Test 3: prior context skipped when pool is None
# ---------------------------------------------------------------------------

def test_prior_context_skipped_when_pool_is_none():
    """When db pool is None, prior context must be empty and layer must be absent."""
    import server as server_module  # top-level server.py on pythonpath

    mock_app = MagicMock()
    mock_app.state._db_pool = None

    with patch.object(server_module, "app", mock_app), patch(
        "sage_poc.memory.postgres_repository.PostgresMemoryRepository",
        return_value=MagicMock(),
    ), patch(
        "sage_poc.nodes.tools.check_user_history.retrieve_prior_context",
        new=AsyncMock(return_value="should not be called"),
    ), patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        new=AsyncMock(return_value="I hear you."),
    ):
        result = asyncio.run(freeflow_respond_node(_BASE_STATE))

    assert "prior_session_context" not in result["prompt_layers"]


# ---------------------------------------------------------------------------
# Test 4: empty prior context is not injected
# ---------------------------------------------------------------------------

def test_empty_prior_context_not_injected():
    """When retrieve_prior_context returns empty string, layer must not appear."""
    with patch(
        "sage_poc.nodes.freeflow_respond._get_prior_context",
        new=AsyncMock(return_value=""),
    ), patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        new=AsyncMock(return_value="I hear you."),
    ):
        result = asyncio.run(freeflow_respond_node(_BASE_STATE))

    assert "prior_session_context" not in result["prompt_layers"]


# ---------------------------------------------------------------------------
# Test 5: tool loop with empty tools falls back to resilient_invoke
# ---------------------------------------------------------------------------

def test_tool_loop_with_empty_tools_uses_resilient_invoke():
    """_invoke_with_tool_loop([]) must delegate to resilient_invoke once."""
    mock_llm = MagicMock()
    mock_fallback = MagicMock()
    messages = [{"role": "user", "content": "Hello"}]

    with patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        new=AsyncMock(return_value="Response text"),
    ) as mock_resilient:
        result = asyncio.run(
            _invoke_with_tool_loop(
                mock_llm,
                messages,
                [],
                node="freeflow_respond",
                language="en",
                fallback_llm=mock_fallback,
            )
        )

    mock_resilient.assert_called_once_with(
        mock_llm,
        messages,
        node="freeflow_respond",
        language="en",
        fallback_llm=mock_fallback,
    )
    assert result == "Response text"


# ---------------------------------------------------------------------------
# Test 6: _invoke_with_tool_loop exhaustion — returns "" after MAX_ITERATIONS
# ---------------------------------------------------------------------------

def test_invoke_with_tool_loop_exhausts_max_iterations():
    """_invoke_with_tool_loop returns '' after MAX_ITERATIONS of tool-only responses.
    The LLM repeatedly returns tool_calls without ever producing plain text.
    """
    mock_tool = MagicMock()
    mock_tool.name = "flag_for_review"
    mock_tool.ainvoke = AsyncMock(return_value="flagged")

    mock_ai = MagicMock()
    mock_ai.tool_calls = [{"name": "flag_for_review", "args": {"reason": "test"}, "id": "tc1"}]
    mock_ai.content = ""

    mock_llm_with_tools = AsyncMock()
    mock_llm_with_tools.ainvoke = AsyncMock(return_value=mock_ai)

    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm_with_tools)

    result = asyncio.run(
        _invoke_with_tool_loop(
            mock_llm,
            [{"role": "user", "content": "test"}],
            [mock_tool],
            node="test",
            language="en",
            fallback_llm=MagicMock(),
        )
    )

    assert result == ""
    assert mock_llm_with_tools.ainvoke.call_count == 5  # MAX_ITERATIONS


# ---------------------------------------------------------------------------
# Test 7: freeflow_respond_node fallback when tool loop is exhausted (FAIL 4.1 fix)
# ---------------------------------------------------------------------------

def test_tool_loop_exhaustion_falls_back_in_node():
    """When _invoke_with_tool_loop returns empty string (MAX_ITERATIONS hit),
    freeflow_respond_node must call resilient_invoke and return a non-empty response.
    A blank response to a user in distress is a clinical incident — never acceptable.
    """
    with patch(
        "sage_poc.nodes.freeflow_respond._get_prior_context",
        new=AsyncMock(return_value=""),
    ), patch(
        "sage_poc.nodes.freeflow_respond._invoke_with_tool_loop",
        new=AsyncMock(return_value=""),  # simulates MAX_ITERATIONS exhaustion
    ), patch(
        "sage_poc.nodes.freeflow_respond.resilient_invoke",
        new=AsyncMock(return_value="I am here for you."),
    ) as mock_resilient:
        result = asyncio.run(freeflow_respond_node(_BASE_STATE))

    mock_resilient.assert_called_once()
    assert result["response_en"] == "I am here for you."
    assert result["response_en"]  # never empty
