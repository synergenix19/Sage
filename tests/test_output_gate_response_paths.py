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
