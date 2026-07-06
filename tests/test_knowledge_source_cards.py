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


# ---------------------------------------------------------------------------
# Lane 2 item 4 — _sources_header: X-Sage-Sources response header.
#
# server.py lives at the repo root (outside src/sage_poc/ — see the crisis-card
# sentinel comment in server.py's /chat handler for the same repo-layout note),
# so the import here is `from server import ...`, matching the existing
# convention in test_stream_tokens.py / test_server.py, not `sage_poc.server`.
# ---------------------------------------------------------------------------
import json
from server import _sources_header


def _p(**kw):  # passage dict helper
    base = {"text": "t", "source_id": "a-en-000", "citation": "c", "source_url": "https://kb/a",
            "title": "T", "video_url": "", "relevance_score": 0.5}
    return {**base, **kw}


def test_allowlist_suppresses_crisis_medical_and_unknown():
    # ALLOWLIST: only ordinary content paths emit. Future safety routes + unknown values fail SAFE.
    for gp in ("crisis", "medical", "hr", "ipv", "jailbreak", "scope_refusal", "future_route", None):
        assert _sources_header({"gate_path": gp, "knowledge_passages": [_p()]}) is None


def test_allowlist_emits_on_standard():
    hdr = _sources_header({"gate_path": "standard", "knowledge_passages": [_p()]})
    assert json.loads(hdr) == [{"type": "article", "title": "T", "url": "https://kb/a", "citation": "c"}]


def test_video_entry_type_and_url():
    hdr = _sources_header({"gate_path": "standard", "knowledge_passages": [
        _p(video_url="https://www.youtube.com/watch?v=abc")]})
    assert json.loads(hdr)[0] == {"type": "video", "title": "T",
                                  "url": "https://www.youtube.com/watch?v=abc", "citation": "c"}


def test_arabic_title_is_header_safe_and_roundtrips():
    hdr = _sources_header({"gate_path": "standard", "knowledge_passages": [_p(title="القلق")]})
    assert hdr.isascii()                      # HTTP-header-safe (ensure_ascii=True)
    assert json.loads(hdr)[0]["title"] == "القلق"   # round-trips


def test_dedupe_by_source_url_and_cap_at_three():
    passages = [_p(source_url="https://kb/a", source_id=f"a-en-{i:03d}") for i in range(3)]  # same article, 3 chunks
    passages += [_p(source_url=f"https://kb/{x}") for x in ("b", "c", "d", "e")]
    entries = json.loads(_sources_header({"gate_path": "standard", "knowledge_passages": passages}))
    urls = [e["url"] for e in entries]
    assert urls.count("https://kb/a") == 1     # deduped
    assert len(entries) == 3                   # capped


def test_no_header_when_no_usable_source():
    assert _sources_header({"gate_path": "standard", "knowledge_passages": [_p(source_url="", video_url="", title="")]}) is None
    assert _sources_header({"gate_path": "standard", "knowledge_passages": []}) is None
