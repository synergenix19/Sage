import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_knowledge_lookup_returns_known_entry():
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
    from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

    mock_passage = KnowledgePassage(
        text="CBT (Cognitive Behavioural Therapy) is an evidence-based approach.",
        source_id="cbt-001-en",
        citation="Beck (1979)",
        relevance_score=0.91,
    )
    mock_result = KnowledgeResult(passages=[mock_passage], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)

    with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            raw = await knowledge_lookup.ainvoke({"query": "what is cbt"})

    data = json.loads(raw)
    assert data["abstain"] is False
    assert len(data["passages"]) == 1
    assert "CBT" in data["passages"][0]["text"] or "Cognitive" in data["passages"][0]["text"]


@pytest.mark.asyncio
async def test_knowledge_lookup_returns_abstain_for_unknown():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

    mock_result = KnowledgeResult(passages=[], abstain=True)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)

    with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            raw = await knowledge_lookup.ainvoke({"query": "what is the meaning of life"})

    data = json.loads(raw)
    assert data["abstain"] is True
    assert data["passages"] == []


@pytest.mark.asyncio
async def test_knowledge_lookup_always_wired_in_freeflow():
    """freeflow_respond_node includes knowledge_lookup regardless of user_id."""
    from sage_poc.nodes.freeflow_respond import freeflow_respond_node

    captured_tools = []

    async def capture_tools(llm, messages, tools, *, node, language, fallback_llm, **kwargs):
        captured_tools.extend(tools)
        return "response"

    mock_llm = MagicMock()

    with patch("sage_poc.nodes.freeflow_respond._invoke_with_tool_loop", side_effect=capture_tools):
        with patch("sage_poc.nodes.freeflow_respond._get_prior_context", AsyncMock(return_value="")):
            state = {"message_en": "what is CBT?", "messages": [], "detected_language": "en"}
            await freeflow_respond_node(state, llm=mock_llm)

    tool_names = [t.name for t in captured_tools]
    assert "knowledge_lookup" in tool_names


@pytest.mark.asyncio
async def test_knowledge_lookup_uses_repository_when_pool_available():
    """When DB pool is available, tool must call PostgresKnowledgeRepository, not static dict."""
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
    from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

    mock_passage = KnowledgePassage(
        text="CBT is evidence-based therapy for depression.",
        source_id="cbt-001-en",
        citation="Beck (1979)",
        relevance_score=0.88,
    )
    mock_result = KnowledgeResult(passages=[mock_passage], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)

    with patch("sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            raw = await knowledge_lookup.ainvoke({"query": "what is CBT?"})

    data = json.loads(raw)
    assert data["abstain"] is False
    assert len(data["passages"]) == 1
    assert data["passages"][0]["source_id"] == "cbt-001-en"


@pytest.mark.asyncio
async def test_knowledge_lookup_falls_back_to_abstain_when_no_pool():
    """When DB pool is None, tool must return abstain without raising."""
    from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup

    with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=None):
        raw = await knowledge_lookup.ainvoke({"query": "what is CBT?"})

    data = json.loads(raw)
    assert data["abstain"] is True
    assert data["passages"] == []


@pytest.mark.asyncio
async def test_tool_arabic_query_normalized_before_search():
    """Tool path: an Arabic tool query reaches _search normalized. Observed at
    _search (non-vacuous)."""
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    seen = {}

    async def fake_search(self, query, language="en", top_k=5):
        seen["query"] = query
        return KnowledgeResult(passages=[], abstain=True)

    tool = make_knowledge_lookup_tool(language="ar")
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            await tool.ainvoke({"query": "أنا قلقان"})

    assert seen["query"] == "انا قلقان"


@pytest.mark.asyncio
async def test_tool_english_query_in_arabic_conversation_not_normalized():
    """Language flag is 'ar' but the LLM-authored query is English — script
    gating means it is NOT normalized (reaches _search unchanged)."""
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    seen = {}

    async def fake_search(self, query, language="en", top_k=5):
        seen["query"] = query
        return KnowledgeResult(passages=[], abstain=True)

    tool = make_knowledge_lookup_tool(language="ar")  # Arabic conversation
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            await tool.ainvoke({"query": "what is CBT?"})   # English query

    assert seen["query"] == "what is CBT?"   # untouched


@pytest.mark.asyncio
async def test_tool_json_includes_query_trace():
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True)

    tool = make_knowledge_lookup_tool(language="ar")
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            raw = await tool.ainvoke({"query": "أنا قلقان"})

    data = json.loads(raw)
    assert data["query_raw"] == "أنا قلقان"
    assert data["query_searched"] == "انا قلقان"


# ---------------------------------------------------------------------------
# Task 4 fix: tool-path query trace must correlate knowledge_lookup tool_call
# ids to their ToolMessage RESULT (not scan for a "knowledge_lookup"-named
# message, which never exists — ToolMessages carry tool_call_id, not name).
# ---------------------------------------------------------------------------

def test_knowledge_lookup_trace_extracts_from_toolmessage():
    """Unit: trace correlates the knowledge_lookup call id to its ToolMessage result."""
    from langchain_core.messages import AIMessage, ToolMessage
    from sage_poc.nodes.freeflow_respond import _knowledge_lookup_trace

    ai = AIMessage(content="", tool_calls=[{"name": "knowledge_lookup", "args": {"query": "أنا قلقان"}, "id": "call_1"}])
    tool = ToolMessage(content=json.dumps({"passages": [], "abstain": True, "query_raw": "أنا قلقان", "query_searched": "انا قلقان"}), tool_call_id="call_1")
    trace = _knowledge_lookup_trace([ai, tool])
    assert trace == {
        "knowledge_query_raw": "أنا قلقان",
        "knowledge_query_searched": "انا قلقان",
        "knowledge_top_similarity": None,
    }


def test_knowledge_lookup_trace_empty_when_not_fired():
    from sage_poc.nodes.freeflow_respond import _knowledge_lookup_trace
    assert _knowledge_lookup_trace([]) == {}


@pytest.mark.asyncio
async def test_tool_loop_captures_toolmessage_for_trace():
    """Integration: _invoke_with_tool_loop records the ToolMessage result so the
    trace can be recovered after the loop (the seam the real freeflow uses)."""
    from langchain_core.messages import AIMessage
    from sage_poc.knowledge.models import KnowledgeResult
    from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository
    from sage_poc.nodes.freeflow_respond import _invoke_with_tool_loop, _knowledge_lookup_trace
    from sage_poc.nodes.tools.knowledge_lookup import make_knowledge_lookup_tool

    tool = make_knowledge_lookup_tool(language="ar")

    # Stub LLM: first call requests knowledge_lookup, second returns plain text.
    class StubLLM:
        def __init__(self):
            self.calls = 0

        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return AIMessage(content="", tool_calls=[{"name": "knowledge_lookup", "args": {"query": "أنا قلقان"}, "id": "call_1"}])
            return AIMessage(content="done")

    async def fake_search(self, query, language="en", top_k=5):
        return KnowledgeResult(passages=[], abstain=True)

    captured: list = []
    with patch.object(PostgresKnowledgeRepository, "_search", fake_search):
        with patch("sage_poc.nodes.tools.knowledge_lookup._get_pool", return_value=MagicMock()):
            await _invoke_with_tool_loop(
                StubLLM(), [{"role": "user", "content": "..."}], [tool],
                node="freeflow_respond", language="ar", fallback_llm=None,
                _tool_messages=captured,
            )

    trace = _knowledge_lookup_trace(captured)
    assert trace["knowledge_query_raw"] == "أنا قلقان"
    assert trace["knowledge_query_searched"] == "انا قلقان"
