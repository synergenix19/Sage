# tests/test_cultural_overrides_cross_concern.py
#
# Phase C cross-concern tests for cultural_overrides + schema conformance.
#
# C-1: stale_skill_id set, active_skill_id=None — overrides NOT injected
# C-2: output_gate cultural_output evaluation targets response_en, not system prompt
# C-3: crisis_state=monitoring + active skill — overrides ARE injected
# C-4: primary_intent=info_request, active_skill_id=None — overrides NOT injected

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sage_poc.prompts.composer import compose_prompt
from sage_poc.skills.schema import Skill, SkillStep


# ── Composer test helpers ─────────────────────────────────────────────────────

def _no_rules_mock():
    r = MagicMock()
    r.actions = []
    return r


def _make_state(**overrides):
    base = {
        "raw_message": "I'm doing a bit better",
        "detected_language": "en",
        "message_en": "I'm doing a bit better",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "none", "s7_result": None, "s7_method": None,
        "distress_trajectory": [], "code_switching": False,
        "primary_intent": "skill_continuation", "secondary_intent": None,
        "intent_confidence": 0.9, "emotional_intensity": 4, "engagement": 6,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "skill_match_method": None, "semantic_score": None,
        "escalation_triggered": None, "gate_path": None, "rule_fired": None,
        "stale_skill_id": None, "re_escalation_within_monitoring": None,
        "response_en": None, "response": None, "path": [],
        "turn_count": 1, "conversation_history": [],
        "prompt_layers": [], "token_usage": {},
        "knowledge_passages": None, "knowledge_abstain": False,
        "knowledge_source": None,
    }
    return {**base, **overrides}


def _skill_with_overrides() -> Skill:
    return Skill(
        skill_id="post_crisis_check_in",
        skill_name="Post-Crisis Check-In",
        skill_type="check_in",
        evidence_base="Clinical protocol",
        target_presentations=["post_crisis"],
        semantic_description="",
        steps=[SkillStep(
            step_id="s1",
            goal="Confirm safety",
            technique="Open check-in",
            tone="warm",
            examples=["How are you feeling right now?"],
            contraindications="",
            completion_criteria="",
        )],
        step_policy=[],
        escalation_matrix={"L1": "Exit gracefully"},
        cultural_overrides={
            "islamic_relief_language": "Mirror Islamic relief expressions warmly.",
            "shame_help_seeking": "Frame help-seeking as courage, not weakness.",
        },
    )


# ── C-1: Stale-skill scenario ─────────────────────────────────────────────────

def test_c1_cultural_overrides_not_injected_when_stale_skill_set():
    """
    When active_skill_id is None (stale session cleared it) but stale_skill_id
    is set, no cultural_overrides block is injected. The injection gate is
    active_skill_id; stale_skill_id is only used for re-entry prompts.
    """
    state = _make_state(active_skill_id=None, stale_skill_id="post_crisis_check_in")
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str, (
        "cultural_overrides must not be injected when active_skill_id is None, "
        "even if stale_skill_id is set"
    )
    assert "cultural_skill_overrides" not in layers


# ── C-2: output_gate targets response_en, not system prompt ──────────────────

@pytest.mark.asyncio
async def test_c2_output_gate_cultural_evaluation_targets_response_en():
    """
    output_gate evaluates the CUO-* rules against response_en (the LLM output),
    not the system prompt that contains cultural_overrides. The rules_engine call
    in output_gate must receive response_text = state["response_en"].
    """
    from sage_poc.nodes.output_gate import output_gate_node

    clean_response = "That sounds like real progress. How are you feeling now?"
    state = {
        "gate_path": None,
        "path": [],
        "detected_language": "en",
        "message_en": "I think I'm doing better",
        "response_en": clean_response,
        "is_safe": True,
        "crisis_state": "monitoring",
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "turn_count": 1,
        "conversation_summary": None,
        "session_id": "sess-c2-test",
        "user_id": "user-c2-test",
        "active_skill_id": "post_crisis_check_in",
        "active_step_id": None,
        "executed_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "emotional_intensity": 4,
        "engagement": 6,
        "s7_result": None,
        "s7_method": None,
        "third_party_crisis": False,
        "escalation_triggered": None,
        "turn_number": 1,
    }

    captured_contexts: list[dict] = []

    def spy_evaluate(category, context):
        if category == "cultural_output":
            captured_contexts.append(context)
        mock_result = MagicMock()
        mock_result.fired = []
        return mock_result

    with (
        patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()),
        patch("sage_poc.nodes.output_gate.rules_engine.evaluate", side_effect=spy_evaluate),
    ):
        await output_gate_node(state)

    assert len(captured_contexts) == 1, "cultural_output must be evaluated exactly once on standard path"
    ctx = captured_contexts[0]
    assert ctx["response_text"] == clean_response, (
        f"cultural_output must receive response_text=response_en; got: {ctx['response_text']!r}"
    )
    # Confirm system-prompt content (cultural_overrides) is NOT leaked into the evaluation context
    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in ctx["response_text"]
    assert "Mirror Islamic" not in ctx.get("response_text", "")


# ── C-3: Crisis monitoring does not suppress overrides ───────────────────────

def test_c3_cultural_overrides_injected_during_crisis_monitoring():
    """
    When crisis_state='monitoring' and active_skill_id is set (e.g., post_crisis_check_in),
    the composer still injects cultural_overrides. The injection gate only checks
    active_skill_id; crisis_state is irrelevant to it.
    """
    skill = _skill_with_overrides()
    state = _make_state(
        active_skill_id="post_crisis_check_in",
        crisis_state="monitoring",
    )
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
    ):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" in system_str, (
        "cultural_overrides must be injected even when crisis_state='monitoring'"
    )
    assert "Mirror Islamic relief expressions warmly." in system_str
    assert "cultural_skill_overrides" in layers


# ── C-4: info_request with no active skill → no overrides ────────────────────

def test_c4_cultural_overrides_not_injected_for_info_request():
    """
    When primary_intent='info_request' and active_skill_id is None (freeflow,
    no skill active), cultural_overrides are not injected. No skill is in
    context, so there are no skill-specific cultural rules to apply.
    """
    state = _make_state(
        active_skill_id=None,
        primary_intent="info_request",
    )
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str, (
        "cultural_overrides must not be injected for info_request with no active skill"
    )
    assert "cultural_skill_overrides" not in layers
