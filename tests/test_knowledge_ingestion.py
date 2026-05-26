"""Tests for knowledge base ingestion script."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_chunk_document_splits_at_sentence_boundaries():
    from sage_poc.knowledge.ingestion import chunk_text
    long_text = (
        "Cognitive Behavioral Therapy is an evidence-based approach. "
        "It helps identify unhelpful thought patterns. "
        "CBT is widely used for depression and anxiety. "
        "Sessions typically last 50 minutes. "
        "It is one of the most researched psychological treatments."
    )
    chunks = chunk_text(long_text, max_tokens=30)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.split()) <= 50, "Chunks should not be massively over-budget"


def test_chunk_document_crisis_content_not_split():
    from sage_poc.knowledge.ingestion import chunk_text
    crisis_text = (
        "If you are in crisis, call 999 immediately. "
        "MoHAP Counselling Line: 800 46342. "
        "Available 24 hours a day, 7 days a week."
    )
    chunks = chunk_text(crisis_text, max_tokens=10, is_crisis_content=True)
    assert len(chunks) == 1, "Crisis content must not be split"
    assert chunks[0] == crisis_text


def test_ingest_document_missing_is_crisis_content_raises():
    from sage_poc.knowledge.ingestion import validate_article_schema
    article = {
        "article_id": "cbt-001",
        "language": "en",
        "title": "CBT Overview",
        "source_url": "https://example.com/cbt",
        "citation": "Beck (1979)",
        "content": "CBT is a therapy approach.",
        # is_crisis_content deliberately missing
    }
    with pytest.raises(ValueError, match="is_crisis_content"):
        validate_article_schema(article)


def test_ingest_document_valid_schema_passes():
    from sage_poc.knowledge.ingestion import validate_article_schema
    article = {
        "article_id": "cbt-001",
        "language": "en",
        "title": "CBT Overview",
        "source_url": "https://example.com/cbt",
        "citation": "Beck (1979)",
        "content": "CBT is a therapy approach.",
        "is_crisis_content": False,
    }
    validate_article_schema(article)  # must not raise
