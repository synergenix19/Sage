# tests/test_cultural_output.py
import pytest
from sage_poc.rules.loader import reload_all
from sage_poc.rules import engine as rules_engine
from sage_poc.rules.engine import _eval_cultural_output
from sage_poc.rules.schemas import CulturalOutputRule


@pytest.fixture(autouse=True)
def fresh_rules():
    reload_all()
    yield
    reload_all()


def test_cultural_output_rule_schema_validates():
    """CulturalOutputRule must validate a well-formed rule dict."""
    rule = CulturalOutputRule.model_validate({
        "rule_id": "TEST-CUO-001",
        "category": "cultural_output",
        "effective_date": "2026-05-21",
        "check_type": "blocklist",
        "condition_type": "always",
        "patterns": ["bad phrase"],
        "action": {"type": "audit_warn", "severity": "medium", "message": "test"},
    })
    assert rule.rule_id == "TEST-CUO-001"
    assert rule.check_type == "blocklist"
    assert rule.condition_type == "always"


def test_cultural_output_rule_schema_allowlist_required():
    """CulturalOutputRule must accept allowlist_required check_type."""
    rule = CulturalOutputRule.model_validate({
        "rule_id": "TEST-CUO-002",
        "category": "cultural_output",
        "effective_date": "2026-05-21",
        "check_type": "allowlist_required",
        "condition_type": "keyword_in_message",
        "condition_keywords": ["allah"],
        "patterns": ["sabr", "allah"],
        "action": {"type": "audit_warn", "severity": "medium", "message": "test"},
    })
    assert rule.check_type == "allowlist_required"
    assert rule.condition_keywords == ["allah"]


def test_evaluate_cultural_output_unknown_category_raises():
    """evaluate() with unknown category must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown rule category"):
        rules_engine.evaluate("nonexistent_category", {})


def test_evaluate_cultural_output_no_violations_on_neutral_input():
    """evaluate('cultural_output', ...) returns empty EvalResult when no rules fire."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds like you are going through a lot right now.",
        "message_en": "I feel overwhelmed by work deadlines",
        "clinical_flags": [],
    })
    assert result.fired == []
    assert result.actions == []


def _make_rule(**kwargs):
    """Build a minimal CulturalOutputRule for unit testing."""
    defaults = {
        "rule_id": "TEST-001",
        "category": "cultural_output",
        "effective_date": "2026-05-21",
        "check_type": "blocklist",
        "condition_type": "always",
        "patterns": ["bad phrase"],
        "action": {"type": "audit_warn", "severity": "medium", "message": "test"},
    }
    defaults.update(kwargs)
    return CulturalOutputRule.model_validate(defaults)


def test_eval_cultural_output_blocklist_fires_when_pattern_in_response():
    rule = _make_rule(check_type="blocklist", condition_type="always", patterns=["bad phrase"])
    result = _eval_cultural_output([rule], {
        "response_text": "This is a bad phrase in the response.",
        "message_en": "anything",
        "clinical_flags": [],
    })
    assert len(result.fired) == 1
    assert result.fired[0].rule_id == "TEST-001"


def test_eval_cultural_output_blocklist_does_not_fire_on_clean_response():
    rule = _make_rule(check_type="blocklist", condition_type="always", patterns=["bad phrase"])
    result = _eval_cultural_output([rule], {
        "response_text": "This is a clean and appropriate response.",
        "message_en": "anything",
        "clinical_flags": [],
    })
    assert result.fired == []


def test_eval_cultural_output_keyword_condition_skips_when_keyword_absent():
    rule = _make_rule(
        check_type="blocklist",
        condition_type="keyword_in_message",
        condition_keywords=["family"],
        patterns=["put yourself first"],
    )
    result = _eval_cultural_output([rule], {
        "response_text": "You should put yourself first always.",
        "message_en": "I feel stressed at work",  # no "family" keyword
        "clinical_flags": [],
    })
    assert result.fired == [], "Rule must not fire when condition keyword absent from message"


