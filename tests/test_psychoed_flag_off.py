"""Task 1 (flag parsing) + Task 3 (state channels) live above. Task 12 (this file's
extension) is the proof layer for the whole Phase 2 mechanism (Tasks 1-11):

  1. Flag-OFF no-op, per node (skill_select/knowledge_retrieve/freeflow_respond), across
     the representative states the earlier task test files already established as clean
     control points: info_request consult, post-crisis auto-select, two-tier keyword
     offer, normal RAG retrieval (a psychoed-block passage must SURVIVE, not be
     quarantined, with the flag off), and freeflow with a stale psychoed_serve in state.
  2. The bare-emotional-words re-pin (spec S7.1 F8 seed; already unit-pinned in
     tests/test_psychoed_resolver.py) repeated THROUGH skill_select_node with the flag ON,
     to pin the INTEGRATED surface, not just the pure resolver function.
  3. Mechanism-A coexistence: the resolver and the info_request consult are two
     independent per-category mechanisms until flip-time retirement (Phase 4) -- a
     category the psychoed flag does NOT cover must still let the consult fire, and a
     category it DOES cover must preempt the consult entirely (Task 8's no-double-claim
     property, exercised here across categories rather than within one).

These are regression pins on already-implemented behavior (Tasks 1-11), not new
mechanism work: every assertion below is expected to pass on first run. A failure here
is a real integration finding, not a red-to-green TDD step -- see the Task 12 report for
the first-run evidence this file's tests were built against.
"""
from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.safety_gate


