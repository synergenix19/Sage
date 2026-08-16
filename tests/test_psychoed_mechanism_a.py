"""Psychoed Mechanism-A: info_request skill-consult before the KB short-circuit.

See docs/superpowers/specs/2026-07-17-psychoed-mechanism-a-design.md. Two coupled sites:
  - skill_select.py's info_request branch now runs the SAME keyword+semantic matching the
    non-info_request path uses; a top match inside INFO_REQUEST_SKILL_CONSULT_SET is
    SELECTED directly (skill_match_method="info_request_skill_consult"). No match, or a
    match outside the set -> the existing KB-bound result, byte-identical to today
    (fail-open by construction).
  - graph.py's _route_after_skill_select keys the info_request->skill_executor diversion
    on skill_match_method (not active_skill_id alone), so a pre-existing active skill never
    changes KB routing.

FLAG-GATED (this update): config.INFO_REQUEST_CONSULT_ENABLED (env SAGE_INFO_REQUEST_CONSULT),
same strict inverted-default idiom as ROUTE_PRECEDENCE_ENABLED (config.py ~170-178) -- only a
literal "true" enables; unset / empty / whitespace / garbage -> OFF. Default OFF means the
consult never runs and this whole mechanism is inert: OFF must be byte-identical to the
pre-consult info_request -> knowledge_retrieve path. All consult-behavior tests below
monkeypatch the flag ON; the dedicated OFF-byte-identical test proves the inert default.

Unit tests drive skill_select_node directly (no LLM). Full-graph tests drive the real
compiled graph with the intent classifier and freeflow responder LLM stubbed offline,
mirroring tests/test_hr_routing.py's / tests/test_medical_redflag_guard.py's style (no
network). The 20 in-scope red drives are the layer1_trigger_corpus rows for spec_id in
{§1f, §3c, §6d, S2c} -- the four Mechanism-A categories the design doc scopes the consult
set to. §4a (Mechanism B) and §7c (independent matching gap, routed to the clinician
packet) are deliberately excluded, per the design doc's scope boundaries section.
"""
import importlib
import json
import pathlib

import pytest

import sage_poc.config as config
from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.skills.info_request_consult_set import INFO_REQUEST_SKILL_CONSULT_SET


# ─────────────────────── SAGE_INFO_REQUEST_CONSULT kill-switch ───────────────────────

def test_info_request_consult_enabled_default_off_with_no_env_set():
    assert config.INFO_REQUEST_CONSULT_ENABLED is False


def test_info_request_consult_strict_idiom_only_literal_true_enables(monkeypatch):
    # Values that must NOT enable the flag, including truthy-looking garbage and the
    # Railway empty-string env-injection case.
    for off_value in ("1", "yes", "", "false", "on", "  ", "truex"):
        monkeypatch.setenv("SAGE_INFO_REQUEST_CONSULT", off_value)
        importlib.reload(config)
        assert config.INFO_REQUEST_CONSULT_ENABLED is False, repr(off_value)

    for on_value in ("true", "TRUE", " true ", "True"):
        monkeypatch.setenv("SAGE_INFO_REQUEST_CONSULT", on_value)
        importlib.reload(config)
        assert config.INFO_REQUEST_CONSULT_ENABLED is True, repr(on_value)

    # Restore clean default state for tests that import config afterward.
    monkeypatch.delenv("SAGE_INFO_REQUEST_CONSULT", raising=False)
    importlib.reload(config)
    assert config.INFO_REQUEST_CONSULT_ENABLED is False


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


# ─────────────────────────── Unit tests (skill_select_node) ───────────────────────────

@pytest.mark.asyncio
async def test_info_request_consult_selects_keyword_matched_consult_skill(monkeypatch):
    """'What is anxiety?' keyword-matches psychoed_anxiety's target_presentations
    ('what is anxiety' substring) -- a Tier-1 hit, no semantic tier needed.
    Flag ON: the consult mechanism this test exercises is inert unless enabled."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(message_en="What is anxiety?", primary_intent="info_request")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "psychoed_anxiety"
    assert result["active_step_id"] == "explain"
    assert result["skill_match_method"] == "info_request_skill_consult"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_info_request_consult_selects_semantic_matched_consult_skill(monkeypatch):
    """'Whats the difference between assertive and aggressive' matches no keyword
    substring in assertive_communication's target_presentations -- must fall through to
    Tier 2 (semantic) and still select, proving the consult reuses BOTH tiers, not just
    keyword. Flag ON: required for the consult to run at all."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(
        message_en="Whats the difference between assertive and aggressive",
        primary_intent="info_request",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "assertive_communication"
    assert result["skill_match_method"] == "info_request_skill_consult"


