import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_knowledge_lookup_returns_known_entry():
    from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup
    raw = await knowledge_lookup.ainvoke({"query": "what is cbt"})
    data = json.loads(raw)
    assert data["abstain"] is False
    assert data["source"] == "knowledge_base_v1"
    assert "CBT" in data["result"] or "Cognitive" in data["result"]


@pytest.mark.asyncio
async def test_knowledge_lookup_returns_abstain_for_unknown():
    from sage_poc.nodes.tools.knowledge_lookup import knowledge_lookup
    raw = await knowledge_lookup.ainvoke({"query": "what is the meaning of life"})
    data = json.loads(raw)
    assert data["abstain"] is True
    assert data["result"] is None


@pytest.mark.asyncio
async def test_knowledge_lookup_always_wired_in_freeflow():
    """freeflow_respond_node includes knowledge_lookup regardless of user_id."""
    from sage_poc.nodes.freeflow_respond import freeflow_respond_node

    captured_tools = []

    async def capture_tools(llm, messages, tools, *, node, language, fallback_llm):
        captured_tools.extend(tools)
        return "response"

    mock_llm = MagicMock()

    with patch("sage_poc.nodes.freeflow_respond._invoke_with_tool_loop", side_effect=capture_tools):
        with patch("sage_poc.nodes.freeflow_respond._get_prior_context", AsyncMock(return_value="")):
            state = {"message_en": "what is CBT?", "messages": [], "detected_language": "en"}
            await freeflow_respond_node(state, llm=mock_llm)

    tool_names = [t.name for t in captured_tools]
    assert "knowledge_lookup" in tool_names
