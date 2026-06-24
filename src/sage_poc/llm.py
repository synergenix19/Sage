from functools import lru_cache

import httpx
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
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE,
)

_HEADERS = {"HTTP-Referer": "https://sage.ai", "X-Title": "SageAI POC"}


def _http_limits() -> httpx.Limits:
    return httpx.Limits(
        max_connections=HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=HTTP_MAX_KEEPALIVE,
        keepalive_expiry=300,
    )


# Shared async HTTP client for all LLM calls.
# keepalive_expiry=300 keeps the TCP connection to OpenRouter alive for 5 minutes
# of inactivity. The httpx default (5s) causes cold-start latency (4.7s TCP/TLS
# re-establishment) after any idle gap — including gaps between demo sessions at
# a Gitex booth. 300s covers typical between-demo idle periods.
# All ChatOpenAI instances share this client so the warmup call in server.py
# _warmup_task() warms the same pool that handles real user requests.
_ASYNC_HTTP_CLIENT = httpx.AsyncClient(limits=_http_limits())

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
        http_async_client=_ASYNC_HTTP_CLIENT,
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
