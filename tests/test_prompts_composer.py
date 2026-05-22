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
