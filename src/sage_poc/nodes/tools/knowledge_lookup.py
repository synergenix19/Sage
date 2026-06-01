"""LLM-callable tool: retrieve validated mental health knowledge (v7 §6.5.2).

Upgraded from static dict to PostgresKnowledgeRepository (hybrid BM25+vector).
Falls back to {passages: [], abstain: True} when the DB pool is unavailable
(test environments, offline mode) — never raises, never blocks the tool loop.

knowledge_source in state is set by freeflow_respond after the tool loop,
not by this tool directly (tools return to LLM, not to state).

Use make_knowledge_lookup_tool(language) to inject detected_language at bind time.
The module-level `knowledge_lookup` export defaults to "en" for backward compatibility.
"""
from __future__ import annotations
import json
import logging
from langchain_core.tools import tool
from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

_log = logging.getLogger(__name__)


def _get_pool():
    try:
        from server import app  # noqa: PLC0415
        return getattr(app.state, "_db_pool", None)
    except Exception:
        return None


def make_knowledge_lookup_tool(language: str = "en"):
    """Return a knowledge_lookup @tool with language injected at bind time."""

    @tool
    async def knowledge_lookup(query: str) -> str:
        """Look up validated clinical or psychoeducational information.

        Call this when the user asks a factual question about mental health,
        therapy modalities, psychological concepts, or evidence-based treatment.
        Do NOT call for personal or emotional support queries.

        When the returned JSON has abstain=true, tell the user you do not have
        specific information on that topic. Do not invent clinical facts.

        Args:
            query: The user's factual question (1-2 sentences).
        """
        pool = _get_pool()
        if pool is None:
            return json.dumps({"passages": [], "abstain": True})

        try:
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve(query, language=language, top_k=5)
            return json.dumps({
                "passages": [p.to_dict() for p in result.passages],
                "abstain": result.abstain,
            })
        except Exception as exc:
            _log.warning("[knowledge_lookup] retrieval failed: %s", exc)
            return json.dumps({"passages": [], "abstain": True})

    return knowledge_lookup


# Default export: English — preserves backward compatibility for tests and
# call sites that don't have access to detected_language at import time.
knowledge_lookup = make_knowledge_lookup_tool("en")