@pytest.mark.asyncio
async def test_info_request_no_match_returns_kb_bound_result_unchanged(monkeypatch):
    """A genuine info-request that matches nothing -> today's KB-bound result: no
    active skill, no skill_match_method. Fail-open, not tuned. Flag ON: proves the
    fail-open behavior holds even with the consult mechanism enabled, not just because
    it never ran."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(
        message_en="What's the crisis helpline number?", primary_intent="info_request"
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["active_step_id"] is None
    assert result["skill_match_method"] is None


@pytest.mark.asyncio
async def test_info_request_match_outside_consult_set_returns_kb_bound_result_unchanged(monkeypatch):
    """'I need to breathe right now' keyword-matches box_breathing (an experiential
    skill, NOT in INFO_REQUEST_SKILL_CONSULT_SET) -- the consult must reject it and fall
    through to KB, exactly as a no-match turn would. Flag ON: required for the consult
    (and thus its INFO_REQUEST_SKILL_CONSULT_SET rejection) to run at all."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(
        message_en="I need to breathe right now", primary_intent="info_request"
    )
    result = await skill_select_node(state)
    assert "box_breathing" not in INFO_REQUEST_SKILL_CONSULT_SET  # the premise holds
    assert result["active_skill_id"] is None
    assert result["active_step_id"] is None
    assert result["skill_match_method"] is None


@pytest.mark.asyncio
async def test_info_request_preexisting_active_skill_id_preserved_on_no_match(monkeypatch):
    """A skill already active when an info_request with no consult match arrives: the
    executor exclusively owns active_skill_id's lifecycle, so skill_select must omit
    the keys entirely (checkpoint preserves them), exactly as today
    (tests/test_skill_select.py::test_info_request_bypasses_crisis_monitoring).
    Flag ON: proves the preservation guard holds even with the consult mechanism
    enabled (it never reaches the consult because active_skill_id is already set)."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(
        message_en="what is the number for the crisis line",
        crisis_state="monitoring",
        primary_intent="info_request",
        active_skill_id="post_crisis_check_in",
        active_step_id="acknowledge_and_check",
    )
    result = await skill_select_node(state)
    assert "active_skill_id" not in result
    assert "active_step_id" not in result
    assert result["skill_match_method"] is None


@pytest.mark.asyncio
async def test_info_request_preexisting_active_skill_id_preserved_even_on_consult_match(monkeypatch):
    """A skill already active when an info_request arrives whose message WOULD
    consult-match: the consult only fires from a clean (no-active-skill) state -- it must
    not hijack an in-progress skill via an incidental factual question mid-session.
    Flag ON: the message here WOULD select psychoed_anxiety if the guard didn't hold,
    so this only proves something with the consult mechanism actually enabled."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(
        message_en="What is anxiety?",
        primary_intent="info_request",
        active_skill_id="box_breathing",
        active_step_id="inhale_hold",
    )
    result = await skill_select_node(state)
    assert "active_skill_id" not in result
    assert "active_step_id" not in result
    assert result["skill_match_method"] is None


# ─────────────────────── Full-graph: 20 in-scope red drives ───────────────────────

_CORPUS = pathlib.Path("tests/fixtures/bot_behaviour_audit/layer1_trigger_corpus.jsonl")
_IN_SCOPE_CATEGORIES = {"§1f", "§3c", "§6d", "S2c"}  # excludes §4a (Mechanism B), §7c (matching gap)


def _load_in_scope_drives() -> list[dict]:
    rows = []
    for line in _CORPUS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("spec_id") in _IN_SCOPE_CATEGORIES:
            rows.append(row)
    return rows


_RED_DRIVES = _load_in_scope_drives()
assert len(_RED_DRIVES) == 20, f"expected 20 in-scope drives (4 categories x 5), got {len(_RED_DRIVES)}"


def _intent_json_info_request(utterance: str) -> str:
    return (
        '{"primary_intent": "info_request", "secondary_intent": null, '
        '"emotional_intensity": 3, "intent_confidence": 0.92}'
    )


def _stub_info_request_intent_and_responder(monkeypatch):
    """Stub the two LLM entry points a consult-selected skill's turn reaches (intent_route's
    classifier, freeflow_respond's responder/tool-loop -- skill_executor routes to
    freeflow_respond same as every other path, per graph.py's skill_executor->freeflow edge)
    so the full graph completes offline. Also stubs skill_executor's completion-criteria and
    resistance-scoring LLM calls (assertive_communication and grief_loss are in
    _LLM_CRITERIA_SKILLS) so those don't attempt network either -- their return values don't
    affect the routing assertions here (skill_match_method/active_skill_id are decided in
    skill_select, upstream of skill_executor)."""
    from unittest.mock import AsyncMock
    from tests.conftest import make_mock_llm

    intent_llm = make_mock_llm([_intent_json_info_request("")])
    responder_llm = make_mock_llm(["Here is some information."])

    monkeypatch.setattr("sage_poc.nodes.intent_route.get_classifier", lambda: intent_llm)
    monkeypatch.setattr("sage_poc.nodes.intent_route.get_fallback_classifier", lambda: intent_llm)
    monkeypatch.setattr("sage_poc.nodes.freeflow_respond.get_responder", lambda: responder_llm)
    monkeypatch.setattr("sage_poc.nodes.freeflow_respond.get_fallback_responder", lambda: responder_llm)
    monkeypatch.setattr(
        "sage_poc.nodes.skill_executor.evaluate_completion_criteria",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
        AsyncMock(return_value=None),
    )


