"""C1 Further-Reading cards on consult turns (SAGE_CONSULT_SOURCES).

Ruling: docs/superpowers/governance/2026-07-29-consult-further-reading-delivery-shape-ask.md
(Option 1 APPROVED with three in-ruling conditions). Spec: v7.3 amendment record, named open
item + invariant precondition. Mechanism:

  - graph.py `_route_after_skill_select`: a consult-selected turn (skill_match_method ==
    "info_request_skill_consult") detours to `knowledge_retrieve_cards` when
    config.CONSULT_SOURCES_ENABLED, then proceeds to skill_executor via the static edge.
    Flag OFF -> "skill_executor" directly, byte-identical to master.
  - nodes/knowledge_retrieve.py `knowledge_retrieve_cards_node`: writes cards_* channels
    ONLY. The composer reads knowledge_passages, so the prompt-byte-untouched property is
    structural (asserted below on the node's return shape AND on the composer gates).
  - server.py `_sources_header`: cards passages feed X-Sage-Sources when the evidence
    channel is empty; same allowlist gate_path, same 3-card cap.
  - audit.py: cards ids land in knowledge_passage_ids with purpose='cards_only' (ruling
    condition 2); flag-OFF rows carry no purpose key (migration 018 = flip deploy gate).

Both-direction regression discipline (safety-path fixture rule): the KB/evidence path and
the flag-OFF consult path are asserted byte-identical to master alongside the flag-ON tests.
"""
import importlib
import json

import pytest

import sage_poc.config as config
from sage_poc.audit import _build_session_audit_row
from sage_poc.graph import _route_after_skill_select
from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_cards_node
from sage_poc.prompts.composer import _allow_light_structure

import server as server_mod


_PASSAGE = {
    "text": "Anxiety is the body's threat response.",
    "source_id": "anxiety-001-en-000",
    "citation": "NIMH 2025",
    "relevance_score": 0.64,
    "source_url": "https://nimh.nih.gov/anxiety",
    "title": "What is anxiety?",
    "video_url": "",
}


def _consult_state(**over):
    state = {
        "primary_intent": "info_request",
        "skill_match_method": "info_request_skill_consult",
        "active_skill_id": "psychoed_anxiety",
        "path": [],
    }
    state.update(over)
    return state


# ─────────────────────── kill-switch idiom ───────────────────────

def test_consult_sources_default_off_with_no_env_set():
    assert config.CONSULT_SOURCES_ENABLED is False


def test_consult_sources_strict_idiom_only_literal_true_enables(monkeypatch):
    for off_value in ("1", "yes", "", "false", "on", "  ", "truex"):
        monkeypatch.setenv("SAGE_CONSULT_SOURCES", off_value)
        importlib.reload(config)
        assert config.CONSULT_SOURCES_ENABLED is False, repr(off_value)
    for on_value in ("true", "TRUE", " true ", "True"):
        monkeypatch.setenv("SAGE_CONSULT_SOURCES", on_value)
        importlib.reload(config)
        assert config.CONSULT_SOURCES_ENABLED is True, repr(on_value)
    monkeypatch.delenv("SAGE_CONSULT_SOURCES", raising=False)
    importlib.reload(config)


# ─────────────────────── routing ───────────────────────

def test_flag_off_consult_turn_routes_straight_to_executor_byte_identical():
    assert config.CONSULT_SOURCES_ENABLED is False
    assert _route_after_skill_select(_consult_state()) == "skill_executor"


def test_flag_on_consult_turn_detours_through_cards_node(monkeypatch):
    monkeypatch.setattr(config, "CONSULT_SOURCES_ENABLED", True)
    assert _route_after_skill_select(_consult_state()) == "knowledge_retrieve_cards"


def test_flag_on_kb_path_unchanged(monkeypatch):
    # Both-direction: a non-consult info_request must still hit Node 6 with the flag ON.
    monkeypatch.setattr(config, "CONSULT_SOURCES_ENABLED", True)
    state = _consult_state(skill_match_method=None, active_skill_id=None)
    assert _route_after_skill_select(state) == "knowledge_retrieve"


def test_cards_node_edge_lands_on_skill_executor():
    # Topology assertion: the detour rejoins the executor, whose conditional router stays
    # the sole post-executor authority (sequential-not-parallel design decision).
    from sage_poc.graph import build_graph
    g = build_graph().get_graph()
    edges = {(e.source, e.target) for e in g.edges}
    assert ("knowledge_retrieve_cards", "skill_executor") in edges
    assert ("knowledge_retrieve_cards", "freeflow_respond") not in edges


# ─────────────────────── cards node: channel separation ───────────────────────