def test_eval_cultural_output_flag_present_condition():
    rule = _make_rule(
        check_type="blocklist",
        condition_type="flag_present",
        condition_value="substance_use",
        patterns=["harm reduction"],
    )
    # Flag absent -- must not fire
    result_no_flag = _eval_cultural_output([rule], {
        "response_text": "Try harm reduction strategies.",
        "message_en": "I'm struggling",
        "clinical_flags": [],
    })
    assert result_no_flag.fired == []

    # Flag present -- must fire
    result_with_flag = _eval_cultural_output([rule], {
        "response_text": "Try harm reduction strategies.",
        "message_en": "I'm struggling",
        "clinical_flags": ["substance_use"],
    })
    assert len(result_with_flag.fired) == 1


def test_eval_cultural_output_allowlist_required_fires_when_pattern_absent():
    rule = _make_rule(
        check_type="allowlist_required",
        condition_type="always",
        patterns=["sabr", "tawakkul"],
    )
    result = _eval_cultural_output([rule], {
        "response_text": "That sounds difficult. How are you coping?",
        "message_en": "anything",
        "clinical_flags": [],
    })
    assert len(result.fired) == 1


def test_eval_cultural_output_allowlist_required_does_not_fire_when_pattern_present():
    rule = _make_rule(
        check_type="allowlist_required",
        condition_type="always",
        patterns=["sabr", "tawakkul"],
    )
    result = _eval_cultural_output([rule], {
        "response_text": "The concept of sabr can be helpful here.",
        "message_en": "anything",
        "clinical_flags": [],
    })
    assert result.fired == []


def test_eval_cultural_output_empty_response_returns_no_violations():
    """Empty response_text must never trigger allowlist_required violations."""
    rule = _make_rule(
        check_type="allowlist_required",
        condition_type="always",
        patterns=["sabr"],
    )
    result = _eval_cultural_output([rule], {
        "response_text": "",
        "message_en": "anything",
        "clinical_flags": [],
    })
    assert result.fired == [], (
        "Empty response_text must not trigger allowlist_required -- generation failure, not policy violation"
    )


