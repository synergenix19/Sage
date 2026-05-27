"""E2E test: info_request flows through all 8 nodes.

Real graph, mocked LLM and DB. Verifies that result state contains
knowledge_source, knowledge_passages, and that the audit trail records
the retrieval path — the proof a clinical reviewer needs to trace
evidence back to its source.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _full_state(**overrides):
    base = {
        "raw_message": "what is CBT?",
        "detected_language": "en",
        "message_en": "what is CBT?",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "third_party_crisis": False,
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "conversation_summary": None,
        "code_switching": False,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "prompt_layers": [],
        "token_usage": {},
        "therapeutic_profile": None,
        "user_id": None,
        "session_id": None,
        "cultural_output_violations": [],
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    return {**base, **overrides}


@pytest.mark.asyncio
@pytest.mark.slow
async def test_e2e_info_request_audit_trail():
    """Full graph run: info_request routes to Node 6, evidence appears in final state.

    Mocks:
    - resilient_invoke: returns intent classification JSON for intent_route node,
      and a plain text response for freeflow_respond node.
    - PostgresKnowledgeRepository.retrieve: returns one known passage.
    - _get_pool: returns a non-None mock so Node 6 doesn't early-exit.
    """
    from sage_poc.graph import build_graph
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    known_passage = KnowledgePassage(
        text="Cognitive Behavioral Therapy (CBT) is an evidence-based therapy for depression.",
        source_id="cbt-001-en",
        citation="Beck (1979)",
        relevance_score=0.88,
    )
    mock_knowledge_result = KnowledgeResult(passages=[known_passage], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_knowledge_result)

    call_count = {"n": 0}

    async def mock_resilient_invoke(llm, messages, *, node, language="en", fallback_llm=None, **kwargs):
        call_count["n"] += 1
        if node == "intent_route":
            return (
                '{"primary_intent": "info_request", "secondary_intent": null, '
                '"intent_confidence": 0.92, "emotional_intensity": 3, "engagement": 7}'
            )
        return "CBT stands for Cognitive Behavioral Therapy. It is an evidence-based approach."

    graph = build_graph(checkpointer=None)

    fixed_response = "CBT stands for Cognitive Behavioral Therapy. It is an evidence-based approach."

    async def mock_tool_loop(llm, messages, tools, *, node, language, fallback_llm, _tool_messages=None):
        return fixed_response

    with patch("sage_poc.nodes.freeflow_respond.resilient_invoke", side_effect=mock_resilient_invoke):
        with patch("sage_poc.nodes.intent_route.resilient_invoke", side_effect=mock_resilient_invoke):
            with patch("sage_poc.nodes.freeflow_respond._invoke_with_tool_loop", side_effect=mock_tool_loop):
                with patch(
                    "sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository",
                    return_value=mock_repo,
                ):
                    with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
                        result = await graph.ainvoke(
                            _full_state(),
                            config={"configurable": {"thread_id": "test-e2e-knowledge-001"}},
                        )

    # 1. Knowledge retrieval state fields
    assert result["knowledge_source"] == "node_6", (
        f"Expected knowledge_source='node_6', got '{result['knowledge_source']}'"
    )
    assert len(result["knowledge_passages"]) == 1
    assert result["knowledge_passages"][0]["source_id"] == "cbt-001-en"
    assert result["knowledge_abstain"] is False

    # 2. Node 6 was in the execution path
    assert "knowledge_retrieve" in result["path"], (
        f"knowledge_retrieve not in path: {result['path']}"
    )

    # 3. A response was produced
    assert result["response"] is not None
    assert len(result["response"]) > 0

    # 4. The path includes all expected nodes in correct order
    path = result["path"]
    assert path.index("safety_check") < path.index("intent_route")
    assert path.index("intent_route") < path.index("skill_select")
    assert path.index("skill_select") < path.index("knowledge_retrieve")
    assert path.index("knowledge_retrieve") < path.index("freeflow_respond")
    assert path.index("freeflow_respond") < path.index("output_gate")
