"""Tests for Node 6: knowledge_retrieve."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _kr_state(**overrides):
    base = {
        "raw_message": "what is CBT?",
        "detected_language": "en",
        "message_en": "what is CBT?",
        "primary_intent": "info_request",
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "path": ["safety_check", "intent_route", "skill_select"],
        "user_id": None,
        "session_id": None,
    }
    return {**base, **overrides}


@pytest.mark.asyncio
async def test_knowledge_retrieve_writes_passages_and_source():
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    mock_passage = KnowledgePassage(
        text="CBT is evidence-based.", source_id="cbt-001-en",
        citation="Beck (1979)", relevance_score=0.85,
    )
    mock_result = KnowledgeResult(passages=[mock_passage], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(_kr_state())

    assert result["knowledge_source"] == "node_6"
    assert len(result["knowledge_passages"]) == 1
    assert result["knowledge_passages"][0]["source_id"] == "cbt-001-en"
    assert result["knowledge_abstain"] is False
    assert "knowledge_retrieve" in result["path"]


@pytest.mark.asyncio
async def test_knowledge_retrieve_abstains_on_db_unavailable():
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=None):
        result = await knowledge_retrieve_node(_kr_state())

    assert result["knowledge_abstain"] is True
    assert result["knowledge_passages"] == []
    assert result["knowledge_source"] == "node_6"


@pytest.mark.asyncio
async def test_knowledge_retrieve_routes_arabic_to_ar_corpus():
    """Arabic turns route to the AR corpus (language='ar') using raw_message as query.

    Post-091d103: knowledge_retrieve_node passes detected_language to repo.retrieve(),
    so Arabic turns query the Arabic corpus directly. The query text is raw_message
    (original Arabic text), not message_en (translated English).
    """
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=KnowledgeResult(passages=[], abstain=True))

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            await knowledge_retrieve_node(_kr_state(detected_language="ar", message_en="what is CBT?"))

    mock_repo.retrieve.assert_called_once()
    call_kwargs = mock_repo.retrieve.call_args
    # language must be 'ar' — Arabic turns query the Arabic corpus
    language_arg = call_kwargs.kwargs.get("language") or (
        call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
    )
    assert language_arg == "ar", f"Expected language='ar', got: {call_kwargs}"
    # query must be raw_message, not message_en
    query_arg = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("query")
    assert query_arg == "what is CBT?", f"Expected raw_message as query, got: {query_arg}"


@pytest.mark.asyncio
async def test_node_arabic_query_normalized_before_search():
    """Node path: an Arabic turn reaches the backend _search with a normalized
    query. Observed at _search so the assertion cannot pass without the rewrite."""
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    seen = {}

    async def fake_search(self, query, language="en", top_k=5):
        seen["query"] = query
        seen["language"] = language
        return KnowledgeResult(passages=[], abstain=True)

    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            await knowledge_retrieve_node(
                _kr_state(detected_language="ar", raw_message="أنا قلقان", message_en="I am anxious")
            )

    assert seen["query"] == "انا قلقان"   # normalized, not raw "أنا قلقان"
    assert seen["language"] == "ar"


@pytest.mark.asyncio
async def test_node_writes_query_trace_to_state():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node

    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True)

    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(
                _kr_state(detected_language="ar", raw_message="أنا قلقان", message_en="I am anxious")
            )

    assert result["knowledge_query_raw"] == "أنا قلقان"
    assert result["knowledge_query_searched"] == "انا قلقان"


@pytest.mark.asyncio
async def test_node_emits_top_similarity_to_state():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node
    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True, top_similarity=0.11)
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            r = await knowledge_retrieve_node(_kr_state(detected_language="en"))
    assert r["knowledge_top_similarity"] == 0.11