def _reload_config(monkeypatch, **env):
    for k in ("SAGE_PSYCHOED_PATHWAYS", "SAGE_PSYCHOED_CATEGORIES"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from sage_poc import config
    return importlib.reload(config)


def test_flag_default_off(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False
    assert cfg.PSYCHOED_CATEGORIES == frozenset()
    assert cfg.psychoed_enabled_for("1f") is False


def test_flag_on_with_categories(monkeypatch):
    cfg = _reload_config(monkeypatch, SAGE_PSYCHOED_PATHWAYS="true",
                         SAGE_PSYCHOED_CATEGORIES="1f,3c")
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is True
    assert cfg.PSYCHOED_CATEGORIES == frozenset({"1f", "3c"})
    assert cfg.psychoed_enabled_for("1f") and not cfg.psychoed_enabled_for("s2c")


def test_invalid_category_rejected(monkeypatch):
    cfg = _reload_config(monkeypatch, SAGE_PSYCHOED_PATHWAYS="true",
                         SAGE_PSYCHOED_CATEGORIES="1f,bogus")
    assert cfg.PSYCHOED_CATEGORIES == frozenset({"1f"})  # bogus dropped with a warning, never served


def test_psychoed_channels_declared():
    from sage_poc.state import SageState
    keys = SageState.__annotations__
    for k in ("psychoed_serve", "psychoed_active_category", "psychoed_delivery_shape",
              "psychoed_blocks_served", "psychoed_menu_offered", "psychoed_weave_fired",
              "psychoed_weave_pending", "psychoed_matched_row_id", "psychoed_collision_path",
              "psychoed_framing", "psychoed_family_exposures"):
        assert k in keys, f"undeclared channel: {k}"


# ═══════════════════════════ Task 12: flag-OFF byte-identity + regression pins ═══════════════════════════
#
# Everything below drives the real node functions (not the pure resolver/weave/classifier
# modules already unit-tested in Tasks 4-6) -- the integration surface is what Task 12 exists
# to pin. `_ss_state()` mirrors tests/test_skill_select.py's and
# tests/test_psychoed_skill_select.py's convention exactly (same defaults, same shape).

def _ss_state(**overrides):
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


def _psychoed_keys(result: dict) -> list[str]:
    return [k for k in result if k.startswith("psychoed_")]


# ─────────────────────── 1. Flag-OFF no-op, per node ───────────────────────
# Env genuinely unset (importlib-reload, per this file's own _reload_config pattern) rather
# than monkeypatch.setattr -- proves the DEFAULT (not just a patched attribute) is inert.
# Where a second flag needs to be flipped ON to prove the OTHER mechanism still runs
# unaffected (Mechanism-A's consult), that one flag is monkeypatch.setattr'd on the SAME
# reloaded module object skill_select reads at call time (its local `from sage_poc import
# config` import binds to sage_poc.config, which importlib.reload() mutates in place).

@pytest.mark.asyncio
async def test_flag_off_noop_skill_select_info_request_consult_case(monkeypatch):
    """(a) info_request consult case: Mechanism-A's consult (a DIFFERENT flag,
    INFO_REQUEST_CONSULT_ENABLED) must still fire exactly as it does without the psychoed
    mechanism existing at all -- the psychoed flag being off must not perturb it. skill_match_method
    stays "info_request_skill_consult" (unchanged from Mechanism-A's own test suite)."""
    from sage_poc.nodes.skill_select import skill_select_node

    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False
    monkeypatch.setattr(cfg, "INFO_REQUEST_CONSULT_ENABLED", True)

    state = _ss_state(message_en="What is anxiety?", primary_intent="info_request")
    result = await skill_select_node(state)

    assert result["active_skill_id"] == "psychoed_anxiety"
    assert result["active_step_id"] == "explain"
    assert result["skill_match_method"] == "info_request_skill_consult"
    assert _psychoed_keys(result) == []


@pytest.mark.asyncio
async def test_flag_off_noop_skill_select_post_crisis_case(monkeypatch):
    """(b) post-crisis case: crisis_state == "monitoring" auto-selects post_crisis_check_in,
    unchanged (mirrors tests/test_skill_select.py::test_monitoring_state_always_selects_post_crisis_check_in)."""
    from sage_poc.nodes.skill_select import skill_select_node

    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False

    state = _ss_state(message_en="I feel a bit calmer now", crisis_state="monitoring")
    result = await skill_select_node(state)

    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["skill_match_method"] == "post_crisis_auto_select"
    assert result["active_step_id"] == "acknowledge_and_check"
    assert _psychoed_keys(result) == []


@pytest.mark.asyncio
async def test_flag_off_noop_skill_select_two_tier_keyword_case(monkeypatch):
    """(c) two-tier keyword case: a Tier-1 keyword hit produces an R1 consent offer, unchanged
    (mirrors tests/test_skill_select.py::test_resolved_state_falls_through_to_normal_skill_matching)."""
    from sage_poc.nodes.skill_select import skill_select_node

    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False

    state = _ss_state(message_en="I keep thinking everything is my fault", crisis_state="resolved")
    result = await skill_select_node(state)

    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword_offer"
    assert _psychoed_keys(result) == []


@pytest.mark.asyncio
async def test_flag_off_noop_knowledge_retrieve_passage_not_quarantined(monkeypatch):
    """(d) knowledge_retrieve normal retrieval: a psychoed-block passage (source_id in
    store.block_ids()) must SURVIVE untouched -- the L4 quarantine is itself flag-gated
    (config.PSYCHOED_PATHWAYS_ENABLED), so with the flag off it must never strip anything,
    unlike tests/test_psychoed_knowledge_retrieve.py's quarantine tests (flag ON)."""
    from sage_poc.nodes.knowledge_retrieve import knowledge_retrieve_node
    from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
    from sage_poc.psychoed import store as psy_store

    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False
    assert "3c-b4" in psy_store.block_ids()  # premise: this source_id IS a psychoed block

    top = KnowledgePassage(
        text="depression content that would be quarantined if the flag were on",
        source_id="3c-b4", citation="", relevance_score=0.91,
    )
    mock_result = KnowledgeResult(passages=[top], abstain=False)
    mock_repo = MagicMock()
    mock_repo.retrieve = AsyncMock(return_value=mock_result)
    state = {
        "raw_message": "what is CBT?", "detected_language": "en", "message_en": "what is CBT?",
        "primary_intent": "info_request", "knowledge_passages": [], "knowledge_abstain": False,
        "knowledge_source": "", "path": ["safety_check", "intent_route", "skill_select"],
        "user_id": None, "session_id": None,
    }

    with patch("sage_poc.nodes.knowledge_retrieve.PostgresKnowledgeRepository", return_value=mock_repo), \
         patch("sage_poc.nodes.knowledge_retrieve._get_pool", return_value=MagicMock()):
        result = await knowledge_retrieve_node(state)

    assert result["knowledge_passages"] == [top.to_dict()]  # SURVIVES -- not stripped
    assert result["knowledge_source"] == "node_6"
    assert _psychoed_keys(result) == []


@pytest.mark.asyncio
async def test_flag_off_noop_freeflow_stale_serve_calls_llm(monkeypatch):
    """(e) freeflow with a stale psychoed_serve in state (e.g. a checkpoint persisted before a
    mid-session flag flip) but the flag OFF: the no-LLM serve-transit block is unreachable, so
    the normal LLM path runs and the LLM is actually invoked -- no serve is composed or emitted."""
    from sage_poc.nodes.freeflow_respond import freeflow_respond_node

    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False

    stale_serve = {
        "category": "6d", "block_id": "6d-b1", "route": "standard", "framing": "abstract",
        "weave_due": False, "matched_row_id": "row-42", "collision_path": "clean",
    }
    state = {
        "path": ["safety_check", "intent_route", "skill_select", "knowledge_retrieve"],
        "detected_language": "en",
        "message_en": "why do people get anxious",
        "raw_message": "why do people get anxious",
        "psychoed_serve": stale_serve,
        "skill_match_method": None,
        "psychoed_active_category": None,
    }

    mock_msg = MagicMock()
    mock_msg.content = "This is the LLM-generated reply, not a psychoed serve."
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    with patch("sage_poc.nodes.freeflow_respond._get_prior_context", AsyncMock(return_value="")):
        result = await freeflow_respond_node(state, llm=mock_llm)

    mock_llm.ainvoke.assert_called()  # the LLM path DID run
    assert result["response_en"] == "This is the LLM-generated reply, not a psychoed serve."
    assert "psychoed_serve" not in result
    assert "psychoed_menu_offered" not in result
    assert _psychoed_keys(result) == []


# ─────────────────────── 2. Bare-emotional-words re-pin at the INTEGRATED surface ───────────────────────
# spec S7.1 F8 seed; already unit-pinned at the pure resolver level in
# tests/test_psychoed_resolver.py::test_bare_emotional_words_no_match. Repeated here THROUGH
# skill_select_node with the flag ON (all six categories) to pin the surface a real turn
# actually reaches -- proving no integration wiring between the resolver and skill_select
# reintroduces a match the resolver itself correctly declines.

_ALL_CATEGORIES = frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"})


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["I'm stressed", "I feel depressed", "I feel sad", "I'm anxious"])
async def test_bare_emotional_words_do_not_serve_at_skill_select_surface(message, monkeypatch):
    import sage_poc.config as config
    from sage_poc.nodes.skill_select import skill_select_node

    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", _ALL_CATEGORIES)

    state = _ss_state(message_en=message)
    result = await skill_select_node(state)

    assert "psychoed_serve" not in result, message
    assert result.get("skill_match_method") != "psychoed_resolver", message


# ─────────────────────── 3. Mechanism-A coexistence across categories ───────────────────────
# Task 8's no-double-claim property was proven WITHIN one category (test_psychoed_skill_select.py::
# test_trigger_hit_serves_and_preempts_info_request_consult: "What is anxiety?" is both a 1f
# trigger phrase and a Mechanism-A keyword match, and the resolver wins). This proves the
# complementary, cross-category half of the same property: the psychoed flag is scoped
# PER-CATEGORY (config.PSYCHOED_CATEGORIES), so a category NOT covered by the flag must leave
# the consult mechanism fully operative -- coexistence, not retirement, until Phase 4's flip.
# "What is grief?" is S2c-t1's exact trigger phrase AND keyword-matches Mechanism-A's
# grief_loss consult skill (target_presentations contains "grief") -- the same
# both-mechanisms-would-fire setup as the within-category test, but resolved by category
# enablement instead of resolver-precedence.

@pytest.mark.asyncio
async def test_mechanism_a_coexistence_uncovered_category_lets_consult_fire(monkeypatch):
    """PSYCHOED_CATEGORIES = {"1f"} only -- s2c is NOT enabled, so the resolver finds no
    enabled-category rows for "What is grief?" and returns None; the consult below it in
    skill_select_node's fall-through then fires normally."""
    import sage_poc.config as config
    from sage_poc.nodes.skill_select import skill_select_node

    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"1f"}))
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)

    state = _ss_state(message_en="What is grief?", primary_intent="info_request")
    result = await skill_select_node(state)

    assert "psychoed_serve" not in result
    assert result["skill_match_method"] == "info_request_skill_consult"
    assert result["active_skill_id"] == "grief_loss"


