"""Experiment 4.5 — Retrieval accuracy tests for Node 6 and knowledge_lookup tool.

Tests cover:
  1. knowledge_retrieve_node contract (Node 6, info_request path)
  2. knowledge_lookup tool contract (freeflow mid-protocol path)
  3. language parameter behaviour (always "en" — known current behaviour)
  4. abstain contract (empty pool, empty rows, out-of-scope)
  5. passage shape validation (all required fields present and typed correctly)
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

from tests.experiment_4_5.conftest import (
    make_passage,
    make_result,
    make_abstain_result,
    make_retrieve_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_multi_result() -> KnowledgeResult:
    return KnowledgeResult(
        passages=[
            make_passage(
                text="CBT is evidence-based therapy for depression.",
                source_id="cbt-001-en",
                citation="Beck (1979)",
                relevance_score=0.91,
            ),
            make_passage(
                text="Exposure therapy targets anxiety disorders.",
                source_id="anx-002-en",
                citation="Barlow (2002)",
                relevance_score=0.78,
            ),
        ],
        abstain=False,
    )


# ===========================================================================
# 1. knowledge_retrieve_node — Node 6
# ===========================================================================

class TestKnowledgeRetrieveNode:
    """Contract tests for knowledge_retrieve_node (Node 6)."""

    @pytest.mark.asyncio
    async def test_returns_passages_and_source_on_success(self):
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                result = await knowledge_retrieve_node(make_retrieve_state())

        assert result["knowledge_source"] == "node_6"
        assert result["knowledge_abstain"] is False
        assert len(result["knowledge_passages"]) == 1
        assert "knowledge_retrieve" in result["path"]

    @pytest.mark.asyncio
    async def test_abstains_when_pool_unavailable(self):
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=None):
            result = await knowledge_retrieve_node(make_retrieve_state())

        assert result["knowledge_abstain"] is True
        assert result["knowledge_passages"] == []
        assert result["knowledge_source"] == "node_6"
        assert "knowledge_retrieve" in result["path"]

    @pytest.mark.asyncio
    async def test_abstains_when_repository_returns_empty(self):
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_abstain_result())

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                result = await knowledge_retrieve_node(make_retrieve_state())

        assert result["knowledge_abstain"] is True
        assert result["knowledge_passages"] == []

    @pytest.mark.asyncio
    async def test_returns_multiple_passages(self):
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=_make_multi_result())

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                result = await knowledge_retrieve_node(make_retrieve_state())

        assert len(result["knowledge_passages"]) == 2
        assert result["knowledge_abstain"] is False

    @pytest.mark.asyncio
    async def test_passage_dicts_have_required_fields(self):
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                result = await knowledge_retrieve_node(make_retrieve_state())

        passage = result["knowledge_passages"][0]
        assert "text" in passage
        assert "source_id" in passage
        assert "citation" in passage
        assert "relevance_score" in passage
        assert isinstance(passage["text"], str)
        assert isinstance(passage["source_id"], str)
        assert isinstance(passage["relevance_score"], float)

    @pytest.mark.asyncio
    async def test_path_extended_with_knowledge_retrieve(self):
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        prior_path = ["safety_check", "intent_route", "skill_select"]
        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                result = await knowledge_retrieve_node(make_retrieve_state(path=prior_path))

        assert result["path"] == prior_path + ["knowledge_retrieve"]

    @pytest.mark.asyncio
    async def test_uses_message_en_as_query(self):
        """Node 6 must pass message_en as the query, not raw_message."""
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                await knowledge_retrieve_node(make_retrieve_state(
                    raw_message="ما هو العلاج المعرفي السلوكي",
                    message_en="what is cognitive behavioral therapy",
                ))

        call_args = mock_repo.retrieve.call_args
        # First positional arg is the query
        actual_query = call_args.args[0] if call_args.args else call_args.kwargs.get("query")
        assert actual_query == "what is cognitive behavioral therapy"

    @pytest.mark.asyncio
    async def test_arabic_query_passes_language_en(self):
        """Node 6 hardcodes language='en' regardless of detected_language.

        Current behaviour (documented): knowledge_retrieve_node always calls
        repo.retrieve(..., language='en'). Arabic messages are pre-translated to
        English by the translation node before retrieval. This test documents and
        asserts the current implementation contract.
        """
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=KnowledgeResult(passages=[], abstain=True))

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                await knowledge_retrieve_node(make_retrieve_state(
                    detected_language="ar",
                    message_en="what is cognitive behavioral therapy",
                ))

        mock_repo.retrieve.assert_called_once()
        call_kwargs = mock_repo.retrieve.call_args
        actual_language = (
            call_kwargs.kwargs.get("language")
            if call_kwargs.kwargs
            else (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        )
        assert actual_language == "en", (
            "knowledge_retrieve_node must always call repo.retrieve(..., language='en'). "
            f"Got: {actual_language!r}. "
            "Arabic messages are pre-translated by the translation node before retrieval "
            "and the corpus is indexed in English only."
        )

    @pytest.mark.asyncio
    async def test_top_k_is_five(self):
        """Node 6 must request top_k=5 passages."""
        from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                await knowledge_retrieve_node(make_retrieve_state())

        call_kwargs = mock_repo.retrieve.call_args
        actual_top_k = (
            call_kwargs.kwargs.get("top_k")
            if call_kwargs.kwargs
            else (call_kwargs.args[2] if len(call_kwargs.args) > 2 else None)
        )
        assert actual_top_k == 5


# ===========================================================================
# 2. knowledge_lookup tool — freeflow mid-protocol path
# ===========================================================================

class TestKnowledgeLookupTool:
    """Contract tests for the knowledge_lookup LangChain tool."""

    @pytest.mark.asyncio
    async def test_returns_json_with_passages_and_abstain(self):
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
                raw = await knowledge_lookup.ainvoke({"query": "what is CBT"})

        data = json.loads(raw)
        assert "passages" in data
        assert "abstain" in data
        assert data["abstain"] is False
        assert len(data["passages"]) == 1

    @pytest.mark.asyncio
    async def test_abstains_when_pool_is_none(self):
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=None):
            raw = await knowledge_lookup.ainvoke({"query": "what is CBT"})

        data = json.loads(raw)
        assert data["abstain"] is True
        assert data["passages"] == []

    @pytest.mark.asyncio
    async def test_abstains_on_repository_exception(self):
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(side_effect=RuntimeError("DB error"))

        with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
                raw = await knowledge_lookup.ainvoke({"query": "what is CBT"})

        data = json.loads(raw)
        assert data["abstain"] is True
        assert data["passages"] == []

    @pytest.mark.asyncio
    async def test_passage_shape_in_tool_output(self):
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=make_result())

        with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
                raw = await knowledge_lookup.ainvoke({"query": "CBT"})

        passage = json.loads(raw)["passages"][0]
        assert "text" in passage
        assert "source_id" in passage
        assert "citation" in passage
        assert "relevance_score" in passage

    @pytest.mark.asyncio
    async def test_tool_hardcodes_language_en(self):
        """knowledge_lookup always retrieves with language='en' (corpus is English-only).

        Current behaviour (documented): the tool passes language='en' hardcoded.
        If an Arabic user triggers a tool call, their message_en (English translation)
        is the query, and the corpus language filter is always 'en'.
        """
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=KnowledgeResult(passages=[], abstain=True))

        with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
                await knowledge_lookup.ainvoke({"query": "what is mindfulness therapy"})

        call_kwargs = mock_repo.retrieve.call_args
        actual_language = (
            call_kwargs.kwargs.get("language")
            if call_kwargs.kwargs
            else (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        )
        assert actual_language == "en", (
            "knowledge_lookup tool must call repo.retrieve(..., language='en'). "
            f"Got: {actual_language!r}. "
            "This is current documented behaviour — the corpus is English-only."
        )

    @pytest.mark.asyncio
    async def test_returns_valid_json_string(self):
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=None):
            raw = await knowledge_lookup.ainvoke({"query": "any query"})

        # Must be a parseable JSON string
        assert isinstance(raw, str)
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_multiple_passages_returned(self):
        from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

        mock_repo = MagicMock()
        mock_repo.retrieve = AsyncMock(return_value=_make_multi_result())

        with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
            with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
                raw = await knowledge_lookup.ainvoke({"query": "anxiety treatments"})

        data = json.loads(raw)
        assert len(data["passages"]) == 2
        assert data["abstain"] is False


# ===========================================================================
# 3. PostgresKnowledgeRepository — unit-level contract
# ===========================================================================

class TestPostgresKnowledgeRepositoryContract:
    """Unit tests for PostgresKnowledgeRepository.retrieve() contract.

    All DB calls are mocked at the asyncpg pool level.
    """

    def _make_mock_pool(self, rows: list[dict]) -> MagicMock:
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=rows)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=False),
            )
        )
        return mock_pool

    @pytest.mark.asyncio
    async def test_returns_passages_from_rows(self):
        from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

        rows = [
            {
                "article_id": "cbt-001-en",
                "chunk_text": "CBT is evidence-based therapy.",
                "citation_metadata": '{"citation": "Beck (1979)"}',
                "rrf_score": 0.85,
            }
        ]
        pool = self._make_mock_pool(rows)

        with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 768):
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve("what is CBT", language="en", top_k=5)

        assert result.abstain is False
        assert len(result.passages) == 1
        p = result.passages[0]
        assert p.source_id == "cbt-001-en"
        assert p.citation == "Beck (1979)"
        assert "CBT" in p.text

    @pytest.mark.asyncio
    async def test_abstains_on_empty_rows(self):
        from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

        pool = self._make_mock_pool([])

        with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 768):
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve("obscure out-of-scope topic", language="en", top_k=5)

        assert result.abstain is True
        assert result.passages == []

    @pytest.mark.asyncio
    async def test_abstains_on_exception(self):
        from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(side_effect=RuntimeError("connection refused"))

        with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 768):
            repo = PostgresKnowledgeRepository(mock_pool)
            result = await repo.retrieve("what is CBT", language="en", top_k=5)

        assert result.abstain is True
        assert result.passages == []

    @pytest.mark.asyncio
    async def test_filters_zero_score_rows(self):
        """Rows with rrf_score == 0.0 must be filtered out (abstain threshold)."""
        from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

        rows = [
            {
                "article_id": "cbt-001-en",
                "chunk_text": "CBT text.",
                "citation_metadata": None,
                "rrf_score": 0.0,
            }
        ]
        pool = self._make_mock_pool(rows)

        with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 768):
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve("query", language="en", top_k=5)

        assert result.abstain is True
        assert result.passages == []

    @pytest.mark.asyncio
    async def test_passage_relevance_score_rounded_to_four_places(self):
        from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

        rows = [
            {
                "article_id": "src-001",
                "chunk_text": "Some text.",
                "citation_metadata": None,
                "rrf_score": 0.123456789,
            }
        ]
        pool = self._make_mock_pool(rows)

        with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 768):
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve("query", language="en", top_k=5)

        assert len(result.passages) == 1
        score = result.passages[0].relevance_score
        assert score == round(0.123456789, 4)

    @pytest.mark.asyncio
    async def test_citation_falls_back_to_article_id_when_metadata_missing(self):
        """When citation_metadata is None, citation must fall back to article_id."""
        from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

        rows = [
            {
                "article_id": "fallback-001",
                "chunk_text": "Some text without metadata.",
                "citation_metadata": None,
                "rrf_score": 0.5,
            }
        ]
        pool = self._make_mock_pool(rows)

        with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 768):
            repo = PostgresKnowledgeRepository(pool)
            result = await repo.retrieve("query", language="en", top_k=5)

        assert result.passages[0].citation == "fallback-001"
