import pytest
from sage_poc.prompts.composer import _select_few_shot_examples, _build_l3_skill_block
from sage_poc.skills.schema import SkillStep


_CBT_STEP = SkillStep(
    step_id="identify_thought",
    goal="Help the user identify and clearly articulate the specific negative thought",
    technique="Socratic questioning",
    technique_description="Ask open questions that help the user surface and name their own thoughts.",
    tone="warm, curious, non-judgmental",
    examples=[
        "What specific thought is going through your mind right now?",
        "When you say you feel like a failure, what exactly are you telling yourself?",
        "Can you put that thought into one sentence, what is the thought saying about you?",
        "وين بالظبط الصوت اللي في بالك الحين؟ شو يقولك؟",
    ],
    contraindications="Do NOT challenge the thought at this step.",
)


def test_select_few_shot_defaults_to_first_two():
    selected = _select_few_shot_examples(_CBT_STEP.examples, language="en", intensity=5)
    assert len(selected) == 2
    assert selected[0] == "What specific thought is going through your mind right now?"


def test_select_few_shot_prefers_arabic_when_language_is_ar():
    selected = _select_few_shot_examples(_CBT_STEP.examples, language="ar", intensity=5)
    arabic_ex = "وين بالظبط الصوت اللي في بالك الحين؟ شو يقولك؟"
    assert arabic_ex in selected
    assert len(selected) == 2


def test_select_few_shot_returns_at_most_two():
    selected = _select_few_shot_examples(_CBT_STEP.examples, language="en", intensity=9)
    assert len(selected) <= 2


def test_select_few_shot_handles_single_example():
    selected = _select_few_shot_examples(["Only one"], language="en", intensity=5)
    assert selected == ["Only one"]


def test_select_few_shot_handles_empty():
    assert _select_few_shot_examples([], language="en", intensity=5) == []


def test_build_l3_skill_block_contains_skill_name():
    block = _build_l3_skill_block("CBT Thought Record", _CBT_STEP, language="en", intensity=5)
    assert "CBT Thought Record" in block


def test_build_l3_skill_block_does_not_contain_raw_goal_label():
    block = _build_l3_skill_block("CBT Thought Record", _CBT_STEP, language="en", intensity=5)
    # P1-4 fix: the old "Goal:/Technique:" form format must NOT appear
    assert "Goal:" not in block
    assert "Technique:" not in block


def test_build_l3_skill_block_contains_do_not_announce():
    block = _build_l3_skill_block("CBT Thought Record", _CBT_STEP, language="en", intensity=5)
    assert "Do NOT announce the technique name" in block


def test_build_l3_skill_block_includes_contraindications():
    block = _build_l3_skill_block("CBT Thought Record", _CBT_STEP, language="en", intensity=5)
    assert "Do NOT challenge the thought at this step." in block


def test_build_l3_skill_block_omits_contraindication_section_when_empty():
    step_no_contra = _CBT_STEP.model_copy(update={"contraindications": ""})
    block = _build_l3_skill_block("CBT Thought Record", step_no_contra, language="en", intensity=5)
    assert "Important:" not in block


def test_build_l3_skill_block_handles_empty_examples():
    step_no_examples = _CBT_STEP.model_copy(update={"examples": []})
    block = _build_l3_skill_block("CBT Thought Record", step_no_examples, language="en", intensity=5)
    assert "CBT Thought Record" in block
    assert "Do NOT announce the technique name" in block


def test_build_l3_skill_block_safe_with_curly_braces_in_goal():
    step_with_braces = _CBT_STEP.model_copy(update={"goal": "Identify {cognitive} patterns"})
    block = _build_l3_skill_block("CBT Thought Record", step_with_braces, language="en", intensity=5)
    assert "{cognitive}" in block  # brace escaped, not interpolated


def test_sanitize_assistant_turn_strips_bold():
    from sage_poc.prompts.composer import _sanitize_assistant_turn
    assert _sanitize_assistant_turn("Hello **world**") == "Hello world"


def test_sanitize_assistant_turn_strips_triple_asterisk():
    from sage_poc.prompts.composer import _sanitize_assistant_turn
    assert _sanitize_assistant_turn("Hello ***world***") == "Hello world"


def test_sanitize_assistant_turn_strips_emoji():
    from sage_poc.prompts.composer import _sanitize_assistant_turn
    result = _sanitize_assistant_turn("Hello \U0001f60a world")
    assert "\U0001f60a" not in result
    assert "Hello" in result


