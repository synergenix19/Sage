# tests/test_post_crisis_classifier.py
import pytest
from unittest.mock import MagicMock
from sage_poc.nodes.post_crisis_classifier import evaluate_s7, _VALID_LABELS


def test_recovery_keyword_returns_recovering():
    label, method = evaluate_s7("thank you, I'm feeling better now")
    assert label == "RECOVERING"
    assert method == "keyword"


def test_still_distressed_keyword_returns_still_distressed():
    # S7's STILL_DISTRESSED tier covers the gap between "I'm fine" and explicit harm language.
    # Explicit crisis phrases ("want to die", etc.) are excluded — S1–S6 catch those before S7 runs.
    label, method = evaluate_s7("I'm still feeling down, nothing has changed")
    assert label == "STILL_DISTRESSED"
    assert method == "keyword"


def test_no_keyword_falls_back_to_llm():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="UNCLEAR")
    label, method = evaluate_s7("I don't know", llm=mock_llm)
    assert label == "UNCLEAR"
    assert method == "llm"
    # LLM was called with only the current message — no conversation history
    call_args = mock_llm.invoke.call_args[0][0]
    assert len(call_args) == 2  # system + user only
    assert call_args[1]["role"] == "user"
    assert call_args[1]["content"] == "I don't know"


def test_llm_invalid_label_falls_back_to_unclear():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="CONFUSED_RESPONSE")
    label, method = evaluate_s7("something unknown", llm=mock_llm)
    assert label == "UNCLEAR"
    assert method == "llm"


def test_all_valid_labels_defined():
    assert _VALID_LABELS == {"RECOVERING", "STILL_DISTRESSED", "UNCLEAR", "NEW_CRISIS"}


def test_still_distressed_keyword_checked_before_recovery():
    """A message containing both a non-crisis distress signal and a recovery phrase: STILL_DISTRESSED wins."""
    label, method = evaluate_s7("nothing has changed but thank you for asking")
    assert label == "STILL_DISTRESSED"
    assert method == "keyword"


def test_crisis_phrase_not_in_still_distressed_keywords():
    """Explicit crisis phrases must NOT be in _STILL_DISTRESSED_KEYWORDS — S1–S6 catch those first."""
    from sage_poc.nodes.post_crisis_classifier import _STILL_DISTRESSED_KEYWORDS
    assert "want to die" not in _STILL_DISTRESSED_KEYWORDS
    assert "going to end it" not in _STILL_DISTRESSED_KEYWORDS
    assert "want to hurt myself" not in _STILL_DISTRESSED_KEYWORDS
