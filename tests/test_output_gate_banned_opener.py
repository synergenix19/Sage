"""Tests for output_gate banned opener detection and graph-level retry (Fix 2).

The gate detects banned openers in response_en, returns early with
banned_opener_correction set in state, and the graph routes back to
freeflow_respond for regeneration. Generation stays in Node 7.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "It sounds like you're really overwhelmed. What's been hardest?",
        "gate_path": None,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 8,
        "engagement": 4,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "cultural_output_violations": [],
        "path": ["safety_check", "intent_route", "freeflow_respond"],
        "turn_count": 1,
        "turn_number": 1,
        "session_id": None,
        "user_id": None,
        "knowledge_source": "",
        "identity_substitution_rule_id": None,
        "original_response_hash": None,
        "original_response_text": None,
        "prompt_layers": ["persona", "intent"],
        "token_usage": {},
        "resistance_score": None,
        "resistance_history": [],
        "semantic_score": None,
        "skill_match_method": None,
        "new_clinical_flags_turn": [],
        "active_step_id": None,
        "prev_step_id": None,
        "re_escalation_within_monitoring": None,
        "engagement_trajectory": [],
        "distress_trajectory": [],
        "last_turn_at": None,
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
    }
    return {**base, **overrides}


# ---- Pattern constant tests -------------------------------------------------

def test_banned_opener_patterns_constant_exists():
    """_BANNED_OPENER_PATTERNS must be a list of regex strings in output_gate."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_PATTERNS
    assert isinstance(_BANNED_OPENER_PATTERNS, list)
    assert len(_BANNED_OPENER_PATTERNS) >= 3


@pytest.mark.parametrize("banned", [
    "It sounds like you're really overwhelmed right now.",
    "That sounds really tough. I'm here for you.",
    "it seems like things have been hard lately.",
    "That sounds really difficult.",
    "it sounds like this has been a lot.",
])
def test_banned_opener_re_catches_violations(banned):
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert _BANNED_OPENER_RE.match(banned.lstrip()), f"Pattern missed: {banned!r}"


@pytest.mark.parametrize("clean", [
    "The exhaustion you're describing is real. What's been hardest?",
    "Three years of that — what shifted recently?",
    "Carrying all of that and still showing up. What do you need most right now?",
])
def test_banned_opener_re_passes_clean_responses(clean):
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert not _BANNED_OPENER_RE.match(clean.lstrip()), f"Pattern incorrectly flagged: {clean!r}"


# ---- output_gate_node early-return tests ------------------------------------

# #58 MIGRATION: the two tests here previously asserted the old remediation contract
# (correction-flag early return; canned fallback on second violation). That mechanism was
# removed. They are rewritten to the new contract: inline rewrite, and pass-through (NOT canned)
# when the rewrite fails. The remediation contract is owned by test_banned_opener_rewrite.py;
# these stay here only because they exercise output_gate_node end to end via _base_state.

@pytest.mark.asyncio
async def test_banned_opener_is_rewritten_inline():
    """A banned opener on an ordinary turn is fixed by an inline rewrite: no regen, no correction
    flag, no early return. The rewritten reply replaces the original; audit records the rewrite."""
    from sage_poc.nodes import output_gate
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(response_en="It sounds like you're really overwhelmed right now.")

    async def _fake_rewrite(response_en, opener, user_message_en):
        return "You're carrying a great deal right now."

    with patch.object(output_gate, "_rewrite_opener", _fake_rewrite), \
         patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
        result = await output_gate_node(state)

    assert result.get("response") == "You're carrying a great deal right now."
    assert "output_gate_opener_rewritten" in result.get("path", [])
    assert result.get("banned_opener_correction") is None          # mechanism removed
    assert result.get("opener_rewrite", {}).get("applied") is True
    assert result["opener_rewrite"]["model"] and "latency_ms" in result["opener_rewrite"]


@pytest.mark.asyncio
async def test_failed_rewrite_passes_original_through_not_canned():
    """When the rewrite fails/returns empty, the model's REAL reply passes through (a soft opener
    is the lesser evil), NOT the content-free canned fallback. Violation flag is set for audit."""
    from sage_poc.nodes import output_gate
    from sage_poc.nodes.output_gate import output_gate_node, _VETTED_FALLBACK_RESPONSE

    original = "That sounds really tough. I'm here for you."
    state = _base_state(response_en=original)

    async def _fail_rewrite(response_en, opener, user_message_en):
        return ""  # rewrite unavailable

    with patch.object(output_gate, "_rewrite_opener", _fail_rewrite), \
         patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
        result = await output_gate_node(state)

    assert result.get("response") == original                      # the REAL reply, not the placeholder
    assert result.get("response") != _VETTED_FALLBACK_RESPONSE
    assert "output_gate_opener_passthrough" in result.get("path", [])
    assert result.get("banned_opener_violation") is True
    assert result.get("opener_rewrite", {}).get("applied") is False