@pytest.mark.asyncio
async def test_mechanism_a_coexistence_covered_category_preempts_consult(monkeypatch):
    """Inverse: PSYCHOED_CATEGORIES = {"s2c"} only -- the SAME message now resolver-matches
    (s2c-t1), so skill_select's top psychoed block returns before the info_request consult
    block is ever reached; the consult never runs (no active_skill_id from it)."""
    import sage_poc.config as config
    from sage_poc.nodes.skill_select import skill_select_node

    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset({"s2c"}))
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)

    state = _ss_state(message_en="What is grief?", primary_intent="info_request")
    result = await skill_select_node(state)

    assert result["skill_match_method"] == "psychoed_resolver"
    assert result["psychoed_serve"]["category"] == "s2c"
    assert result["psychoed_active_category"] == "s2c"
    assert "active_skill_id" not in result  # consult never reached -- no skill activation at all


# ─────────────────────── 4. Weave-pending flag-off safety ───────────────────────
# Documents a deliberate residual: a mid-pathway flag flip (OFF mid-session, with a serve's
# weave question already asked) strands psychoed_weave_pending=True in a persisted checkpoint.
# With the flag off, skill_select's entire psychoed block (including the weave evaluator) is
# unreachable, so this turn is NEVER evaluated as a weave reply -- no escalation, no psychoed
# keys at all, it just falls through to ordinary skill matching. This is safe specifically
# because Node-1 (safety_check) re-screens every turn for crisis signals independent of the
# psychoed pathway -- a genuinely concerning reply to the stranded weave question is still
# caught by the upstream crisis-detection backstop, not orphaned. This test exists to make that
# reliance explicit and pinned, not to imply the weave itself is re-armed once the flag returns.

@pytest.mark.asyncio
async def test_weave_pending_stranded_by_flag_off_is_never_evaluated(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False
    from sage_poc.nodes.skill_select import skill_select_node

    # "kind of, not really" keyword-matches grounding_5_4_3_2_1 (fast keyword path, no BGE-M3
    # semantic call) -- it would ALSO be a PSY-WEAVE-1 contradiction marker if evaluated, which
    # is exactly the point: with the flag off, it never gets that chance.
    state = _ss_state(
        message_en="kind of, not really",
        psychoed_weave_pending=True,
        psychoed_active_category="1f",
    )
    result = await skill_select_node(state)

    assert "psychoed_weave_escalation" not in result
    assert result.get("skill_match_method") != "psychoed_weave_escalation"
    assert _psychoed_keys(result) == []
