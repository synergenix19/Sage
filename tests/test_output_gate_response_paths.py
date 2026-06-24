# tests/test_output_gate_response_paths.py
"""T-11: Output gate calibration — verify 4 distinct response paths produce correct output.

v7 Node 8 must route each input category to a distinct, verified response.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(**kwargs):
    """Build a minimal SageState dict for output_gate_node tests."""
    defaults = {
        "gate_path": None,
        "path": [],
        "detected_language": "en",
        "message_en": "Hello",
        "response_en": "Hi there",
        "is_safe": True,
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "turn_count": 0,
        "conversation_summary": None,
        "session_id": "sess-123",
        "user_id": "user-456",
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "emotional_intensity": 5,
        "engagement": 5,
        "s7_result": None,
        "s7_method": None,
        "third_party_crisis": False,
        "escalation_triggered": None,
    }
    return {**defaults, **kwargs}


# ---------------------------------------------------------------------------
# Tests — response content for each path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_refusal_path_returns_hardcoded_response():
    """gate_path='scope_refusal' must return the hardcoded SCOPE_REFUSAL_RESPONSE string."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path="scope_refusal")

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    response = result["response"]
    assert "medical professional" in response or "licensed therapist" in response, (
        f"scope_refusal response must reference medical professional or licensed therapist, got: {response!r}"
    )


@pytest.mark.asyncio
async def test_jailbreak_path_returns_hardcoded_response():
    """gate_path='jailbreak' must return the hardcoded JAILBREAK_RESPONSE string."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path="jailbreak")

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    response = result["response"]
    assert "Sage" in response, (
        f"jailbreak response must contain 'Sage', got: {response!r}"
    )
    assert "wellness companion" in response, (
        f"jailbreak response must contain 'wellness companion', got: {response!r}"
    )


@pytest.mark.asyncio
async def test_standard_path_passes_through_response_en():
    """gate_path=None must pass response_en through unchanged (English, no translation)."""
    from sage_poc.nodes.output_gate import output_gate_node

    expected = "You seem to be carrying a lot right now."
    state = make_state(gate_path=None, response_en=expected)

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert result["response"] == expected, (
        f"Standard path must return response_en unchanged, got: {result['response']!r}"
    )


@pytest.mark.asyncio
async def test_output_gate_writes_latency_ms_to_audit_when_turn_started_at_present():
    """Latency instrumentation: output_gate must derive latency_ms from turn_started_at
    (stamped before ainvoke) and fold it into the session_audit row. Previously NULL in prod
    because nothing ever wrote state['latency_ms']."""
    import time as _time
    from sage_poc.nodes import output_gate as og

    state = make_state(
        gate_path=None,
        response_en="Here is a helpful reply.",
        turn_started_at=_time.monotonic() - 1.5,  # turn began ~1.5s ago
    )
    audit_mock = AsyncMock()
    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.write_session_audit", new=audit_mock),
    ):
        await og.output_gate_node(state)
        await asyncio.sleep(0)  # let the fire-and-forget audit task schedule

    audited = [c.args[0] for c in audit_mock.call_args_list if c.args]
    assert audited, "output_gate must call write_session_audit"
    row = audited[-1]
    assert isinstance(row.get("latency_ms"), int), f"latency_ms must be an int, got {row.get('latency_ms')!r}"
    assert row["latency_ms"] >= 1400, f"latency_ms should reflect ~1.5s elapsed, got {row['latency_ms']}"


@pytest.mark.asyncio
async def test_output_gate_latency_ms_none_safe_without_turn_started_at():
    """No turn_started_at (e.g. a path that didn't go through server.py) must not crash and
    must leave latency_ms unset rather than fabricating a value."""
    from sage_poc.nodes import output_gate as og

    state = make_state(gate_path=None, response_en="Hi")  # no turn_started_at
    audit_mock = AsyncMock()
    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.write_session_audit", new=audit_mock),
    ):
        result = await og.output_gate_node(state)
        await asyncio.sleep(0)

    assert result["response"] == "Hi"
    audited = [c.args[0] for c in audit_mock.call_args_list if c.args]
    assert audited and audited[-1].get("latency_ms") is None


# ---------------------------------------------------------------------------
# G1 guard: directive_posture + live offer -> closing question preserved (Step 4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g1_offer_closing_question_preserved_when_directive_posture_and_offer_live():
    """G1: directive_posture=True + offered_skill_ids set must NOT strip the offer's
    closing question. The question-discipline block must skip _strip_trailing_question
    when an offer is live, so the user sees the offer's closing prompt."""
    from sage_poc.nodes import output_gate as og

    # A response that ends with a question (the offer's closing prompt).
    offer_response = "Here are two options that might help. Would you like to try one?"
    state = make_state(
        gate_path=None,
        response_en=offer_response,
        directive_posture=True,
        offered_skill_ids=["box_breathing", "body_scan"],
    )
    audit_mock = AsyncMock()
    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.write_session_audit", new=audit_mock),
    ):
        result = await og.output_gate_node(state)

    # The closing question must survive intact.
    assert result["response"].endswith("?"), (
        f"G1: offer closing question must not be stripped, got: {result['response']!r}"
    )


