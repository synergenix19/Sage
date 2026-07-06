"""Lane 2 item 1 — source cards. KnowledgePassage carries source_url + title so the API can
emit them (X-Sage-Sources header) for the frontend to render a source card OUTSIDE the prose.

Additive + byte-identical: existing 4-arg construction still works, new fields default empty, and
the LLM-prompt rendering (composer uses citation/source_id) is unchanged.
"""
from sage_poc.knowledge.models import KnowledgePassage


def test_existing_construction_defaults_new_fields_empty():
    d = KnowledgePassage(text="t", source_id="a-en-000", citation="Anxiety 101", relevance_score=0.5).to_dict()
    assert d["source_url"] == "" and d["title"] == "" and d["video_url"] == ""
    assert d["text"] == "t" and d["citation"] == "Anxiety 101"


def test_passage_carries_url_title_video_through_to_dict():
    d = KnowledgePassage(
        text="t", source_id="a-en-000", citation="Anxiety 101", relevance_score=0.5,
        source_url="https://kb.sage/a", title="Understanding Anxiety",
        video_url="https://www.youtube.com/watch?v=abc123",
    ).to_dict()
    assert d["source_url"] == "https://kb.sage/a"
    assert d["title"] == "Understanding Anxiety"
    assert d["video_url"] == "https://www.youtube.com/watch?v=abc123"


def test_ingestion_citation_meta_includes_video_url():
    from sage_poc.knowledge.ingestion import content_hash  # video_url must affect the hash
    a = {"article_id": "v-001", "language": "en", "title": "T", "source_url": "https://kb/v",
         "citation": "C", "content": "body", "is_crisis_content": False,
         "video_url": "https://www.youtube.com/watch?v=abc"}
    b = {**a, "video_url": ""}
    assert content_hash(a) != content_hash(b)   # changing the video re-ingests


def test_row_to_passage_reads_url_title_video_from_metadata():
    from sage_poc.knowledge.postgres_repository import _row_to_passage
    row = {"chunk_text": "x", "article_id": "anx-001-en-000", "rrf_score": 0.0123,
           "citation_metadata": '{"title": "Understanding Anxiety", "source_url": "https://kb/a", '
                                '"citation": "Anxiety 101", "video_url": "https://youtu.be/xyz"}'}
    p = _row_to_passage(row)
    assert p.title == "Understanding Anxiety" and p.source_url == "https://kb/a"
    assert p.video_url == "https://youtu.be/xyz" and p.citation == "Anxiety 101"


def test_row_to_passage_defaults_missing_metadata_fields():
    from sage_poc.knowledge.postgres_repository import _row_to_passage
    p = _row_to_passage({"chunk_text": "x", "article_id": "a-en", "rrf_score": 0.5, "citation_metadata": "{}"})
    assert p.title == "" and p.source_url == "" and p.video_url == "" and p.citation == "a-en"
