"""The audit record must carry both the raw and the searched query so the
normalization applied inside the repository is not invisible to the trail."""
from sage_poc.audit import _build_session_audit_row


def test_audit_record_includes_raw_and_searched_query():
    state = {
        "knowledge_source": "node_6",
        "knowledge_passages": [],
        "knowledge_abstain": True,
        "knowledge_query_raw": "أنا قلقان",
        "knowledge_query_searched": "انا قلقان",
    }
    record = _build_session_audit_row(state)
    assert record["knowledge_query_raw"] == "أنا قلقان"
    assert record["knowledge_query_searched"] == "انا قلقان"


def test_audit_record_includes_top_similarity():
    rec = _build_session_audit_row({"knowledge_source": "node_6", "knowledge_top_similarity": 0.11})
    assert rec["knowledge_top_similarity"] == 0.11