@pytest.mark.asyncio
async def test_directive_posture_no_offer_strips_trailing_question():
    """G1 negative: directive_posture=True + NO offered_skill_ids -> strip still fires."""
    from sage_poc.nodes import output_gate as og

    response_with_q = "Here is what I suggest. Does that sound right to you?"
    state = make_state(
        gate_path=None,
        response_en=response_with_q,
        directive_posture=True,
        offered_skill_ids=None,
    )
    audit_mock = AsyncMock()
    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.write_session_audit", new=audit_mock),
    ):
        result = await og.output_gate_node(state)

    assert not result["response"].endswith("?"), (
        f"G1 negative: trailing question should be stripped without an offer, got: {result['response']!r}"
    )


@pytest.mark.asyncio
async def test_crisis_passthrough_path():
    """Crisis response text from crisis_response_node must flow through the standard path unchanged."""
    from sage_poc.nodes.output_gate import output_gate_node

    crisis_text = "I hear you. Please reach out: UAE MoHAP 800 46342."
    state = make_state(gate_path=None, response_en=crisis_text, crisis_state="active")

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert "800 46342" in result["response"], (
        f"Crisis hotline number must be preserved through standard path, got: {result['response']!r}"
    )


# ---------------------------------------------------------------------------
# Tests — gate_path value recorded in return dict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_refusal_gate_path_set_in_return():
    """gate_path='scope_refusal' must be preserved in the returned dict."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path="scope_refusal")

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert result["gate_path"] == "scope_refusal", (
        f"Expected gate_path='scope_refusal' in result, got: {result['gate_path']!r}"
    )


@pytest.mark.asyncio
async def test_jailbreak_gate_path_set_in_return():
    """gate_path='jailbreak' must be preserved in the returned dict."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path="jailbreak")

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert result["gate_path"] == "jailbreak", (
        f"Expected gate_path='jailbreak' in result, got: {result['gate_path']!r}"
    )


@pytest.mark.asyncio
async def test_standard_gate_path_set_as_standard_when_none():
    """When gate_path=None, the returned dict must record gate_path='standard'."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path=None)

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert result["gate_path"] == "standard", (
        f"None gate_path must be normalised to 'standard' in result, got: {result['gate_path']!r}"
    )


# ---------------------------------------------------------------------------
# Tests — cultural_output evaluation gating
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_refusal_skips_cultural_violation_check():
    """scope_refusal path must NOT invoke rules_engine.evaluate with 'cultural_output'."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path="scope_refusal")
    called_categories = []

    def spy_evaluate(category, context):
        called_categories.append(category)
        mock_result = MagicMock()
        mock_result.fired = []
        return mock_result

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", side_effect=spy_evaluate),
    ):
        await output_gate_node(state)

    assert "cultural_output" not in called_categories, (
        "scope_refusal path must not call rules_engine.evaluate('cultural_output', ...)"
    )