# ── Task 2: output_gate wiring ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_output_gate_calls_cultural_output_evaluate(monkeypatch):
    """output_gate_node must call rules_engine.evaluate('cultural_output', ...) for standard path."""
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.rules import engine as rules_engine

    calls = []
    original_evaluate = rules_engine.evaluate

    def mock_evaluate(category, context):
        calls.append((category, context))
        return original_evaluate(category, context)

    monkeypatch.setattr(rules_engine, "evaluate", mock_evaluate)

    state = {
        "gate_path": None,
        "detected_language": "en",
        "path": [],
        "response_en": "That makes sense. How are you feeling about it?",
        "message_en": "I feel anxious",
        "clinical_flags": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    await output_gate_node(state)

    cultural_output_calls = [c for c in calls if c[0] == "cultural_output"]
    assert len(cultural_output_calls) == 1, "output_gate_node must call evaluate('cultural_output', ...) once"
    ctx = cultural_output_calls[0][1]
    assert ctx["response_text"] == "That makes sense. How are you feeling about it?"
    assert ctx["message_en"] == "I feel anxious"
    assert ctx["clinical_flags"] == []


@pytest.mark.asyncio
async def test_output_gate_skips_cultural_output_for_scope_refusal(monkeypatch):
    """Scope refusal path must skip cultural output evaluation — fixed response, not LLM-generated."""
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.rules import engine as rules_engine

    calls = []
    original_evaluate = rules_engine.evaluate

    def mock_evaluate(category, context):
        calls.append(category)
        return original_evaluate(category, context)

    monkeypatch.setattr(rules_engine, "evaluate", mock_evaluate)

    state = {
        "gate_path": "scope_refusal",
        "detected_language": "en",
        "path": [],
        "response_en": None,
        "message_en": "diagnose me",
        "clinical_flags": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    await output_gate_node(state)
    assert "cultural_output" not in calls


@pytest.mark.asyncio
async def test_output_gate_returns_cultural_output_violations_in_state():
    """output_gate_node must return cultural_output_violations list in all paths."""
    from sage_poc.nodes.output_gate import output_gate_node

    # Standard path with violation — list must contain rule ID
    result_violation = await output_gate_node({
        "gate_path": None,
        "detected_language": "en",
        "path": [],
        "response_en": "Maybe try dating apps to feel more connected.",
        "message_en": "I feel lonely",
        "clinical_flags": [],
        "turn_count": 0,
        "conversation_history": [],
    })
    assert "cultural_output_violations" in result_violation
    assert "CUO-GC-001" in result_violation["cultural_output_violations"]

    # Scope refusal — must return empty list, not omit the key
    result_refusal = await output_gate_node({
        "gate_path": "scope_refusal",
        "detected_language": "en",
        "path": [],
        "response_en": None,
        "message_en": "diagnose me",
        "clinical_flags": [],
        "turn_count": 0,
        "conversation_history": [],
    })
    assert "cultural_output_violations" in result_refusal
    assert result_refusal["cultural_output_violations"] == []

    # Standard path clean — must return empty list
    result_clean = await output_gate_node({
        "gate_path": None,
        "detected_language": "en",
        "path": [],
        "response_en": "That sounds really difficult. What has been on your mind?",
        "message_en": "I feel overwhelmed",
        "clinical_flags": [],
        "turn_count": 0,
        "conversation_history": [],
    })
    assert "cultural_output_violations" in result_clean
    assert result_clean["cultural_output_violations"] == []


# ── CUO-IS-001 ───────────────────────────────────────────────────────────────

def test_cuo_is_001_fires_when_islamic_input_but_secular_response():
    """CUO-IS-001 must fire when user used 'allah' but response contains no Islamic vocabulary."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "That sounds really difficult. How are you coping with it?",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    fired_ids = [r.rule_id for r in result.fired]
    assert "CUO-IS-001" in fired_ids, (
        "CUO-IS-001 must fire when Islamic keyword in message but no Islamic vocab in response"
    )


def test_cuo_is_001_passes_when_response_mirrors_islamic_vocab():
    """CUO-IS-001 must NOT fire when response includes Islamic vocabulary."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "The concept of sabr can help, patient perseverance through difficulty is honoured.",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    fired_ids = [r.rule_id for r in result.fired]
    assert "CUO-IS-001" not in fired_ids


def test_cuo_is_001_does_not_fire_without_islamic_input():
    """CUO-IS-001 must NOT fire when the user's message has no Islamic keywords."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "That sounds really difficult. How are you coping with it?",
        "message_en": "I feel so alone and hopeless",
        "clinical_flags": [],
    })
    fired_ids = [r.rule_id for r in result.fired]
    assert "CUO-IS-001" not in fired_ids


def test_cuo_is_001_known_limitation_secular_patience_clears_allowlist():
    """Known limitation: secular 'patience' satisfies the allowlist without Islamic framing.

    'patience' is in the patterns list as a proxy for sabr-adjacent content.
    A response like 'It takes patience to work through this' clears the check
    even though it contains no Islamic vocabulary. This is a conscious trade-off
    for POC scope — full resolution requires NLP-level framing detection.
    """
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It takes patience to work through these feelings.",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    fired_ids = [r.rule_id for r in result.fired]
    # Documents current behaviour — CUO-IS-001 does NOT fire because "patience" is in patterns
    assert "CUO-IS-001" not in fired_ids


def test_cuo_is_001_passes_when_response_uses_patient():
    """CUO-IS-001 must NOT fire when response contains 'patient' — common paraphrase of sabr."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Be patient with yourself, this is a test from Allah and you will find your way.",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    assert "CUO-IS-001" not in [r.rule_id for r in result.fired]


def test_cuo_is_001_passes_when_response_uses_trust():
    """CUO-IS-001 must NOT fire when response contains 'trust' — paraphrase of tawakkul."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Trust in His plan, even when it is hard to see the wisdom in it.",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    assert "CUO-IS-001" not in [r.rule_id for r in result.fired]


def test_cuo_is_001_passes_when_response_uses_test():
    """CUO-IS-001 must NOT fire when response contains 'test' — paraphrase of ibtila."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Many people of faith feel this is a test that ultimately strengthens them.",
        "message_en": "I feel like allah has abandoned me",
        "clinical_flags": [],
    })
    assert "CUO-IS-001" not in [r.rule_id for r in result.fired]


# ── CUO-FA-001 ───────────────────────────────────────────────────────────────

