"""Tests for the LLM resilience layer (Doc 5)."""
from __future__ import annotations

import asyncio
import json
import pathlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_llm(responses=None, side_effects=None,
              model_name="test/model", base_url="https://test.api"):
    """Build a mock ChatOpenAI. responses → list of str, side_effects → list of exceptions."""
    llm = MagicMock()
    llm.model_name = model_name
    llm.openai_api_base = base_url
    if side_effects:
        llm.ainvoke = AsyncMock(side_effect=side_effects)
    elif responses:
        llm.ainvoke = AsyncMock(
            side_effect=[MagicMock(content=r) for r in responses]
        )
    else:
        llm.ainvoke = AsyncMock(return_value=MagicMock(content="ok"))
    return llm


async def _collect(gen) -> str:
    """Collect all chunks from an async generator."""
    return "".join([chunk async for chunk in gen])


# ── Fallback JSON ─────────────────────────────────────────────────────────────

def test_fallbacks_json_valid():
    path = (
        pathlib.Path(__file__).parent.parent
        / "src/sage_poc/resilience/fallbacks.json"
    )
    assert path.exists(), "fallbacks.json must exist"
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    nodes_langs = {(e["node"], e["language"]) for e in data}
    required = {
        ("freeflow_respond", "en"),
        ("freeflow_respond", "ar"),
        ("low_confidence_respond", "en"),
        ("low_confidence_respond", "ar"),
        ("default", "en"),
        ("default", "ar"),
    }
    missing = required - nodes_langs
    assert not missing, f"Missing fallback entries: {missing}"


def test_fallback_no_em_dashes():
    path = (
        pathlib.Path(__file__).parent.parent
        / "src/sage_poc/resilience/fallbacks.json"
    )
    data = json.loads(path.read_text())
    for entry in data:
        assert "—" not in entry["response"], (
            f"Em dash in fallback node={entry['node']} lang={entry['language']}"
        )