@pytest.mark.asyncio
async def test_jailbreak_skips_cultural_violation_check():
    """jailbreak path must NOT invoke rules_engine.evaluate with 'cultural_output'."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path="jailbreak")
    called_categories = []

    def spy_evaluate(category, context):
        called_categories.append(category)
        mock_result = MagicMock()
        mock_result.fired = []
        return mock_result

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", side_effect=spy_evaluate),
    ):
        await output_gate_node(state)

    assert "cultural_output" not in called_categories, (
        "jailbreak path must not call rules_engine.evaluate('cultural_output', ...)"
    )


@pytest.mark.asyncio
async def test_standard_path_evaluates_cultural_violations():
    """Standard (gate_path=None) path must invoke rules_engine.evaluate with 'cultural_output'."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path=None, response_en="Everything will be fine.")
    called_categories = []

    def spy_evaluate(category, context):
        called_categories.append(category)
        mock_result = MagicMock()
        mock_result.fired = []
        return mock_result

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", side_effect=spy_evaluate),
    ):
        await output_gate_node(state)

    assert "cultural_output" in called_categories, (
        "Standard path must call rules_engine.evaluate('cultural_output', ...) exactly once"
    )


# ---------------------------------------------------------------------------
# Tests — hardcoded responses override response_en
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_refusal_overrides_response_en():
    """scope_refusal must return the hardcoded string even when response_en contains other text."""
    from sage_poc.nodes.output_gate import output_gate_node

    bad_response = "some bad response"
    state = make_state(gate_path="scope_refusal", response_en=bad_response)

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert bad_response not in result["response"], (
        f"Hardcoded scope_refusal response must override response_en, "
        f"but found the original text in: {result['response']!r}"
    )


# ---------------------------------------------------------------------------
# Tests — turn_count increment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_turn_count_incremented():
    """output_gate_node must increment turn_count by 1 on every path."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path=None, turn_count=3)

    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)

    assert result["turn_count"] == 4, (
        f"turn_count=3 must become 4 after output_gate_node, got: {result['turn_count']}"
    )


@pytest.mark.asyncio
async def test_output_gate_audit_includes_knowledge_fields(caplog):
    """Audit log must include knowledge_source and passage count when retrieval fired."""
    import logging
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.config import AUDIT_LOG_ENABLED

    if not AUDIT_LOG_ENABLED:
        pytest.skip("AUDIT_LOG_ENABLED is False")

    state = make_state(
        gate_path=None,
        knowledge_source="node_6",
        knowledge_passages=[
            {"text": "CBT is...", "source_id": "cbt-001-en", "citation": "Beck (1979)", "relevance_score": 0.88}
        ],
        knowledge_abstain=False,
    )

    with caplog.at_level(logging.INFO, logger="sage_poc.nodes.output_gate"):
        with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
            await output_gate_node(state)

    assert "knowledge_source" in caplog.text, "Audit log must include knowledge_source"
    assert "node_6" in caplog.text, "Audit log must include the knowledge source value"
    assert "cbt-001-en" in caplog.text, "Audit log must include passage source_id"


# ---------------------------------------------------------------------------
# Tests — CUO-ID-001 identity substitution (Task 7)
# ---------------------------------------------------------------------------

def _make_fired_rule(rule_id, action):
    from unittest.mock import MagicMock
    r = MagicMock()
    r.rule_id = rule_id
    r.version = "1.0.0"
    r.action = action
    return r


@pytest.mark.asyncio
async def test_cuo_id_001_substitute_replaces_response():
    """CUO-ID-001: when LLM says 'mental health coach', output_gate must substitute with canonical wellness statement."""
    from sage_poc.nodes.output_gate import output_gate_node

    coach_response = "I am your mental health coach and I am here to help."
    state = make_state(gate_path=None, response_en=coach_response)

    sub_action = {
        "type": "substitute",
        "substitute_with": "I'm Sage, a wellness companion here to offer emotional support and evidence-based coping tools. That's my role. What's been on your mind today?",
        "severity": "high",
        "message": "Identity claim substituted.",
    }
    fired_rule = _make_fired_rule("CUO-ID-001", sub_action)
    mock_result = MagicMock()
    mock_result.fired = [fired_rule]

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=mock_result),
    ):
        result = await output_gate_node(state)

    assert "wellness companion" in result["response"], (
        f"Response must be substituted with wellness companion statement, got: {result['response']!r}"
    )
    assert "mental health coach" not in result["response"], (
        f"Original identity claim must not appear in final response, got: {result['response']!r}"
    )


@pytest.mark.asyncio
async def test_cuo_id_001_substitute_records_rule_id_and_hash():
    """CUO-ID-001 substitution must record rule_id and sha256 hash of original response for PDPL audit."""
    from sage_poc.nodes.output_gate import output_gate_node

    original = "I am your mental health coach here."
    state = make_state(gate_path=None, response_en=original)

    sub_action = {
        "type": "substitute",
        "substitute_with": "I'm Sage, a wellness companion.",
        "severity": "high",
        "message": "Substituted.",
    }
    fired_rule = _make_fired_rule("CUO-ID-001", sub_action)
    mock_result = MagicMock()
    mock_result.fired = [fired_rule]

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=mock_result),
    ):
        result = await output_gate_node(state)

    assert result["identity_substitution_rule_id"] == "CUO-ID-001", (
        f"identity_substitution_rule_id must be 'CUO-ID-001', got: {result.get('identity_substitution_rule_id')!r}"
    )
    assert result["original_response_hash"] is not None, (
        "original_response_hash must be set when substitution fires"
    )
    assert len(result["original_response_hash"]) == 16, (
        f"original_response_hash must be 16-char sha256 prefix, got: {result['original_response_hash']!r}"
    )


@pytest.mark.asyncio
async def test_no_substitution_leaves_rule_id_and_hash_none():
    """When no substitute rule fires, identity_substitution_rule_id and original_response_hash must be None."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = make_state(gate_path=None, response_en="I hear that things are tough right now.")

    mock_result = MagicMock()
    mock_result.fired = []

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=mock_result),
    ):
        result = await output_gate_node(state)

    assert result["identity_substitution_rule_id"] is None
    assert result["original_response_hash"] is None


