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
    assert "motivational" in block.lower() or "MI" in block or "substance" in block.lower()


def test_l5_user_context_includes_distress_note_when_escalating():
    block = _build_l5_user_context_block(
        clinical_flags=["escalating_distress"], intensity=8, engagement=4
    )
    assert "elevated" in block.lower() or "multiple turns" in block.lower()
