"""Tests for knowledge retrieval layer — Task 3 through Task 6."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_knowledge_passage_dataclass():
    from sage_poc.knowledge.models import KnowledgePassage
    p = KnowledgePassage(
        text="CBT is evidence-based therapy.",
        source_id="cbt-001-en",
        citation="Beck (1979)",
        relevance_score=0.88,
    )
    assert p.text == "CBT is evidence-based therapy."
    assert p.source_id == "cbt-001-en"
    assert p.relevance_score == 0.88


def test_knowledge_result_abstain():
    from sage_poc.knowledge.models import KnowledgeResult
    r = KnowledgeResult(passages=[], abstain=True)
    assert r.abstain is True
    assert r.passages == []


def test_knowledge_result_with_passages():
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
    p = KnowledgePassage(text="text", source_id="id-1", citation="src", relevance_score=0.7)
    r = KnowledgeResult(passages=[p], abstain=False)
    assert not r.abstain
    assert len(r.passages) == 1


def test_rewriter_normalizes_common_alef_variants():
    from sage_poc.knowledge.rewriter import normalize_arabic_query
    assert normalize_arabic_query("أنا") == "انا"
    assert normalize_arabic_query("إنسان") == "انسان"
    assert normalize_arabic_query("آخر") == "اخر"


def test_rewriter_passthrough_for_english():
    from sage_poc.knowledge.rewriter import normalize_arabic_query
    result = normalize_arabic_query("what is CBT?")
    assert result == "what is CBT?"


@pytest.mark.asyncio
async def test_base_retrieve_normalizes_arabic_before_search():
    """Interface contract: any KnowledgeRepository normalizes an Arabic query
    BEFORE the backend _search sees it. Guarantees the rewrite survives a
    repository swap (Postgres -> Azure)."""
    from sage_poc.knowledge.repository import KnowledgeRepository
    from sage_poc.knowledge.models import KnowledgeResult

    seen = {}

    class RecordingRepo(KnowledgeRepository):
        async def _search(self, query, language="en", top_k=5):
            seen["query"] = query
            return KnowledgeResult(passages=[], abstain=True)

    repo = RecordingRepo()
    # 'أنا' contains an Alef-hamza that normalizes to 'انا'
    await repo.retrieve("أنا قلقان", language="ar", top_k=5)
    assert seen["query"] == "انا قلقان"


@pytest.mark.asyncio
async def test_base_retrieve_passes_english_through_untouched():
    from sage_poc.knowledge.repository import KnowledgeRepository
    from sage_poc.knowledge.models import KnowledgeResult

    seen = {}

    class RecordingRepo(KnowledgeRepository):
        async def _search(self, query, language="en", top_k=5):
            seen["query"] = query
            return KnowledgeResult(passages=[], abstain=True)

    repo = RecordingRepo()
    await repo.retrieve("what is CBT?", language="en")
    assert seen["query"] == "what is CBT?"


def test_contains_arabic_detects_script():
    from sage_poc.knowledge.repository import KnowledgeRepository
    assert KnowledgeRepository._contains_arabic("ما هو") is True
    assert KnowledgeRepository._contains_arabic("what is CBT") is False
    assert KnowledgeRepository._contains_arabic("CBT ما هو") is True  # mixed Araglish


@pytest.mark.asyncio
async def test_postgres_repo_returns_passages_on_match():
    """Hybrid search returns KnowledgeResult with passages when rows are found."""
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.knowledge.models import KnowledgePassage

    fake_row = {
        "article_id": "cbt-001-en",
        "chunk_text": "CBT is an evidence-based therapy.",
        "citation_metadata": {"citation": "Beck (1979)"},
        "rrf_score": 0.042,
    }

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[fake_row])
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))

    with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 1024):
        repo = PostgresKnowledgeRepository(mock_pool)
        result = await repo.retrieve("what is CBT", language="en", top_k=5)

    assert not result.abstain
    assert len(result.passages) == 1
    assert result.passages[0].source_id == "cbt-001-en"
    assert result.passages[0].citation == "Beck (1979)"


@pytest.mark.asyncio
async def test_postgres_repo_abstains_when_no_rows():
    """Returns abstain=True when no rows are returned."""
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))

    with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 1024):
        repo = PostgresKnowledgeRepository(mock_pool)
        result = await repo.retrieve("completely unrelated query xyz", language="en")

    assert result.abstain is True
    assert result.passages == []


@pytest.mark.asyncio
async def test_postgres_repo_filters_by_language():
    """Language filter is passed to DB query."""
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=None),
    ))

    with patch("sage_poc.knowledge.postgres_repository._get_embedding", return_value=[0.1] * 1024):
        repo = PostgresKnowledgeRepository(mock_pool)
        await repo.retrieve("ما هو العلاج المعرفي", language="ar")

    call_args = mock_conn.fetch.call_args
    # The SQL query or its arguments must include the language filter value "ar"
    assert any("ar" in str(a) for a in call_args.args + tuple(call_args.kwargs.values()))
