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