def test_sanitize_assistant_turn_replaces_em_dash():
    from sage_poc.prompts.composer import _sanitize_assistant_turn
    assert _sanitize_assistant_turn("one—two") == "one, two"


from sage_poc.prompts.composer import _build_l0_system_block, _build_l1_history_block


def test_l0_system_block_starts_with_important():
    block = _build_l0_system_block()
    assert block.startswith("IMPORTANT")


def test_l1_history_empty_returns_none():
    assert _build_l1_history_block([]) is None


def test_l1_history_respects_window_size():
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"}
        for i in range(12)
    ]
    block = _build_l1_history_block(history)
    # window_size=8: turns 0-3 are outside the window
    assert "message 3" not in block
    assert "message 11" in block


def test_l1_history_sanitizes_assistant_turns():
    history = [{"role": "assistant", "content": "**bold** and emoji \U0001f60a"}]
    block = _build_l1_history_block(history)
    assert "**" not in block
    assert "\U0001f60a" not in block


def test_l1_history_preserves_user_turns_verbatim():
    history = [{"role": "user", "content": "I feel **really** bad"}]
    block = _build_l1_history_block(history)
    assert "I feel **really** bad" in block


def test_l1_history_safe_with_curly_braces_in_user_message():
    history = [{"role": "user", "content": "My mood is {6/10} today"}]
    block = _build_l1_history_block(history)
    assert block is not None
    assert "{6/10}" in block


def test_l1_history_always_includes_first_line_even_if_over_budget():
    long_content = " ".join(["word"] * 350)  # 350 words, exceeds budget of 300
    history = [{"role": "user", "content": long_content}]
    block = _build_l1_history_block(history)
    assert block is not None
    assert "word" in block


def test_l1_history_respects_word_budget_for_subsequent_lines():
    long_content = " ".join(["word"] * 60)  # ~60 words per message
    history = [{"role": "user", "content": long_content} for _ in range(6)]
    block = _build_l1_history_block(history)
    assert block is not None
    line_count = block.count("USER:")
    assert line_count < 6


from sage_poc.prompts.composer import _build_l2_intent_block


def test_l2_intent_block_contains_intensity():
    block = _build_l2_intent_block("general_chat", intensity=5, secondary_intent=None)
    assert "5/10" in block


def test_l2_intent_block_low_intensity_uses_lighter_guidance():
    block = _build_l2_intent_block("general_chat", intensity=2, secondary_intent=None)
    assert "lighter" in block.lower() or "mild" in block.lower()


def test_l2_intent_block_high_intensity_uses_validation_guidance():
    block = _build_l2_intent_block("general_chat", intensity=8, secondary_intent=None)
    assert "validat" in block.lower() or "distressed" in block.lower()


def test_l2_intent_block_falls_back_gracefully_for_unknown_intent():
    block = _build_l2_intent_block("totally_unknown_intent_xyz", intensity=5, secondary_intent=None)
    assert block is not None
    assert "5/10" in block


def test_l2_intent_block_appends_secondary_intent():
    block = _build_l2_intent_block("general_chat", intensity=5, secondary_intent="info_request")
    assert "info_request" in block


def test_l2_intent_block_mid_intensity_uses_engaged_guidance():
    block = _build_l2_intent_block("general_chat", intensity=5, secondary_intent=None)
    assert "moderately" in block.lower() or "engaged" in block.lower()


from sage_poc.prompts.composer import _build_l4_knowledge_block, _build_l5_user_context_block


def test_l4_knowledge_block_formats_with_citation_marker():
    block = _build_l4_knowledge_block("Anxiety is a feeling of worry or fear.")
    assert "[1]" in block
    assert "Anxiety is a feeling" in block


def test_l4_knowledge_block_includes_abstain_instruction():
    block = _build_l4_knowledge_block("Some snippet.")
    assert "not certain" in block


def test_l4_knowledge_block_returns_none_for_empty_snippet():
    assert _build_l4_knowledge_block(None) is None
    assert _build_l4_knowledge_block("") is None


def test_l5_user_context_returns_none_when_no_relevant_flags():
    result = _build_l5_user_context_block(clinical_flags=[], intensity=5, engagement=5)
    assert result is None


def test_l5_user_context_fires_for_substance_use():
    block = _build_l5_user_context_block(
        clinical_flags=["substance_use"], intensity=5, engagement=6
    )
    assert block is not None
    assert "motivational" in block.lower()


def test_l5_user_context_includes_distress_note_when_escalating():
    block = _build_l5_user_context_block(
        clinical_flags=["escalating_distress"], intensity=8, engagement=4
    )
    assert "elevated" in block.lower() or "multiple turns" in block.lower()


