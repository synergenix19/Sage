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
        "vec_distance": 0.1,
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


@pytest.mark.asyncio
async def test_retrieve_stamps_raw_and_searched_query():
    from sage_poc.knowledge.repository import KnowledgeRepository
    from sage_poc.knowledge.models import KnowledgeResult

    class RecordingRepo(KnowledgeRepository):
        async def _search(self, query, language="en", top_k=5):
            return KnowledgeResult(passages=[], abstain=True)

    result = await RecordingRepo().retrieve("أنا قلقان", language="ar")
    assert result.query_raw == "أنا قلقان"
    assert result.query_searched == "انا قلقان"


def test_cosine_threshold_config_defaults_fail_open():
    import importlib, sage_poc.config as cfg
    importlib.reload(cfg)
    assert cfg.COSINE_ABSTAIN_THRESHOLD == 0.0  # fail-open until deploy sets the env var

def test_knowledge_result_has_top_similarity():
    from sage_poc.knowledge.models import KnowledgeResult
    r = KnowledgeResult(passages=[], abstain=True, top_similarity=0.12)
    assert r.top_similarity == 0.12
    assert KnowledgeResult().top_similarity is None


def _mk_pool(rows):
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=rows)
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock(return_value=None)))
    return mock_pool

@pytest.mark.asyncio
async def test_search_abstains_when_top_cosine_below_threshold(monkeypatch):
    """Off-domain: best cosine similarity low -> abstain with EMPTY pack."""
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.30)
    rows = [  # vec_distance 0.85 -> sim 0.15 < 0.30
        {"article_id": "x", "chunk_text": "t", "citation_metadata": {}, "rrf_score": 0.0164, "vec_distance": 0.85},
    ]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("recipe for cake", language="en")
    assert r.abstain is True
    assert r.passages == []            # empty pack, no L4 injection
    assert round(r.top_similarity, 2) == 0.15

@pytest.mark.asyncio
async def test_search_retrieves_when_top_cosine_above_threshold(monkeypatch):
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.30)
    rows = [  # vec_distance 0.20 -> sim 0.80 >= 0.30
        {"article_id": "cbt-001-en", "chunk_text": "CBT...", "citation_metadata": {"citation": "Beck"}, "rrf_score": 0.03, "vec_distance": 0.20},
    ]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("what is CBT", language="en")
    assert r.abstain is False
    assert len(r.passages) == 1 and r.passages[0].source_id == "cbt-001-en"
    assert round(r.top_similarity, 2) == 0.80

@pytest.mark.asyncio
async def test_search_fail_open_when_threshold_zero(monkeypatch):
    """Threshold 0.0 (committed default / rollback) skips the gate even for NEGATIVE
    similarity (distance > 1.0). Guarantees merging Tasks 1-4 is inert in prod."""
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.0)
    rows = [  # vec_distance 1.3 -> sim -0.30 (negative); rrf 0.0164 > 0.015 secondary guard
        {"article_id": "x", "chunk_text": "t", "citation_metadata": {}, "rrf_score": 0.0164, "vec_distance": 1.3},
    ]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("q", language="en")
    assert r.abstain is False          # fail-open: cosine gate skipped
    assert len(r.passages) == 1        # retrieved via retained RRF secondary guard

@pytest.mark.asyncio
async def test_search_null_vec_distance_counts_as_not_similar(monkeypatch):
    """FTS-only rows (NULL vec_distance) don't create similarity -> abstain."""
    import sage_poc.knowledge.postgres_repository as pr
    monkeypatch.setattr(pr, "COSINE_ABSTAIN_THRESHOLD", 0.30)
    rows = [{"article_id": "x", "chunk_text": "t", "citation_metadata": {}, "rrf_score": 0.0164, "vec_distance": None}]
    with patch.object(pr, "_get_embedding", return_value=[0.1] * 1024):
        r = await pr.PostgresKnowledgeRepository(_mk_pool(rows))._search("q", language="en")
    assert r.abstain is True and r.passages == [] and r.top_similarity == 0.0