# Honest recovery record (per-category, MEASURED against the real graph + real BGE-M3
# embeddings -- not the design doc's a priori estimate, which guessed §3c/S2c would BOTH
# be partial. Actual: 19/20.
#   §1f (psychoed_anxiety), §6d (assertive_communication/psychoed_anxiety family), and
#   S2c (grief_loss/psychoed_depression family) recover FULLY (5/5 each) -- every drive's
#   top match lands inside INFO_REQUEST_SKILL_CONSULT_SET.
#   §3c (psychoed_depression) recovers PARTIALLY (4/5). The one miss --
#   "Why can't I just snap out of feeling low" -- top-matches behavioral_activation
#   (semantic score 0.549), a real, clinically-adjacent skill that is simply outside the
#   consult set, not a routing failure: the consult mechanism ran, found a match, and
#   correctly declined to select it because it isn't in INFO_REQUEST_SKILL_CONSULT_SET.
#   This is a matching-CONTENT question for the clinician packet (the design doc's
#   §4a/§7c precedent: "a clinical content question routed to the packet, do not rewrite
#   semantic_description to satisfy the router"), not a defect this routing fix owns.
#   This test pins the MEASURED split per category rather than forcing every drive green
#   or reproducing the doc's un-verified guess, per the task's instruction not to fudge a
#   category that isn't clean.

_EXPECTED_FULL_RECOVERY = {"§1f", "§6d", "S2c"}
# The one known, investigated, non-fudged miss in the partial category (§3c).
_KNOWN_CONTENT_GAP_DRIVE = "Why can't I just snap out of feeling low"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_graph_red_drives_reach_consult_skill_or_report_gap(monkeypatch):
    from sage_poc.graph import build_graph

    per_category: dict[str, list[tuple[str, bool]]] = {}
    for row in _RED_DRIVES:
        monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
        _stub_info_request_intent_and_responder(monkeypatch)
        drive = row["utterance"]
        spec_id = row["spec_id"]
        app = build_graph()
        result = await app.ainvoke(
            {"raw_message": drive, "path": []},
            config={"configurable": {"thread_id": f"psychoed-red-{hash((spec_id, drive))}"}},
        )
        reached = (
            result.get("skill_match_method") == "info_request_skill_consult"
            and "skill_executor" in result.get("path", [])
            and "knowledge_retrieve" not in result.get("path", [])
        )
        per_category.setdefault(spec_id, []).append((drive, reached))

    # Per-category assertions -- the honest recovery record, not a blanket pass.
    for spec_id, outcomes in per_category.items():
        recovered = sum(1 for _, ok in outcomes if ok)
        total = len(outcomes)
        if spec_id in _EXPECTED_FULL_RECOVERY:
            assert recovered == total, (
                f"{spec_id} expected FULL recovery ({total}/{total}), got {recovered}/{total}: "
                f"{[(d, ok) for d, ok in outcomes if not ok]}"
            )
        else:
            # §3c: partial recovery, pinned to the MEASURED 4/5 (not a loose ">=1" floor)
            # so a further regression is caught, and the one known miss is the investigated
            # content gap, not a different/new failure.
            assert recovered == total - 1, (
                f"{spec_id} expected PARTIAL recovery (4/5, the investigated content gap), "
                f"got {recovered}/{total}: {[(d, ok) for d, ok in outcomes if not ok]}"
            )
            missed = [d for d, ok in outcomes if not ok]
            assert missed == [_KNOWN_CONTENT_GAP_DRIVE], (
                f"{spec_id}'s miss changed from the investigated content gap -- "
                f"now missing {missed}, investigate before accepting"
            )

    total_recovered = sum(1 for outcomes in per_category.values() for _, ok in outcomes if ok)
    total_drives = sum(len(outcomes) for outcomes in per_category.values())
    print(f"\n[psychoed-mechanism-a] honest recovery: {total_recovered}/{total_drives} "
          f"({', '.join(f'{k}={sum(1 for _, ok in v if ok)}/{len(v)}' for k, v in sorted(per_category.items()))})")


# ─────────────────────── Must-stay-KB over-pull guard (REQUIRED) ───────────────────────

