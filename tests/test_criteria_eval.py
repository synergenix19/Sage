"""Tests for the LLM-based completion criteria evaluator.

All LLM calls are mocked — no live inference.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_llm_yes_returns_true():
    """LLM responding 'yes' must return True."""
    from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

    with patch("sage_poc.nodes.criteria_eval._call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "yes"
        result = await evaluate_completion_criteria(
            message_en="I feel safe right now",
            criterion="User has confirmed current safety status",
        )
    assert result is True


@pytest.mark.asyncio
async def test_llm_no_returns_false():
    """LLM responding 'no' must return False."""
    from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

    with patch("sage_poc.nodes.criteria_eval._call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "no"
        result = await evaluate_completion_criteria(
            message_en="whatever I'm fine",
            criterion="User has confirmed current safety status",
        )
    assert result is False


@pytest.mark.asyncio
async def test_llm_exception_falls_back_to_heuristic_multi_word():
    """LLM exception must fall back to word-count heuristic; multi-word message returns True."""
    from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

    with patch("sage_poc.nodes.criteria_eval._call_llm", side_effect=RuntimeError("timeout")):
        result = await evaluate_completion_criteria(
            message_en="I feel better now",
            criterion="User has confirmed current safety status",
        )
    assert result is True  # 4 words > 1


@pytest.mark.asyncio
async def test_llm_exception_falls_back_to_heuristic_single_word():
    """LLM exception must fall back to word-count heuristic; single-word message returns False."""
    from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

    with patch("sage_poc.nodes.criteria_eval._call_llm", side_effect=RuntimeError("timeout")):
        result = await evaluate_completion_criteria(
            message_en="ok",
            criterion="User has confirmed current safety status",
        )
    assert result is False  # 1 word, not > 1


@pytest.mark.asyncio
async def test_empty_criterion_uses_heuristic():
    """Empty criterion must skip LLM and use word-count heuristic."""
    from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

    with patch("sage_poc.nodes.criteria_eval._call_llm", new_callable=AsyncMock) as mock_llm:
        result = await evaluate_completion_criteria(
            message_en="hello",
            criterion="",
        )
    mock_llm.assert_not_called()
    assert result is False  # 1 word


@pytest.mark.asyncio
async def test_empty_message_returns_true():
    """Empty message with non-empty criterion returns True (skip check — not blocking)."""
    from sage_poc.nodes.criteria_eval import evaluate_completion_criteria

    result = await evaluate_completion_criteria(message_en="", criterion="some criterion")
    assert result is True
