"""Integration tests for intent_route_node: LLM response parsing and state output.

These tests mock resilient_invoke to return controlled JSON strings.
They verify that intent_route_node correctly parses the LLM output and
writes all expected fields to state — including secondary_intent (RT-2).

test_routing.py covers the routing functions (_route_after_intent, etc.) with
pre-set state values. These tests are the complementary layer: they prove the
node itself produces the state values that the routing functions rely on.
"""
import pytest
from unittest.mock import AsyncMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "message_en": "I've been feeling down for weeks",
        "detected_language": "en",
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "therapeutic_profile": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "path": ["safety_check"],
    }
    return {**base, **overrides}


@pytest.mark.asyncio
async def test_rt2_secondary_intent_parsed_and_written():
    """RT-2: secondary_intent must be written to state when LLM returns a blended intent."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "new_skill", "secondary_intent": "info_request", '
        '"intent_confidence": 0.87, "emotional_intensity": 6, "engagement": 7}'
    )
    state = _base_state(
        message_en="I've been blaming myself for everything — also, is CBT something that could help?",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "new_skill", (
        f"Expected primary_intent='new_skill', got '{result['primary_intent']}'"
    )
    assert result["secondary_intent"] == "info_request", (
        f"RT-2 FAIL: secondary_intent should be 'info_request', got '{result['secondary_intent']}'"
    )
    assert result["intent_confidence"] == pytest.approx(0.87)
    assert result["emotional_intensity"] == 6
    assert result["engagement"] == 7
    assert "intent_route" in result["path"]


@pytest.mark.asyncio
async def test_secondary_intent_is_none_when_llm_returns_null():
    """When LLM returns secondary_intent: null, state must have secondary_intent=None."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.91, "emotional_intensity": 3, "engagement": 8}'
    )
    state = _base_state(message_en="Hey, how's it going?")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["secondary_intent"] is None


@pytest.mark.asyncio
async def test_intent_route_low_confidence_writes_correct_confidence():
    """When LLM returns low confidence, intent_confidence in state must be < 0.6."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.42, "emotional_intensity": 4, "engagement": 3}'
    )
    state = _base_state(message_en="I don't know... just stuff I guess")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["intent_confidence"] < 0.6, (
        f"Expected intent_confidence < 0.6 for ambiguous message, got {result['intent_confidence']}"
    )
    assert result["intent_confidence"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_intent_route_defaults_to_general_chat_on_malformed_json():
    """Malformed LLM response must not raise — defaults to general_chat with confidence 0.5."""
    from sage_poc.nodes.intent_route import intent_route_node

    state = _base_state(message_en="test message")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value="NOT JSON AT ALL")):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["intent_confidence"] == pytest.approx(0.5)
    assert result["secondary_intent"] is None


@pytest.mark.asyncio
async def test_intent_route_path_appended():
    """intent_route node must append 'intent_route' to the path field."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.9, "emotional_intensity": 5, "engagement": 5}'
    )
    state = _base_state(path=["safety_check"])

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["path"] == ["safety_check", "intent_route"]


def test_intent_system_prompt_does_not_say_mental_health_assistant():
    """INTENT_SYSTEM must not describe the system as 'mental health assistant'.
    Internal framing consistency: matches the public 'wellbeing companion' identity.
    """
    from sage_poc.nodes.intent_route import INTENT_SYSTEM
    assert "mental health assistant" not in INTENT_SYSTEM.lower(), (
        "INTENT_SYSTEM should say 'wellbeing companion app', not 'mental health assistant'"
    )
    assert "wellbeing companion" in INTENT_SYSTEM.lower(), (
        "INTENT_SYSTEM should reference 'wellbeing companion app called Sage'"
    )


# ── Skill-switch intent regression (safety-adjacent) ─────────────────────────
#
# These tests mock resilient_invoke to simulate what the LLM returns, then verify
# intent_route_node writes the correct intent. They do not test the LLM's actual
# classification — that requires a real integration run. They test that:
# (a) the node correctly routes a skill-switch response marked new_skill
# (b) a crisis-marked response from a passive-SI-entangled technique request
#     reaches the state as crisis, not new_skill
# (c) the INTENT_SYSTEM prompt contains the generic mode-switch rule (no enumerated
#     skill names) and the safety carve-out for acceptance-framed harm
#
# The adversarial boundary (does the real LLM correctly classify EN/AR/Arabizi
# acceptance-framed passive-SI entangled with a technique request?) requires a
# real LLM integration run and is documented as a hard gate before Gitex.