# ---------------------------------------------------------------------------
# Task 8: compose_prompt() integration tests
# ---------------------------------------------------------------------------
from unittest.mock import patch, MagicMock
from sage_poc.prompts.composer import compose_prompt


_BASE_STATE: dict = {
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


def _make_state(**kwargs):
    return {**_BASE_STATE, **kwargs}


def _no_rules():
    cultural = MagicMock(); cultural.actions = []
    injection = MagicMock(); injection.actions = []
    def _eval(cat, _ctx):
        return cultural if cat == "cultural" else injection
    return _eval


def test_compose_prompt_returns_three_tuple():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        result = compose_prompt(_BASE_STATE)
    assert len(result) == 3
    system_str, user_str, layers = result
    assert isinstance(system_str, str)
    assert isinstance(user_str, str)
    assert isinstance(layers, list)


def test_compose_prompt_system_starts_with_important():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        system_str, _, _ = compose_prompt(_BASE_STATE)
    assert system_str.startswith("IMPORTANT")


def test_compose_prompt_layers_always_contains_persona_and_intent():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, _, layers = compose_prompt(_BASE_STATE)
    assert "persona" in layers
    assert "intent" in layers


def test_compose_prompt_no_l3_wrapper_when_no_skill():
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, _, layers = compose_prompt(_BASE_STATE)
    assert "L3_skill_wrapper" not in layers
    assert "skill_instruction" not in layers


def test_compose_prompt_l3_wrapper_fires_for_normal_skill_step():
    state = _make_state(
        active_skill_id="cbt_thought_record",
        executed_step_id="identify_thought",
        step_instruction="Goal: identify_thought.",
    )
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, layers = compose_prompt(state)
    assert "L3_skill_wrapper" in layers
    assert "THERAPEUTIC APPROACH" in user_str
    assert "Goal:" not in user_str  # P1-4 fix: old form format gone


def test_compose_prompt_escalation_uses_raw_step_instruction():
    state = _make_state(
        active_skill_id="cbt_thought_record",
        executed_step_id="identify_thought",
        step_instruction="[L1] Exit skill gracefully if user requests to stop",
        escalation_triggered={"level": "L1", "reason": "stop", "action": "exit_skill"},
    )
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, layers = compose_prompt(state)
    assert "skill_instruction" in layers
    assert "L3_skill_wrapper" not in layers
    assert "[L1]" in user_str


def test_compose_prompt_history_layer_present_when_history_exists():
    state = _make_state(conversation_history=[
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}
    ])
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, _, layers = compose_prompt(state)
    assert "history" in layers


def test_compose_prompt_cultural_layer_tracked():
    cultural = MagicMock()
    cultural.actions = [{"target": "system", "content": "Acknowledge Islamic framing.", "priority": 1}]
    injection = MagicMock(); injection.actions = []
    def _eval(cat, _ctx):
        return cultural if cat == "cultural" else injection
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_eval):
        _, _, layers = compose_prompt(_BASE_STATE)
    assert "cultural" in layers


def test_compose_prompt_clinical_adaptation_layer_tracked():
    cultural = MagicMock(); cultural.actions = []
    injection = MagicMock()
    injection.actions = [{"target": "system", "content": "Substance use disclosure."}]
    def _eval(cat, _ctx):
        return cultural if cat == "cultural" else injection
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_eval):
        state = _make_state(clinical_flags=["substance_use"])
        _, _, layers = compose_prompt(state)
    assert "clinical_adaptation" in layers


def test_compose_prompt_knowledge_layer_fires_for_info_request():
    state = _make_state(primary_intent="info_request", message_en="what is anxiety")
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, layers = compose_prompt(state)
    assert "knowledge" in layers
    assert "[1]" in user_str


def test_compose_prompt_l5_user_context_fires_for_clinical_flags():
    state = _make_state(clinical_flags=["substance_use"])
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, _, layers = compose_prompt(state)
    assert "user_context" in layers


def test_compose_prompt_post_crisis_context_fires_when_monitoring():
    state = _make_state(crisis_state="monitoring", s7_result="RECOVERING")
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, layers = compose_prompt(state)
    assert "post_crisis_context" in layers
    assert "POST-CRISIS CONTEXT" in user_str


def test_compose_prompt_user_message_always_last_in_user_str():
    state = _make_state(message_en="this is my message")
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, _ = compose_prompt(_BASE_STATE)
    assert user_str.endswith("USER: I've been feeling anxious for weeks")