@pytest.mark.asyncio
async def test_output_gate_resets_retry_count_on_clean_response():
    """On a clean response, output_gate must complete normally and reset banned_opener_retry_count."""
    from sage_poc.nodes.output_gate import output_gate_node

    clean = "The exhaustion you're describing is real. What's been hardest this week?"
    state = _base_state(response_en=clean, banned_opener_retry_count=0)

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    assert result.get("banned_opener_retry_count") == 0
    assert result.get("banned_opener_correction") is None
    assert result.get("response") is not None


@pytest.mark.asyncio
async def test_output_gate_no_banned_check_for_scope_refusal():
    """Hardcoded scope_refusal response is exempt from the banned opener check."""
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(gate_path="scope_refusal", response_en="")

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    assert result.get("response") is not None
    assert result.get("banned_opener_correction") is None


# ---- Graph routing tests ----------------------------------------------------

def test_route_after_output_gate_is_terminal_even_with_correction():
    """#58: the freeflow re-entry was removed; _route_after_output_gate is now terminal (always
    END) even if a stale banned_opener_correction were present. Opener fixes are inline now."""
    from sage_poc.graph import _route_after_output_gate
    from langgraph.graph import END
    state = {
        "banned_opener_correction": "stale value must not re-enter freeflow",
        "banned_opener_retry_count": 1,
    }
    assert _route_after_output_gate(state) == END


def test_route_after_output_gate_returns_end_when_no_correction():
    """_route_after_output_gate must return END when no correction is pending."""
    from sage_poc.graph import _route_after_output_gate
    from langgraph.graph import END
    state = {
        "banned_opener_correction": None,
        "banned_opener_retry_count": 0,
    }
    assert _route_after_output_gate(state) == END


def test_route_after_output_gate_returns_end_after_max_retries():
    """_route_after_output_gate must return END when retry_count > 1 even if correction set."""
    from sage_poc.graph import _route_after_output_gate
    from langgraph.graph import END
    state = {
        "banned_opener_correction": "some correction",
        "banned_opener_retry_count": 2,
    }
    assert _route_after_output_gate(state) == END


# ---- Phase G: Adversarial Pattern Tests ------------------------------------

@pytest.mark.parametrize("variant", [
    "IT SOUNDS LIKE you're overwhelmed.",
    "It Sounds Like you're overwhelmed.",
    "it sounds like you're overwhelmed.",
    "It sounds like...",
])
def test_g1_banned_opener_re_catches_case_variations(variant):
    """G-1: All case variations of banned openers must be caught (case-insensitive flag)."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert _BANNED_OPENER_RE.match(variant.lstrip()), f"Case variation missed: {variant!r}"


@pytest.mark.parametrize("text_with_whitespace", [
    "   It sounds like you're overwhelmed.",
    "\nIt sounds like you're overwhelmed.",
    "\t  It sounds like you're overwhelmed.",
])
def test_g2_banned_opener_re_catches_after_lstrip(text_with_whitespace):
    """G-2: Gate uses response_en.lstrip() before matching; banned openers must still be caught."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    stripped = text_with_whitespace.lstrip()
    assert _BANNED_OPENER_RE.match(stripped), (
        f"After lstrip(), banned opener missed: {text_with_whitespace!r}"
    )


