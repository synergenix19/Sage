"""Shared fixtures for Experiment 4.5 — RAG Retrieval Accuracy & Grounding."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult


# ---------------------------------------------------------------------------
# Knowledge passage / result factories
# ---------------------------------------------------------------------------

def make_passage(
    text: str = "CBT is an evidence-based therapy for depression.",
    source_id: str = "cbt-001-en",
    citation: str = "Beck (1979)",
    relevance_score: float = 0.88,
) -> KnowledgePassage:
    return KnowledgePassage(
        text=text,
        source_id=source_id,
        citation=citation,
        relevance_score=relevance_score,
    )


def make_result(passages: list[KnowledgePassage] | None = None, abstain: bool = False) -> KnowledgeResult:
    if passages is None:
        passages = [make_passage()]
    return KnowledgeResult(passages=passages, abstain=abstain)


def make_abstain_result() -> KnowledgeResult:
    return KnowledgeResult(passages=[], abstain=True)


# ---------------------------------------------------------------------------
# State factories
# ---------------------------------------------------------------------------

def make_retrieve_state(**overrides) -> dict:
    """Minimal SageState dict for knowledge_retrieve_node tests."""
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


def make_gate_state(**overrides) -> dict:
    """Minimal SageState dict for output_gate_node tests."""
    base = {
        "raw_message": "what is CBT?",
        "detected_language": "en",
        "message_en": "what is CBT?",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "conversation_summary": None,
        "code_switching": False,
        "primary_intent": "info_request",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 4,
        "engagement": 6,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": "standard",
        "response_en": "CBT is an evidence-based approach to treating depression.",
        "response": None,
        "path": ["safety_check", "intent_route", "skill_select", "knowledge_retrieve", "freeflow_respond"],
        "turn_count": 0,
        "turn_number": 1,
        "conversation_history": [],
        "knowledge_passages": [
            {
                "text": "CBT is an evidence-based therapy for depression.",
                "source_id": "cbt-001-en",
                "citation": "Beck (1979)",
                "relevance_score": 0.88,
            }
        ],
        "knowledge_abstain": False,
        "knowledge_source": "node_6",
        "user_id": None,
        "session_id": "test-rag-sess-001",
        "third_party_crisis": False,
        "stale_skill_id": None,
        "identity_substitution_rule_id": None,
        "original_response_hash": None,
        "original_response_text": None,
        "cultural_output_violations": [],
        "resistance_history": [],
        "resistance_score": None,
        "rule_fired": None,
        "prev_step_id": None,
        "new_clinical_flags_turn": [],
        "re_escalation_within_monitoring": None,
        "therapeutic_profile": None,
        "prompt_layers": [],
        "token_usage": {},
        "last_turn_at": None,
    }
    return {**base, **overrides}


def make_compose_state(**overrides) -> dict:
    """Minimal SageState dict for compose_prompt grounding tests."""
    base = {
        "raw_message": "what is CBT?",
        "detected_language": "en",
        "message_en": "what is CBT?",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "new_clinical_flags_turn": [],
        "third_party_crisis": False,
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "conversation_summary": None,
        "code_switching": False,
        "primary_intent": "info_request",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 4,
        "engagement": 6,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "prev_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "prompt_layers": [],
        "token_usage": {},
        "escalation_triggered": None,
        "resistance_history": [],
        "resistance_score": None,
        "cultural_output_violations": [],
        "knowledge_passages": [
            {
                "text": "CBT is an evidence-based therapy for depression.",
                "source_id": "cbt-001-en",
                "citation": "Beck (1979)",
                "relevance_score": 0.88,
            }
        ],
        "knowledge_abstain": False,
        "knowledge_source": "node_6",
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": ["safety_check", "intent_route", "skill_select", "knowledge_retrieve"],
        "turn_count": 0,
        "turn_number": 1,
        "conversation_history": [],
        "therapeutic_profile": None,
        "user_id": None,
        "session_id": None,
        "last_turn_at": None,
        "stale_skill_id": None,
        "identity_substitution_rule_id": None,
        "original_response_hash": None,
        "original_response_text": None,
        "re_escalation_within_monitoring": None,
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# rules_engine mock helper (mirrors test_prompts_composer.py _no_rules pattern)
# ---------------------------------------------------------------------------

def _no_rules():
    """Return a side_effect callable that stubs rules_engine.evaluate with empty actions."""
    cultural = MagicMock()
    cultural.actions = []
    injection = MagicMock()
    injection.actions = []

    def _eval(cat, _ctx):
        return cultural if cat == "cultural" else injection

    return _eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_passage():
    return make_passage()


@pytest.fixture
def multi_passage():
    return [
        make_passage(
            text="CBT is an evidence-based therapy for depression.",
            source_id="cbt-001-en",
            citation="Beck (1979)",
            relevance_score=0.91,
        ),
        make_passage(
            text="Exposure therapy is effective for anxiety disorders.",
            source_id="anx-002-en",
            citation="Barlow (2002)",
            relevance_score=0.78,
        ),
        make_passage(
            text="Mindfulness-based cognitive therapy reduces relapse risk.",
            source_id="mbct-003-en",
            citation="Segal et al. (2002)",
            relevance_score=0.65,
        ),
    ]


@pytest.fixture
def mock_repo():
    """AsyncMock PostgresKnowledgeRepository with sensible defaults."""
    repo = MagicMock()
    repo.retrieve = AsyncMock(return_value=make_result())
    return repo
