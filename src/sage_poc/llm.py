from langchain_openai import ChatOpenAI
from sage_poc.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    CLASSIFIER_MODEL,
    RESPONDER_MODEL,
    TRANSLATOR_MODEL,
)

_HEADERS = {"HTTP-Referer": "https://sage.ai", "X-Title": "SageAI POC"}


def get_classifier() -> ChatOpenAI:
    """Fast, low-temperature model for intent classification and safety routing."""
    return ChatOpenAI(
        model=CLASSIFIER_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0,
        max_tokens=512,
        default_headers=_HEADERS,
    )


def get_responder() -> ChatOpenAI:
    """Higher-quality model for therapeutic response generation."""
    return ChatOpenAI(
        model=RESPONDER_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0.7,
        max_tokens=1024,
        default_headers=_HEADERS,
    )


def get_translator() -> ChatOpenAI:
    """Fast model for Arabic ↔ English translation."""
    return ChatOpenAI(
        model=TRANSLATOR_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0,
        max_tokens=1024,
        default_headers=_HEADERS,
    )
