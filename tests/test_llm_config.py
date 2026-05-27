"""Guard: no Claude model in any default. Claude routes data outside UAE (PDPL violation)."""
from sage_poc.config import (
    RESPONDER_MODEL, CLASSIFIER_MODEL, TRANSLATOR_MODEL,
    FALLBACK_RESPONDER_MODEL, FALLBACK_CLASSIFIER_MODEL,
)


def test_no_claude_in_any_default():
    for model in [RESPONDER_MODEL, CLASSIFIER_MODEL, TRANSLATOR_MODEL,
                  FALLBACK_RESPONDER_MODEL, FALLBACK_CLASSIFIER_MODEL]:
        assert "anthropic" not in model and "claude" not in model.lower(), (
            f"Claude found in model default {model!r} — violates UAE data residency (PDPL)"
        )


def test_responder_is_gpt4o():
    assert RESPONDER_MODEL == "openai/gpt-4o"
