"""Phase 2 Task 10: knowledge_retrieve's psychoed integration.

Three behaviors, all gated by `config.PSYCHOED_PATHWAYS_ENABLED`:
  - outcome-1: a `psychoed_serve` payload already resolved by skill_select is a
    deterministic store fetch -- repo.retrieve() is NEVER called, the payload is
    enriched with a content_hash, and the family/blocks-served channels are appended.
  - menu-after-weave passthrough: same no-DB shape, but nothing to append (no payload).
  - outcome-2: the semantic backstop -- when the normal RAG path's TOP passage happens
    to be a psychoed block (fail-to-personal framing), and the L4 quarantine that keeps
    psychoed copy out of knowledge_passages (and therefore out of LLM synthesis) in
    every flag-ON turn, regardless of which outcome fired.

Mirrors tests/test_knowledge_retrieve_node.py's fake-pool/fake-repo pattern.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sage_poc.config as config
from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node
from sage_poc.psychoed import store as psy_store


def _kr_state(**overrides):
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


# ─────────────────────────── (a) outcome-1: deterministic store fetch, no DB ───────────────────────────

@pytest.mark.asyncio
async def test_outcome1_serve_payload_skips_db_and_enriches_hash(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    serve_payload = {
        "category": "3c", "block_id": "3c-b4", "route": "standard",
        "framing": "personal", "weave_due": True,
        "matched_row_id": "3c-t3", "collision_path": None,
    }
    state = _kr_state(
        psychoed_serve=serve_payload,
        psychoed_blocks_served=["1f-b1"],
        psychoed_family_exposures=["understanding_anxiety"],
    )
    mock_repo_cls = MagicMock()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", mock_repo_cls):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    mock_repo_cls.assert_not_called()  # repo never constructed -> retrieve() never called; no DB
    assert result["psychoed_serve"]["content_hash"] == psy_store.block_sha256("3c-b4")
    assert result["psychoed_serve"]["category"] == "3c"  # original payload keys survive
    assert result["psychoed_blocks_served"] == ["1f-b1", "3c-b4"]
    assert result["psychoed_family_exposures"] == ["understanding_anxiety", "understanding_depression"]
    assert result["knowledge_passages"] == []
    assert result["knowledge_abstain"] is False
    assert result["knowledge_source"] == "psychoed_store"
    assert result["path"] == state["path"] + ["knowledge_retrieve"]


@pytest.mark.asyncio
async def test_outcome1_menu_first_hit_falls_back_to_first_block_family(monkeypatch):
    """block_id=None (menu-first hit): no content_hash, no blocks_served append, but the
    family-exposure channel still gets an entry -- derived from the category's first
    manifest block (no specific block was served yet)."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    serve_payload = {
        "category": "1f", "block_id": None, "route": "standard",
        "framing": "abstract", "weave_due": False,
        "matched_row_id": "1f-t1", "collision_path": None,
    }
    state = _kr_state(psychoed_serve=serve_payload)
    mock_repo_cls = MagicMock()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", mock_repo_cls):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    mock_repo_cls.assert_not_called()
    assert "content_hash" not in result["psychoed_serve"]
    assert result["psychoed_blocks_served"] == []
    assert result["psychoed_family_exposures"] == ["understanding_anxiety"]


# ─────────────────────────── (b) menu-after-weave passthrough ───────────────────────────