def test_wellness_identity_rule_file_loads_and_is_valid():
    """wellness_identity.json must load as a valid CulturalOutputRule and have correct check_type."""
    import json
    from pathlib import Path
    from sage_poc.rules.schemas import CulturalOutputRule

    rule_path = (
        Path(__file__).parent.parent
        / "src" / "sage_poc" / "rules" / "data" / "cultural_output" / "wellness_identity.json"
    )
    data = json.loads(rule_path.read_text())
    rules = [CulturalOutputRule(**r) for r in data["rules"]]
    assert len(rules) == 1
    rule = rules[0]
    assert rule.rule_id == "CUO-ID-001"
    assert rule.check_type == "blocklist"
    assert rule.active is True
    assert rule.action["type"] == "substitute"
    assert "wellness companion" in rule.action["substitute_with"]
    assert "mental health coach" in rule.patterns


# ---------------------------------------------------------------------------
# Task 8: Question-discipline helpers
# ---------------------------------------------------------------------------

def test_limit_to_one_question_collapses_stacked_questions():
    from sage_poc.nodes.output_gate import _limit_to_one_question
    text = ("Where would you place yourself from one to ten? And what could help boost "
            "your confidence a bit more?")
    out = _limit_to_one_question(text)
    assert out.count("?") == 1
    assert "Where would you place yourself" in out


def test_limit_to_one_question_keeps_statements_and_first_question():
    from sage_poc.nodes.output_gate import _limit_to_one_question
    text = "That sounds heavy. What's weighing on you most? Do you feel anxious?"
    out = _limit_to_one_question(text)
    assert out == "That sounds heavy. What's weighing on you most?"


def test_limit_to_one_question_noop_for_single_question():
    from sage_poc.nodes.output_gate import _limit_to_one_question
    text = "That sounds hard. What's been hardest?"
    assert _limit_to_one_question(text) == text


