from langchain_openai import ChatOpenAI
from sage_poc.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    CLASSIFIER_MODEL,
    RESPONDER_MODEL,
    TRANSLATOR_MODEL,
    FALLBACK_RESPONDER_MODEL,
    FALLBACK_CLASSIFIER_MODEL,
)

_HEADERS = {"HTTP-Referer": "https://sage.ai", "X-Title": "SageAI POC"}

_classifier: ChatOpenAI | None = None
_responder: ChatOpenAI | None = None
_translator: ChatOpenAI | None = None
_fallback_responder: ChatOpenAI | None = None
_fallback_classifier: ChatOpenAI | None = None


def get_classifier() -> ChatOpenAI:
    """Fast, low-temperature model for intent classification and safety routing."""
    global _classifier
    if _classifier is None:
        _classifier = ChatOpenAI(
            model=CLASSIFIER_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=0,
            max_tokens=512,
            default_headers=_HEADERS,
        )
    return _classifier


def get_responder() -> ChatOpenAI:
    """Higher-quality model for therapeutic response generation."""
    global _responder
    if _responder is None:
        _responder = ChatOpenAI(
            model=RESPONDER_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=0.7,
            max_tokens=1024,
            default_headers=_HEADERS,
        )
    return _responder


def get_translator() -> ChatOpenAI:
    """Fast model for Arabic ↔ English translation."""
    global _translator
    if _translator is None:
        _translator = ChatOpenAI(
            model=TRANSLATOR_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=0,
            max_tokens=1024,
            default_headers=_HEADERS,
        )
    return _translator


def get_fallback_responder() -> ChatOpenAI:
    """Fallback model for response generation when primary is unavailable."""
    global _fallback_responder
    if _fallback_responder is None:
        _fallback_responder = ChatOpenAI(
            model=FALLBACK_RESPONDER_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=0.7,
            max_tokens=1024,
            default_headers=_HEADERS,
        )
    return _fallback_responder


def get_fallback_classifier() -> ChatOpenAI:
    """Fallback model for intent classification when primary is unavailable."""
    global _fallback_classifier
    if _fallback_classifier is None:
        _fallback_classifier = ChatOpenAI(
            model=FALLBACK_CLASSIFIER_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=0,
            max_tokens=512,
            default_headers=_HEADERS,
        )
    return _fallback_classifier


def reset_singletons() -> None:
    """Reset all cached LLM instances. Call in test teardown to prevent mock leakage."""
    global _classifier, _responder, _translator, _fallback_responder, _fallback_classifier
    _classifier = None
    _responder = None
    _translator = None
    _fallback_responder = None
    _fallback_classifier = None
