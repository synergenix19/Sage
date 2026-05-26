# tests/test_post_crisis_classifier.py
import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.post_crisis_classifier import evaluate_s7, _VALID_LABELS


async def test_recovery_keyword_returns_recovering():
    label, method = await evaluate_s7("thank you, I'm feeling better now")
    assert label == "RECOVERING"
    assert method == "keyword"


async def test_still_distressed_keyword_returns_still_distressed():
    # S7's STILL_DISTRESSED tier covers the gap between "I'm fine" and explicit harm language.
    # Explicit crisis phrases ("want to die", etc.) are excluded — S1–S6 catch those before S7 runs.
    label, method = await evaluate_s7("I'm still feeling down, nothing has changed")
    assert label == "STILL_DISTRESSED"
    assert method == "keyword"


async def test_no_keyword_falls_back_to_llm():
    with patch(
        "sage_poc.nodes.post_crisis_classifier.resilient_invoke",
        new=AsyncMock(return_value="UNCLEAR"),
    ) as mock_ri:
        label, method = await evaluate_s7("I don't know")
        assert label == "UNCLEAR"
        assert method == "llm"
        # resilient_invoke was called with only the current message — no conversation history
        call_args = mock_ri.call_args
        messages = call_args[0][1]  # positional arg: (llm, messages, ...)
        assert len(messages) == 2  # system + user only
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "I don't know"


async def test_llm_invalid_label_falls_back_to_unclear():
    with patch(
        "sage_poc.nodes.post_crisis_classifier.resilient_invoke",
        new=AsyncMock(return_value="CONFUSED_RESPONSE"),
    ):
        label, method = await evaluate_s7("something unknown")
        assert label == "UNCLEAR"
        assert method == "llm"


def test_all_valid_labels_defined():
    assert _VALID_LABELS == {"RECOVERING", "STILL_DISTRESSED", "UNCLEAR", "NEW_CRISIS"}


async def test_still_distressed_keyword_checked_before_recovery():
    """A message containing both a non-crisis distress signal and a recovery phrase: STILL_DISTRESSED wins."""
    label, method = await evaluate_s7("nothing has changed but thank you for asking")
    assert label == "STILL_DISTRESSED"
    assert method == "keyword"


def test_crisis_phrase_not_in_still_distressed_keywords():
    """Explicit crisis phrases must NOT be in _STILL_DISTRESSED_KEYWORDS — S1–S6 catch those first."""
    from sage_poc.nodes.post_crisis_classifier import _STILL_DISTRESSED_KEYWORDS
    assert "want to die" not in _STILL_DISTRESSED_KEYWORDS
    assert "going to end it" not in _STILL_DISTRESSED_KEYWORDS
    assert "want to hurt myself" not in _STILL_DISTRESSED_KEYWORDS


async def test_evaluate_s7_uses_resilient_invoke_on_llm_path():
    """Confirm evaluate_s7 calls resilient_invoke when keywords don't match."""
    with patch(
        "sage_poc.nodes.post_crisis_classifier.resilient_invoke",
        new=AsyncMock(return_value="UNCLEAR"),
    ) as mock_ri:
        label, method = await evaluate_s7("something ambiguous")
        assert label == "UNCLEAR"
        assert method == "llm"
        mock_ri.assert_awaited_once()