def test_strip_trailing_question_removes_dangling_question():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = ("Prepare a few calm, assertive phrases beforehand. You can set a boundary by "
            "naming when you need a break. How does this sit with you?")
    assert _strip_trailing_question(text).endswith("need a break.")


def test_strip_trailing_question_keeps_question_only_response():
    from sage_poc.nodes.output_gate import _strip_trailing_question
    text = "What feels hardest right now?"
    assert _strip_trailing_question(text) == text


def test_strip_trailing_question_no_catastrophic_backtracking():
    """ReDoS guard: a degenerate reply with many '?' clauses and a non-question tail must not
    trigger catastrophic regex backtracking, which would synchronously freeze the single-replica
    event loop. The strip must return near-instantly, not in seconds. (re holds the GIL during
    matching, so a thread/signal timeout can't preempt it — we measure wall-clock directly. The
    input is calibrated to ~5s on the vulnerable regex, so the assertion fails fast on regression.)"""
    import time
    from sage_poc.nodes.output_gate import _strip_trailing_question
    evil = ("word word? " * 20) + " trailing tail with no terminator"  # many '?'-groups, end-anchor fails
    start = time.perf_counter()
    _strip_trailing_question(evil)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"_strip_trailing_question took {elapsed:.2f}s — catastrophic backtracking"


# ---------------------------------------------------------------------------
# Task 8: Question-discipline node integration tests
# ---------------------------------------------------------------------------

import pytest


@pytest.mark.asyncio
async def test_output_gate_collapses_stacked_questions_on_default_freeflow_turn():
    """Flag-2 permanent guard: a DEFAULT freeflow turn (no crisis_state / step_instruction
    kwargs) MUST collapse stacked questions, so the carve-out can't go silently inert."""
    from sage_poc.nodes import output_gate as og
    state = make_state(
        primary_intent="general_chat",
        directive_posture=False,
        response_en="That's a lot. What's heaviest? And what would help right now?",
    )
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await og.output_gate_node(state)
    assert result["response_en"].count("?") == 1


@pytest.mark.asyncio
async def test_output_gate_strips_trailing_question_on_directive_turn():
    from sage_poc.nodes import output_gate as og
    state = make_state(
        primary_intent="general_chat",
        directive_posture=True,
        response_en="Prepare a few calm, assertive phrases beforehand. How does this sit with you?",
    )
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await og.output_gate_node(state)
    assert "?" not in result["response_en"]
    assert "Prepare a few calm, assertive phrases beforehand." in result["response_en"]


@pytest.mark.asyncio
async def test_question_discipline_skips_monitoring_turn_preserving_safety_question():
    """SAFETY: on a post-crisis monitoring turn, stacked questions must NOT be collapsed -
    a safety question appearing as the 2nd question must survive."""
    from sage_poc.nodes import output_gate as og
    state = make_state(
        primary_intent="general_chat",
        directive_posture=False,
        crisis_state="monitoring",
        response_en="I hear how much pain you're in. What's happening? Are you safe right now?",
    )
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await og.output_gate_node(state)
    assert "Are you safe right now?" in result["response_en"], (
        "safety question was stripped on a monitoring turn -- crisis_state carve-out missing"
    )


@pytest.mark.asyncio
async def test_question_discipline_skips_skill_execution_turn():
    """D1 freeflow-only: a skill-execution turn (step_instruction set) must NOT be disciplined."""
    from sage_poc.nodes import output_gate as og
    state = make_state(
        primary_intent="skill_continuation",
        directive_posture=False,
        step_instruction="Ask the user to recall the situation. What happened? How did you feel?",
        response_en="Let's look at that. What happened? How did you feel?",
    )
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await og.output_gate_node(state)
    assert result["response_en"].count("?") == 2, (
        "discipline ran on a skill-execution turn -- step_instruction guard missing"
    )


def test_crisis_response_bypasses_output_gate_edge():
    """SAFETY: crisis_response routes straight to END, never through output_gate."""
    import sage_poc.graph as g
    import inspect
    src = inspect.getsource(g.build_graph)
    assert 'add_edge("crisis_response", END)' in src, (
        "crisis_response must edge directly to END (bypassing output_gate)"
    )