@pytest.mark.parametrize("must_catch", [
    "It sounds like this has been really hard.",
    "That sounds incredibly difficult.",
    "it sounds like a lot to carry.",
])
def test_g3a_banned_opener_re_catches_standard_evasion_variants(must_catch):
    """G-3a: Standard banned opener forms with adjective variation must all be caught."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert _BANNED_OPENER_RE.match(must_catch.lstrip()), f"Evasion variant missed: {must_catch!r}"


@pytest.mark.parametrize("must_pass", [
    "It sounds good to hear you're doing better.",  # 'it sounds' without 'like' — not reflective
    "Does that sound right to you?",                # question form, starts with "Does"
    "That sounds about right.",                     # agreement form — G-3c fix: no longer caught
    "That sounds good.",                            # positive affirmation — not a reflective paraphrase
])
def test_g3b_banned_opener_re_does_not_flag_non_reflective_forms(must_pass):
    """G-3b: Non-reflective forms must not trigger the gate (no false positives).

    'That sounds about right.' is an agreement form. Before the G-3c fix, the broad
    r'that sounds\\b' pattern incorrectly caught it. The narrowed pattern now requires
    an emotional adjective, so agreement and affirmation forms pass correctly.
    """
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert not _BANNED_OPENER_RE.match(must_pass.lstrip()), f"False positive: {must_pass!r}"


def test_g3c_narrowed_pattern_does_not_catch_agreement_forms():
    """G-3c: The narrowed 'that sounds' pattern must pass agreement forms and catch
    reflective emotional openers. Verifies the G-3c false-positive fix:
    r'that sounds (...adjectives...)' replaces the former broad r'that sounds\\b'.
    """
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    # Agreement forms must NOT be caught
    assert not _BANNED_OPENER_RE.match("That sounds about right."), (
        "G-3c fix: 'That sounds about right.' must not be caught by the narrowed pattern"
    )
    assert not _BANNED_OPENER_RE.match("That sounds good."), (
        "G-3c fix: 'That sounds good.' must not be caught"
    )
    # Emotional reflective forms MUST still be caught
    assert _BANNED_OPENER_RE.match("That sounds really tough."), (
        "G-3c fix: reflective form 'That sounds really tough.' must still be caught"
    )
    assert _BANNED_OPENER_RE.match("That sounds incredibly difficult."), (
        "G-3c fix: reflective form 'That sounds incredibly difficult.' must still be caught"
    )
    assert _BANNED_OPENER_RE.match("That sounds hard."), (
        "G-3c fix: reflective form 'That sounds hard.' must still be caught (no intensifier required)"
    )


@pytest.mark.parametrize("arabic_text", [
    "يبدو أنك تمر بوقت صعب",    # "It seems like you're having a hard time" (Arabic)
    "يبدو لي أنك",               # "It seems to me that you..." (Arabic)
])
def test_g4_arabic_responses_not_flagged_by_english_regex(arabic_text):
    """G-4: Arabic text starting with Arabic equivalents of banned openers must NOT trigger
    the English-only regex. Arabic persona stylistics are governed separately.
    """
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    assert not _BANNED_OPENER_RE.match(arabic_text.lstrip()), (
        f"Arabic text incorrectly flagged by English regex: {arabic_text!r}"
    )


@pytest.mark.parametrize("edge_case, description", [
    ("", "empty string"),
    (".", "single punctuation"),
    ("It", "partial word — no boundary"),
    ("It sounds", "partial phrase — missing 'like'"),
])
def test_g5_edge_cases_do_not_crash_and_do_not_match(edge_case, description):
    """G-5: Edge cases must not crash the regex and must not produce false positives."""
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    result = _BANNED_OPENER_RE.match(edge_case.lstrip())
    assert result is None, f"Edge case '{description}' ({edge_case!r}) incorrectly matched"


# ---- Audit write on early return -------------------------------------------

@pytest.mark.asyncio
async def test_rewrite_turn_writes_one_authoritative_audit_and_marks_path():
    """#58 (migrated from the early-return audit tests): with the early return removed, a
    banned-opener turn writes exactly ONE authoritative audit row (the final write) and carries
    the new path marker. Preserves the 'one row per turn' invariant the early-return guarded."""
    from sage_poc.nodes import output_gate
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(response_en="It sounds like you're overwhelmed.", session_id="s-audit")

    async def _fake_rewrite(response_en, opener, user_message_en):
        return "The overwhelm is real right now."

    with patch.object(output_gate, "_rewrite_opener", _fake_rewrite), \
         patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()) as mock_audit:
        result = await output_gate_node(state)

    assert "output_gate_opener_rewritten" in result.get("path", [])
    assert mock_audit.call_count == 1            # one authoritative row, no intermediate early-return write
    assert result.get("opener_rewrite", {}).get("applied") is True


# RETIRED in #58 (mechanism removed; coverage preserved elsewhere):
#  - test_no_intermediate_audit_write_on_early_return: there is no early return now, so "no
#    intermediate write" is structural. The one-row-per-turn invariant it guarded (the 409 race)
#    is asserted by test_rewrite_turn_writes_one_authoritative_audit_and_marks_path above
#    (mock_audit.call_count == 1).
#  - test_banned_opener_violation_true_when_fallback_substituted: the canned-fallback-on-second-
#    violation path no longer exists; a failed rewrite passes the real reply through with
#    banned_opener_violation=True, asserted by test_failed_rewrite_passes_original_through_not_canned.
