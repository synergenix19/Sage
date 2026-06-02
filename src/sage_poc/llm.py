from functools import lru_cache

from langchain_openai import ChatOpenAI

from sage_poc.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    CLASSIFIER_MODEL,
    RESPONDER_MODEL,
    TRANSLATOR_MODEL,
    FALLBACK_RESPONDER_MODEL,
    FALLBACK_CLASSIFIER_MODEL,
    RESISTANCE_MODEL,
)

_HEADERS = {"HTTP-Referer": "https://sage.ai", "X-Title": "SageAI POC"}

_LLM_CONFIGS: dict[str, tuple[str, float, int]] = {
    "classifier":          (CLASSIFIER_MODEL,          0,   512),
    "responder":           (RESPONDER_MODEL,            0.7, 1024),
    "translator":          (TRANSLATOR_MODEL,           0,   1024),
    "fallback_responder":  (FALLBACK_RESPONDER_MODEL,   0.7, 1024),
    "fallback_classifier": (FALLBACK_CLASSIFIER_MODEL,  0,   512),
    "resistance":          (RESISTANCE_MODEL,           0,   16),
}


@lru_cache(maxsize=None)
def _make_llm(model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
        default_headers=_HEADERS,
    )


def get_classifier() -> ChatOpenAI:
    """Fast, low-temperature model for intent classification and safety routing."""
    model, temp, max_tokens = _LLM_CONFIGS["classifier"]
    return _make_llm(model, temp, max_tokens)


def get_responder() -> ChatOpenAI:
    """Higher-quality model for therapeutic response generation."""
    model, temp, max_tokens = _LLM_CONFIGS["responder"]
    return _make_llm(model, temp, max_tokens)


def get_translator() -> ChatOpenAI:
    """Fast model for Arabic ↔ English translation."""
    model, temp, max_tokens = _LLM_CONFIGS["translator"]
    return _make_llm(model, temp, max_tokens)


def get_fallback_responder() -> ChatOpenAI:
    """Fallback model for response generation when primary is unavailable."""
    model, temp, max_tokens = _LLM_CONFIGS["fallback_responder"]
    return _make_llm(model, temp, max_tokens)


def get_fallback_classifier() -> ChatOpenAI:
    """Fallback model for intent classification when primary is unavailable."""
    model, temp, max_tokens = _LLM_CONFIGS["fallback_classifier"]
    return _make_llm(model, temp, max_tokens)


def get_resistance_model() -> ChatOpenAI:
    """Model for clinical resistance scoring.

    Configure SAGE_RESISTANCE_MODEL to a local sovereign endpoint (Falcon-3B) before
    production — resistance scores feed the therapeutic profile and step policy. Defaults
    to SAGE_CLASSIFIER_MODEL as interim fallback.
    """
    model, temp, max_tokens = _LLM_CONFIGS["resistance"]
    return _make_llm(model, temp, max_tokens)


def reset_singletons() -> None:
    """Reset all cached LLM instances. Call in test teardown to prevent mock leakage."""
    _make_llm.cache_clear()