@pytest.mark.asyncio
async def test_menu_after_weave_no_db_no_appends(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    state = _kr_state(
        skill_match_method="psychoed_menu_after_weave",
        psychoed_blocks_served=["1f-b1"],
        psychoed_family_exposures=["understanding_anxiety"],
    )
    mock_repo_cls = MagicMock()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", mock_repo_cls):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    mock_repo_cls.assert_not_called()
    assert result["knowledge_passages"] == []
    assert result["knowledge_abstain"] is False
    assert result["knowledge_source"] == "psychoed_store"
    assert "psychoed_serve" not in result
    assert "psychoed_blocks_served" not in result   # no payload -> nothing to append
    assert "psychoed_family_exposures" not in result


# ─────────────────────────── (c) outcome-2: semantic backstop, fail-to-personal ───────────────────────────

@pytest.mark.asyncio
async def test_outcome2_backstop_fires_on_psychoed_top_passage(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    top = KnowledgePassage(text="depression content leaked into RAG", source_id="3c-b4",
                            citation="", relevance_score=0.91)
    mock_result = KnowledgeResult(passages=[top], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    payload = result["psychoed_serve"]
    assert payload["category"] == "3c"
    assert payload["block_id"] == "3c-b4"
    assert payload["route"] == "standard"
    assert payload["framing"] == "personal"          # fail-to-personal
    assert payload["weave_due"] is True               # 3c manifest declares safety_weave
    assert payload["collision_path"] == "semantic_backstop"
    assert payload["matched_row_id"] is None
    assert payload["content_hash"] == psy_store.block_sha256("3c-b4")

    assert result["psychoed_active_category"] == "3c"
    assert result["psychoed_delivery_shape"] == "answer_first"
    assert result["psychoed_framing"] == "personal"
    assert result["psychoed_weave_pending"] is True
    assert result["psychoed_weave_fired"] is True
    assert result["psychoed_matched_row_id"] is None
    assert result["psychoed_collision_path"] == "semantic_backstop"
    assert result["psychoed_blocks_served"] == ["3c-b4"]
    assert result["psychoed_family_exposures"] == ["understanding_depression"]

    # L4 quarantine: the only passage WAS the served block -> stripped to empty.
    assert result["knowledge_passages"] == []


@pytest.mark.asyncio
async def test_outcome2_does_not_fire_when_result_abstains(monkeypatch):
    """A psychoed-id top passage that arrives on an abstained result must not trigger the
    backstop (abstain means the retrieval itself judged the match too weak)."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    top = KnowledgePassage(text="weak match", source_id="3c-b4", citation="", relevance_score=0.1)
    mock_result = KnowledgeResult(passages=[top], abstain=True)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    assert "psychoed_serve" not in result
    # L4 quarantine still strips the psychoed passage even though the backstop didn't fire.
    assert result["knowledge_passages"] == []
    assert result["knowledge_abstain"] is True


@pytest.mark.asyncio
async def test_outcome2_suppressed_mid_active_skill(monkeypatch):
    """Reviewer finding (HIGH, controller-adjudicated): spec §2.1 item 2 requires mid-skill
    suppression parity with the resolver -- a backstop firing while a skill is already active
    would set psychoed_weave_pending and feed the user's NEXT skill-continuation reply into the
    weave evaluator (spurious crisis-escalation risk). active_skill_id set -> no backstop, but
    the L4 quarantine still strips the psychoed passage and normal RAG continues unaffected."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    top = KnowledgePassage(text="depression content leaked into RAG", source_id="3c-b4",
                            citation="", relevance_score=0.91)
    mock_result = KnowledgeResult(passages=[top], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state(active_skill_id="box_breathing")

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    psychoed_keys = [k for k in result if k.startswith("psychoed_")]
    assert psychoed_keys == [], f"backstop must not fire mid-active-skill: {psychoed_keys}"
    # L4 quarantine is unchanged -- still strips the psychoed passage even though the
    # backstop is suppressed.
    assert result["knowledge_passages"] == []


@pytest.mark.asyncio
async def test_outcome2_suppressed_on_acute_distress(monkeypatch):
    """Reviewer finding (HIGH, controller-adjudicated): spec §2.2 requires outcome-2 to run the
    IDENTICAL Classifier A check as outcome-1 -- no emission path may skip it. An acute-distress
    message co-occurring with a psychoed-id top passage must not get a backstop serve (fail-to-
    acute takes precedence), but the passage is still quarantined out of knowledge_passages."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    top = KnowledgePassage(text="depression content leaked into RAG", source_id="3c-b4",
                            citation="", relevance_score=0.91)
    mock_result = KnowledgeResult(passages=[top], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state(message_en="I can't breathe right now what is anxiety")

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    psychoed_keys = [k for k in result if k.startswith("psychoed_")]
    assert psychoed_keys == [], f"backstop must not fire on acute distress: {psychoed_keys}"
    assert result["knowledge_passages"] == []


@pytest.mark.asyncio
async def test_outcome2_suppressed_on_non_english_turn(monkeypatch):
    """Controller checkpoint fix (spec §3.7/§7.3): EN-only pathway entry applies to the outcome-2
    backstop too -- an AR turn whose top RAG passage happens to be a psychoed block must not get
    an unsolicited backstop serve (a downstream translate-out of the EN block would be ungraded
    machine-translated clinical copy). Quarantine still strips the passage regardless of language."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    top = KnowledgePassage(text="depression content leaked into RAG", source_id="3c-b4",
                            citation="", relevance_score=0.91)
    mock_result = KnowledgeResult(passages=[top], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state(detected_language="ar", raw_message="ما هو الاكتئاب")

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    psychoed_keys = [k for k in result if k.startswith("psychoed_")]
    assert psychoed_keys == [], f"backstop must not fire on a non-English turn: {psychoed_keys}"
    # L4 quarantine is unchanged -- still strips the psychoed passage regardless of language.
    assert result["knowledge_passages"] == []


# ─────────────────────────── (d) L4 quarantine only (psychoed block ranked 2nd) ───────────────────────────

@pytest.mark.asyncio
async def test_quarantine_strips_psychoed_block_ranked_second_no_backstop(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    normal = KnowledgePassage(text="CBT is evidence-based.", source_id="cbt-001-en",
                               citation="Beck (1979)", relevance_score=0.85)
    psychoed_leak = KnowledgePassage(text="depression content leaked into RAG", source_id="3c-b4",
                                      citation="", relevance_score=0.5)
    mock_result = KnowledgeResult(passages=[normal, psychoed_leak], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    assert "psychoed_serve" not in result   # top passage wasn't psychoed -> no backstop
    assert result["knowledge_passages"] == [normal.to_dict()]   # normal passage survives, block stripped


# ─────────────────────────── (e) flag OFF: byte-identical to control ───────────────────────────

@pytest.mark.asyncio
async def test_flag_off_byte_identical_to_control(monkeypatch):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", False)
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult

    mock_passage = KnowledgePassage(text="CBT is evidence-based.", source_id="cbt-001-en",
                                     citation="Beck (1979)", relevance_score=0.85)
    mock_result = KnowledgeResult(passages=[mock_passage], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state()

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    assert result == {
        "knowledge_passages": [mock_passage.to_dict()],
        "knowledge_abstain": False,
        "knowledge_source": "node_6",
        "knowledge_query_raw": mock_result.query_raw,
        "knowledge_query_searched": mock_result.query_searched,
        "knowledge_top_similarity": mock_result.top_similarity,
        "path": state["path"] + ["knowledge_retrieve"],
    }
    psychoed_keys = [k for k in result if k.startswith("psychoed_")]
    assert psychoed_keys == [], f"psychoed keys leaked with the flag off: {psychoed_keys}"


@pytest.mark.asyncio
async def test_flag_off_serve_payload_in_state_is_ignored(monkeypatch):
    """Even if a psychoed_serve payload is somehow present in state (e.g. stale checkpoint),
    flag OFF means the whole psychoed block is unreachable -- normal DB retrieval still runs."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", False)
    from sage_poc.knowledge.models import KnowledgeResult

    mock_result = KnowledgeResult(passages=[], abstain=True)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = _kr_state(psychoed_serve={"category": "3c", "block_id": "3c-b4"})

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo):
        with patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
            result = await knowledge_retrieve_node(state)

    mock_repo.retrieve.assert_called_once()   # DB path still runs; psychoed guard is unreachable
    assert result["knowledge_source"] == "node_6"
