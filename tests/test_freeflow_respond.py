import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sage_poc.nodes.freeflow_respond import compose_prompt, freeflow_respond_node


def _no_rules():
    r = MagicMock()
    r.actions = []
    return r

# Minimal state for testing
_BASE_STATE = {
    "raw_message": "I've been feeling anxious for weeks",
    "detected_language": "en",
    "message_en": "I've been feeling anxious for weeks",
    "is_safe": True, "crisis_flags": [], "clinical_flags": [],
    "crisis_state": "none", "s7_result": None, "s7_method": None,
    "distress_trajectory": [], "code_switching": False,
    "primary_intent": "new_skill", "secondary_intent": None,
    "intent_confidence": 0.9, "emotional_intensity": 7, "engagement": 6,
    "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
    "step_instruction": None, "skill_match_method": None, "semantic_score": None,
    "escalation_triggered": None, "gate_path": None,
    "response_en": None, "response": None,
    "path": ["safety_check", "intent_route"],
    "turn_count": 0, "conversation_history": [],
    "prompt_layers": [], "token_usage": {},
}


def test_compose_prompt_returns_layers():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        _, _, layers = compose_prompt(_BASE_STATE)
    assert "persona" in layers
    assert isinstance(layers, list)
    assert all(isinstance(l, str) for l in layers)


def test_compose_prompt_history_layer():
    state = {**_BASE_STATE, "conversation_history": [
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}
    ]}
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        _, _, layers = compose_prompt(state)
    assert "history" in layers


def test_compose_prompt_skill_instruction_layer():
    state = {**_BASE_STATE, "step_instruction": "Ask the user to name one small worry."}
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        _, _, layers = compose_prompt(state)
    assert "skill_instruction" in layers


def test_compose_prompt_no_skill_instruction_when_absent():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        _, _, layers = compose_prompt(_BASE_STATE)
    assert "skill_instruction" not in layers


def test_freeflow_respond_node_returns_prompt_layers():
    mock_msg = MagicMock()
    mock_msg.content = "That sounds really difficult."
    mock_msg.usage_metadata = {"input_tokens": 200, "output_tokens": 40, "total_tokens": 240}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    result = asyncio.run(freeflow_respond_node(_BASE_STATE, llm=mock_llm))

    assert "prompt_layers" in result
    assert isinstance(result["prompt_layers"], list)
    assert "persona" in result["prompt_layers"]


def test_freeflow_respond_node_returns_token_usage():
    mock_msg = MagicMock()
    mock_msg.content = "That sounds really difficult."
    mock_msg.usage_metadata = {"input_tokens": 200, "output_tokens": 40, "total_tokens": 240}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    result = asyncio.run(freeflow_respond_node(_BASE_STATE, llm=mock_llm))

    assert result["token_usage"] == {"input": 200, "output": 40, "total": 240}


def test_freeflow_respond_node_handles_missing_usage_metadata():
    mock_msg = MagicMock()
    mock_msg.content = "I hear you."
    mock_msg.usage_metadata = None

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_msg)

    result = asyncio.run(freeflow_respond_node(_BASE_STATE, llm=mock_llm))

    assert result["token_usage"] == {"input": 0, "output": 0, "total": 0}


def test_compose_prompt_intent_layer_always_present():
    # L2 per v7 §5.6 is always included regardless of path
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        _, _, layers = compose_prompt(_BASE_STATE)
    assert "intent" in layers


def test_compose_prompt_cultural_layer_tracked():
    # When rules_engine fires a cultural action, the "cultural" layer must appear.
    cultural_result = MagicMock()
    cultural_result.actions = [{"target": "system", "content": "Acknowledge Islamic framing.", "priority": 1}]
    injection_result = MagicMock()
    injection_result.actions = []

    def fake_evaluate(category, _ctx):
        if category == "cultural":
            return cultural_result
        return injection_result

    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=fake_evaluate):
        _, _, layers = compose_prompt(_BASE_STATE)

    assert "cultural" in layers


def test_compose_prompt_clinical_adaptation_layer_tracked():
    # When prompt_injection fires a system-targeted injection, "clinical_adaptation" must appear.
    cultural_result = MagicMock()
    cultural_result.actions = []
    injection_result = MagicMock()
    injection_result.actions = [{"target": "system", "content": "User has disclosed substance use history."}]

    def fake_evaluate(category, _ctx):
        if category == "cultural":
            return cultural_result
        return injection_result

    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=fake_evaluate):
        state = {**_BASE_STATE, "clinical_flags": ["substance_use"]}
        _, _, layers = compose_prompt(state)

    assert "clinical_adaptation" in layers


def test_dialect_mirroring_fires_on_any_arabic_message():
    # CU-DM-001 has empty trigger_keywords (language-only trigger). It must fire
    # on every Arabic turn — including generic messages with no Khaleeji markers —
    # so the LLM always gets "respond in Arabic" framing.
    arabic_state = {
        **_BASE_STATE,
        "raw_message": "فهمت",  # "I understand" — no Khaleeji markers, no keywords
        "detected_language": "ar",
        "message_en": "I understand",
    }
    # Use live rules engine (not mocked) — this tests the actual rule file.
    system_str, _, layers = compose_prompt(arabic_state)
    assert "cultural" in layers, (
        "Cultural layer must fire for Arabic messages even without keyword match. "
        "CU-DM-001 (dialect_mirroring) uses empty trigger_keywords as a language-only trigger."
    )
    assert "Arabic" in system_str or "LANGUAGE" in system_str, (
        "Arabic language instruction must appear in system prompt"
    )