_MUST_STAY_KB = [
    "what's the crisis helpline number?",
    "how does this app work?",
]

# Topic-mention-without-request controls: distress disclosure, NOT an information
# request -- must not be swept into the consult (or into any skill at all via this path).
_TOPIC_MENTION_CONTROLS = [
    "I'm so tired today",
    "I've just been feeling really anxious lately",
]


@pytest.mark.slow
@pytest.mark.parametrize("message", _MUST_STAY_KB)
@pytest.mark.asyncio
async def test_genuine_info_request_stays_kb_full_graph(message, monkeypatch):
    """The fail-open proof: a genuine info-request matches no consult skill and must
    reach knowledge_retrieve, never skill_executor -- byte-identical to pre-fix behavior.
    Flag ON: proves the fail-open guard holds with the consult mechanism enabled, not
    just because it's off by default (that is covered separately, without the flag)."""
    from sage_poc.graph import build_graph

    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    _stub_info_request_intent_and_responder(monkeypatch)
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": message, "path": []},
        config={"configurable": {"thread_id": f"psychoed-guard-{hash(message)}"}},
    )
    assert result.get("skill_match_method") != "info_request_skill_consult", message
    assert "knowledge_retrieve" in result.get("path", []), message
    assert "skill_executor" not in result.get("path", []), message
    assert result.get("active_skill_id") not in INFO_REQUEST_SKILL_CONSULT_SET, message


@pytest.mark.slow
@pytest.mark.parametrize("message", _MUST_STAY_KB)
@pytest.mark.asyncio
async def test_genuine_info_request_stays_kb_unit(message, monkeypatch):
    """Same guard, direct skill_select_node call -- pins the unit-level mechanism the
    full-graph test above depends on. Flag ON, same rationale as the full-graph guard."""
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(message_en=message, primary_intent="info_request")
    result = await skill_select_node(state)
    assert result["skill_match_method"] != "info_request_skill_consult"
    assert result["active_skill_id"] is None


@pytest.mark.parametrize("message", _TOPIC_MENTION_CONTROLS)
@pytest.mark.asyncio
async def test_topic_mention_without_request_stays_off_consult_unit(message):
    """Bare distress disclosure classified as general_chat (not info_request) never
    reaches the info_request branch at all -- consult is scoped strictly to primary_intent
    == 'info_request', never touched for general_chat."""
    state = _ss_state(message_en=message, primary_intent="general_chat")
    result = await skill_select_node(state)
    assert result.get("skill_match_method") != "info_request_skill_consult"


# ─────────────────── OFF-byte-identical: default (flag OFF) inert proof ───────────────────
# config.INFO_REQUEST_CONSULT_ENABLED default-OFF is asserted above; these tests do NOT
# monkeypatch the flag, so they run against the real default. "What is anxiety?" is the
# same §1f drive that test_info_request_consult_selects_keyword_matched_consult_skill proves
# WOULD select psychoed_anxiety when the flag is ON -- here, OFF, it must fall through to
# the unchanged KB-bound result, proving the gate (not the message) controls the outcome.

def test_info_request_consult_flag_off_by_default_in_this_test_process():
    # Guards the two tests below against a leaked/mutated flag state from another test
    # or fixture in the same process (monkeypatch reverts automatically, but this makes
    # the OFF-byte-identical proof self-checking rather than assuming isolation held).
    assert config.INFO_REQUEST_CONSULT_ENABLED is False


@pytest.mark.asyncio
async def test_info_request_consult_off_by_default_falls_through_to_kb_bound_result_unit():
    """§1f drive that matches psychoed_anxiety when the flag is ON: with the flag at its
    default (OFF), the consult must never run -- today's KB-bound result, unchanged."""
    state = _ss_state(message_en="What is anxiety?", primary_intent="info_request")
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["active_step_id"] is None
    assert result["skill_match_method"] is None


@pytest.mark.slow
@pytest.mark.asyncio
async def test_info_request_consult_off_by_default_routes_to_knowledge_retrieve_full_graph(monkeypatch):
    """Same §1f drive through the real compiled graph with the flag at its default (OFF):
    must reach knowledge_retrieve, never skill_executor -- byte-identical to the pre-consult
    info_request -> knowledge_retrieve path (today's shipped behavior)."""
    from sage_poc.graph import build_graph

    _stub_info_request_intent_and_responder(monkeypatch)
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": "What is anxiety?", "path": []},
        config={"configurable": {"thread_id": "psychoed-off-byte-identical"}},
    )
    assert result.get("skill_match_method") != "info_request_skill_consult"
    assert "knowledge_retrieve" in result.get("path", [])
    assert "skill_executor" not in result.get("path", [])
    assert result.get("active_skill_id") not in INFO_REQUEST_SKILL_CONSULT_SET
