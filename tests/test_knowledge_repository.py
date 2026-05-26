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