def test_cuo_fa_001_fires_when_family_context_and_individualist_response():
    """CUO-FA-001 must fire when family context + individualist dismissal phrase in response."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds hard. Remember, you need to put yourself first and set boundaries with your family.",
        "message_en": "My parents expect me to give up my career",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" in [r.rule_id for r in result.fired], (
        "CUO-FA-001 must fire on 'put yourself first' when family context present"
    )


def test_cuo_fa_001_fires_on_you_owe_them_nothing():
    """CUO-FA-001 must fire on 'you owe them nothing' dismissal."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "You owe them nothing. Your own happiness matters most.",
        "message_en": "I feel guilty about letting my family down",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" in [r.rule_id for r in result.fired]


def test_cuo_fa_001_absent_without_family_context():
    """CUO-FA-001 must NOT fire when message has no family keywords."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "You need to put yourself first and prioritize your own needs.",
        "message_en": "I feel really overwhelmed by work",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" not in [r.rule_id for r in result.fired], (
        "CUO-FA-001 must not fire without family context, even if individualist phrase present"
    )


def test_cuo_fa_001_absent_when_response_is_balanced():
    """CUO-FA-001 must NOT fire when response is balanced (no individualist dismissal phrases)."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds like you're trying to hold a lot of things at once, your own needs and the expectations of people you love.",
        "message_en": "My parents expect me to give up my career",
        "clinical_flags": [],
    })
    assert "CUO-FA-001" not in [r.rule_id for r in result.fired]


# ── CUO-SU-001 ───────────────────────────────────────────────────────────────

def test_cuo_su_001_fires_on_harm_reduction_with_substance_flag():
    """CUO-SU-001 must fire when response contains harm-reduction language + substance_use flag."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Harm reduction strategies like using clean needles can help keep you safer.",
        "message_en": "I've been using drugs to cope",
        "clinical_flags": ["substance_use"],
    })
    assert "CUO-SU-001" in [r.rule_id for r in result.fired], (
        "CUO-SU-001 must fire on 'harm reduction' when substance_use flag active"
    )


def test_cuo_su_001_fires_on_moderate_use_language():
    """CUO-SU-001 must fire on 'moderate use' framing."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Some people find that moderate use of alcohol helps them relax.",
        "message_en": "I drink to deal with stress",
        "clinical_flags": ["substance_use"],
    })
    assert "CUO-SU-001" in [r.rule_id for r in result.fired], (
        "CUO-SU-001 must fire on 'moderate use' when substance_use flag active"
    )


def test_cuo_su_001_absent_without_substance_flag():
    """CUO-SU-001 must NOT fire when substance_use flag is not active."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Harm reduction approaches can sometimes be helpful.",
        "message_en": "I'm struggling",
        "clinical_flags": [],
    })
    assert "CUO-SU-001" not in [r.rule_id for r in result.fired]


def test_cuo_su_001_absent_for_clean_substance_response():
    """CUO-SU-001 must NOT fire when substance_use flag active but response is clean."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "It sounds like the substance is helping you manage some really difficult feelings. What emotions does it help with?",
        "message_en": "I drink to deal with stress",
        "clinical_flags": ["substance_use"],
    })
    assert "CUO-SU-001" not in [r.rule_id for r in result.fired]


# ── CUO-GC-001 ───────────────────────────────────────────────────────────────

def test_cuo_gc_001_fires_on_western_dating_language():
    """CUO-GC-001 must fire when response references dating apps in a UAE cultural context."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "Maybe trying dating apps could help you feel more connected.",
        "message_en": "I feel so lonely",
        "clinical_flags": [],
    })
    assert "CUO-GC-001" in [r.rule_id for r in result.fired]


def test_cuo_gc_001_fires_on_pork_idiom():
    """CUO-GC-001 must fire on pork-related idioms inappropriate in Islamic context."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "You could say he's bringing home the bacon with that job.",
        "message_en": "My husband works very hard",
        "clinical_flags": [],
    })
    assert "CUO-GC-001" in [r.rule_id for r in result.fired]


def test_cuo_gc_001_absent_for_appropriate_response():
    """CUO-GC-001 must NOT fire for culturally appropriate responses."""
    result = rules_engine.evaluate("cultural_output", {
        "response_text": "That sounds really isolating. What kinds of connection have felt meaningful to you in the past?",
        "message_en": "I feel so lonely",
        "clinical_flags": [],
    })
    assert "CUO-GC-001" not in [r.rule_id for r in result.fired]