@pytest.mark.asyncio
async def test_skill_switch_request_writes_new_skill(self=None):
    """A mocked 'new_skill' response from a skill-switch scenario must produce
    primary_intent='new_skill' in state, routing to skill_select → entry_screen."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "new_skill", "secondary_intent": null, '
        '"intent_confidence": 0.88, "emotional_intensity": 5, "engagement": 7}'
    )
    state = _base_state(
        message_en="let's try a different approach for this",
        active_skill_id="worry_time",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "new_skill", (
        "A skill-switch request must produce new_skill intent so skill_select fires "
        f"and the new skill starts at step 0. Got '{result['primary_intent']}'"
    )


@pytest.mark.asyncio
async def test_arabic_skill_switch_request_writes_new_skill():
    """A mocked 'new_skill' response from an Arabic skill-switch scenario must produce
    primary_intent='new_skill' in state.

    This verifies the node correctly writes the LLM's Arabic-triggered classification.
    Note: this does NOT verify the LLM actually classifies Arabic skill-switch requests
    as new_skill — that requires the real LLM integration run (hard gate before Gitex).
    The routing consequence (new_skill → skill_select → entry_screen) is tested in
    test_routing.py against the _route_after_intent function directly.
    """
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "new_skill", "secondary_intent": null, '
        '"intent_confidence": 0.85, "emotional_intensity": 4, "engagement": 6}'
    )
    state = _base_state(
        message_en="خلنا نجرب شي ثاني",
        active_skill_id="worry_time",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "new_skill", (
        "Arabic skill-switch request (mocked as new_skill) must produce new_skill in state. "
        f"Got '{result['primary_intent']}'. If wrong, node plumbing is broken."
    )


@pytest.mark.asyncio
async def test_acceptance_framed_harm_entangled_with_technique_request_routes_crisis():
    """When acceptance-framed passive-SI language is entangled with a technique request,
    the LLM (simulated here) must return crisis, not new_skill.

    This is the safety carve-out in clause (d): the skill-switch shortcut must yield
    to the safety path. If the LLM returns new_skill for this class, the entry screen
    does NOT protect the user — they get routed into ACT acceptance content.

    The mock simulates the correct LLM behavior. The adversarial case (does the real
    LLM consistently make this call in EN/AR/Arabizi?) is a hard gate integration test.
    """
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "crisis", "secondary_intent": null, '
        '"intent_confidence": 0.91, "emotional_intensity": 9, "engagement": 3}'
    )
    state = _base_state(
        message_en="I want to try acceptance, like make peace with not being here anymore",
        active_skill_id="worry_time",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "crisis", (
        "Acceptance-framed passive-SI entangled with technique request must route to crisis, "
        f"not new_skill. Got '{result['primary_intent']}'. "
        "If wrong, user routes into ACT acceptance content — worst possible destination."
    )


@pytest.mark.asyncio
async def test_arabizi_acceptance_harm_entangled_routes_crisis():
    """Same adversarial class in Arabizi must route to crisis (safety carve-out applies
    regardless of script). Arabizi is the primary at-risk script gap in this system."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "crisis", "secondary_intent": null, '
        '"intent_confidence": 0.89, "emotional_intensity": 9, "engagement": 3}'
    )
    state = _base_state(
        message_en="bidi ajarreb el qabool, a2bal eni ma3 bidi akmal",
        active_skill_id="worry_time",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "crisis", (
        "Arabizi acceptance-framed harm must route to crisis, not new_skill. "
        f"Got '{result['primary_intent']}'. This is the sixth cycle of the Arabic asymmetry."
    )


def test_intent_system_contains_generic_skill_switch_rule_not_enumerated_names():
    """INTENT_SYSTEM must use a generic mode-switch rule for skill_continuation,
    not enumerate specific technique names.

    Enumerated names (try defusion, try acceptance) belong in Node 4 skill JSON
    target_presentations — they are clinician-authored content, not engineer-owned
    classifier vocabulary. Adding them to the intent prompt creates a layering
    violation: the prompt drifts out of sync as skills are added via CMS.
    """
    from sage_poc.nodes.intent_route import INTENT_SYSTEM

    # The rule must be generic (mode switch), not naming specific techniques
    enumerated_names = ["try defusion", "try acceptance", "help me problem solve this", "help me with the what-if"]
    for phrase in enumerated_names:
        assert phrase not in INTENT_SYSTEM, (
            f"INTENT_SYSTEM must not enumerate technique name '{phrase}'. "
            "Use a generic mode-switch rule. Named triggers belong in Node 4 skill JSON."
        )

    # The generic mode-switch concept must be present
    assert "different approach" in INTENT_SYSTEM or "different technique" in INTENT_SYSTEM, (
        "INTENT_SYSTEM must contain a generic mode-switch rule (different approach/technique). "
        "Without this, skill-switch requests default to skill_continuation and bypass entry_screen."
    )


def test_intent_system_contains_safety_carveout_for_acceptance_framed_harm():
    """INTENT_SYSTEM clause (d) must have an explicit safety carve-out for
    technique requests entangled with acceptance-of-non-existence language.

    Without this carve-out, the generic skill-switch rule routes acceptance-framed
    passive-SI into ACT — the worst possible destination for that user class.
    This is the measured safety gap: CRADLE recall 39.4%, Arabic S3 limited coverage.
    """
    from sage_poc.nodes.intent_route import INTENT_SYSTEM

    # The safety carve-out must explicitly name the failure mode
    assert "acceptance-of-non-existence" in INTENT_SYSTEM or "acceptance of non-existence" in INTENT_SYSTEM.lower(), (
        "INTENT_SYSTEM must contain a safety carve-out for acceptance-of-non-existence language. "
        "Without it, technique-switch requests entangled with passive-SI route to new_skill."
    )
    assert "crisis" in INTENT_SYSTEM, (
        "INTENT_SYSTEM must mention crisis routing in the safety carve-out context."
    )


# ── Option A: advice deflection fix (2026-06-07) ─────────────────────────────
#
# These tests guard the general_chat.json exception clause introduced in v1.2.0.
# Intent routing is unchanged (no advice_request category yet — that is Option B).
# The fix lives in the L2 template: the exception clause instructs the LLM to
# provide concrete suggestions when the user returns the conversational floor.
#
# Test is placed here because intent_route is the upstream gate for general_chat.
# The comment documents clearly: if this test fails after Option B activates,
# it is because the routing changed, not because the template regressed.

def test_general_chat_template_contains_exception_clause_for_floor_return():
    """OPTION-A GUARD: general_chat L2 template must contain the floor-return exception.

    When the user says 'I don't know, can you suggest something?', intent_route
    currently routes to general_chat (no advice_request category in INTENT_SYSTEM).
    The fix is in the template: the exception clause tells the LLM to answer its
    own question with concrete suggestions rather than re-asking.

    If this assertion fails: check general_chat.json — the exception clause
    ('Exception: if the user says they do not know...') must be present. This is
    the Option A fix; removing it re-opens the advice deflection bug.

    If this assertion starts failing after Option B activates: the routing change
    in INTENT_SYSTEM may have moved delegation traffic away from general_chat.
    Verify advice_request.json contains the equivalent instruction before removing
    this guard.
    """
    from sage_poc.prompts.composer import _build_l2_intent_block

    block = _build_l2_intent_block("general_chat", intensity=5, secondary_intent=None)

    assert "Exception" in block, (
        "OPTION-A FAIL: general_chat L2 block missing the exception clause. "
        "The LLM will not see the instruction to provide concrete suggestions "
        "when the user returns the conversational floor. Check general_chat.json."
    )
    assert "do not know" in block.lower(), (
        "OPTION-A FAIL: exception clause must address 'do not know' — the "
        "dispreferred-response signal. Check general_chat.json exception wording."
    )
    assert "concrete" in block.lower(), (
        "OPTION-A FAIL: exception clause must instruct 'concrete' suggestions — "
        "not a restatement of the exploratory posture. Check general_chat.json."
    )