class _FakeResult:
    def __init__(self, passages, abstain, sim):
        self.passages, self.abstain, self.top_similarity = passages, abstain, sim
        self.query_raw = self.query_searched = "q"


class _FakePassage:
    def to_dict(self):
        return dict(_PASSAGE)


@pytest.mark.asyncio
async def test_cards_node_writes_only_cards_channels(monkeypatch):
    from sage_poc.nodes import knowledge_retrieve as kr
    monkeypatch.setattr(kr, "_get_pool", lambda: object())

    class _FakeRepo:
        def __init__(self, pool): ...
        async def retrieve(self, q, language, top_k):
            return _FakeResult([_FakePassage()], abstain=False, sim=0.64)

    monkeypatch.setattr(kr, "PostgresKnowledgeRepository", _FakeRepo)
    out = await knowledge_retrieve_cards_node({"detected_language": "en", "message_en": "what is anxiety", "path": []})
    assert out["cards_knowledge_passages"] == [_PASSAGE]
    # The structural prompt-untouched property: none of the composer-read channels appear.
    for forbidden in ("knowledge_passages", "knowledge_abstain", "knowledge_source"):
        assert forbidden not in out, forbidden


@pytest.mark.asyncio
async def test_cards_node_abstain_means_zero_cards(monkeypatch):
    # Ruling: weak evidence -> NO cards, never weak cards (ABSTAIN floor applies).
    from sage_poc.nodes import knowledge_retrieve as kr
    monkeypatch.setattr(kr, "_get_pool", lambda: object())

    class _FakeRepo:
        def __init__(self, pool): ...
        async def retrieve(self, q, language, top_k):
            return _FakeResult([_FakePassage()], abstain=True, sim=0.21)

    monkeypatch.setattr(kr, "PostgresKnowledgeRepository", _FakeRepo)
    out = await knowledge_retrieve_cards_node({"detected_language": "en", "message_en": "x", "path": []})
    assert out["cards_knowledge_passages"] == []
    assert out["cards_knowledge_abstain"] is True


def test_composer_light_structure_gate_blind_to_cards_channels():
    # _allow_light_structure fires on knowledge_passages; cards must never trip it.
    state = _consult_state(cards_knowledge_passages=[_PASSAGE], knowledge_passages=[], crisis_state="none")
    assert _allow_light_structure(state) is False


# ─────────────────────── sources header ───────────────────────

def test_sources_header_serves_cards_on_consult_turn():
    result = {"gate_path": "standard", "knowledge_passages": [], "cards_knowledge_passages": [_PASSAGE]}
    header = server_mod._sources_header(result)
    assert header is not None
    (entry,) = json.loads(header)
    assert entry["url"] == _PASSAGE["source_url"]


def test_sources_header_evidence_path_unchanged_and_wins_over_cards():
    ev = dict(_PASSAGE, source_id="other-en-000", source_url="https://apa.org/x")
    result = {"gate_path": "standard", "knowledge_passages": [ev], "cards_knowledge_passages": [_PASSAGE]}
    (entry,) = json.loads(server_mod._sources_header(result))
    assert entry["url"] == ev["source_url"]


def test_sources_header_gate_path_allowlist_still_binds_cards():
    result = {"gate_path": "crisis", "cards_knowledge_passages": [_PASSAGE]}
    assert server_mod._sources_header(result) is None


# ─────────────────────── audit purpose discriminator ───────────────────────

def test_audit_cards_turn_stamps_cards_only_purpose_and_ids():
    row = _build_session_audit_row(_consult_state(
        session_id="s", turn_number=4,
        cards_knowledge_passages=[_PASSAGE],
        cards_knowledge_top_similarity=0.64,
    ))
    assert row["knowledge_retrieval_purpose"] == "cards_only"
    assert row["knowledge_passage_ids"] == [_PASSAGE["source_id"]]
    assert row["knowledge_top_similarity"] == 0.64


def test_audit_flag_off_row_byte_identical_no_purpose_key():
    row = _build_session_audit_row(_consult_state(session_id="s", turn_number=4))
    assert "knowledge_retrieval_purpose" not in row
    assert row["knowledge_passage_ids"] == []


def test_audit_evidence_turn_keeps_evidence_semantics_null_purpose():
    # KB path: ids from knowledge_passages, no purpose key (NULL = today's evidence semantics).
    row = _build_session_audit_row({
        "session_id": "s", "turn_number": 1, "path": [],
        "knowledge_passages": [_PASSAGE], "knowledge_source": "node_6",
    })
    assert "knowledge_retrieval_purpose" not in row
    assert row["knowledge_passage_ids"] == [_PASSAGE["source_id"]]
