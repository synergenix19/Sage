import pytest
from sage_poc.prompts.composer import _select_few_shot_examples, _build_l3_skill_block, _TOTAL_WORD_BUDGET
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


# ---- cultural_overrides injection tests ----

from unittest.mock import MagicMock, patch
from sage_poc.prompts.composer import compose_prompt
from sage_poc.skills.schema import Skill, SkillStep


def _no_rules_mock():
    r = MagicMock()
    r.actions = []
    return r


def _make_composer_state(**overrides):
    base = {
        "raw_message": "I feel better now",
        "detected_language": "en",
        "message_en": "I feel better now",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "monitoring", "s7_result": None, "s7_method": None,
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


def _make_skill_with_overrides(overrides: dict | None = None) -> Skill:
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
        cultural_overrides=overrides if overrides is not None else {
            "islamic_relief_language": "Mirror Islamic relief expressions warmly.",
            "shame_help_seeking": "Frame help-seeking as courage, not weakness.",
        },
    )


def test_cultural_overrides_injected_into_system_when_skill_active():
    skill = _make_skill_with_overrides()
    state = _make_composer_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
    ):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" in system_str
    assert "Mirror Islamic relief expressions warmly." in system_str
    assert "Frame help-seeking as courage, not weakness." in system_str
    assert "cultural_skill_overrides" in layers


def test_cultural_overrides_not_injected_when_no_active_skill():
    state = _make_composer_state(active_skill_id=None)
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str
    assert "cultural_skill_overrides" not in layers


def test_cultural_overrides_empty_dict_not_injected():
    skill = _make_skill_with_overrides(overrides={})
    state = _make_composer_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
    ):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str
    assert "cultural_skill_overrides" not in layers


def test_cultural_overrides_load_failure_does_not_crash_composer():
    state = _make_composer_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", side_effect=FileNotFoundError("missing")),
    ):
        system_str, _, layers = compose_prompt(state)

    assert "cultural_skill_overrides" not in layers


def test_cultural_overrides_budget_exceeded_does_not_append_layer_tag():
    # Build overrides that exceed 200 words
    long_text = "This is a very long cultural override instruction. " * 70  # ~564 words
    skill = _make_skill_with_overrides(overrides={"long_override": long_text})
    state = _make_composer_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules_mock()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
    ):
        system_str, _, layers = compose_prompt(state)

    # Budget exceeded: block NOT injected, layer tag NOT added
    assert "cultural_skill_overrides" not in layers
    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str


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


def test_l1_history_always_includes_newest_turn_even_if_over_budget():
    long_content = " ".join(["word"] * 350)  # 350 words, exceeds budget of 300
    history = [{"role": "user", "content": long_content}]
    block = _build_l1_history_block(history)
    assert block is not None
    assert "word" in block


def test_l1_history_respects_word_budget_for_subsequent_lines():
    long_content = " ".join(["word"] * 90)  # ~90 words × 6 entries = ~540 words > 450 budget
    history = [{"role": "user", "content": long_content} for _ in range(6)]
    block = _build_l1_history_block(history)
    assert block is not None
    line_count = block.count("USER:")
    assert line_count < 6   # some truncation must still occur at base 450-word budget


def test_l1_history_newest_turn_appears_when_budget_tight():
    """After Fix 1: the most recent message in the window survives truncation."""
    # 8 messages × ~57 words each ≈ 456 words > 300-word budget
    # Old iteration: markers 0–4 kept; marker7 (newest) dropped.
    # New iteration: markers 7–3 kept; marker0 (oldest) may be dropped.
    history = []
    for i in range(8):
        filler = " ".join(["filler"] * 54)
        history.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"marker{i} {filler}",
        })
    block = _build_l1_history_block(history)
    assert block is not None
    assert "marker7" in block   # newest must always be present


def test_l1_history_base_budget_is_450():
    """Verify the template's base word_budget is 450 after the increase."""
    from sage_poc.prompts.loader import get_template
    tmpl = get_template("L1_history")
    assert tmpl.word_budget == 450


def test_compose_prompt_l1_budget_flexes_to_600_on_freeflow_turns():
    """L1 gets 600-word flex budget when no skill and no info_request intent."""
    from sage_poc.prompts.composer import _compute_l1_budget
    freeflow_state = _make_state(
        primary_intent="general_chat",
        secondary_intent=None,
        step_instruction=None,
    )
    assert _compute_l1_budget(freeflow_state) == 600


def test_compose_prompt_l1_budget_stays_at_450_when_skill_active():
    """L1 budget does not flex when a skill step is in progress."""
    from sage_poc.prompts.composer import _compute_l1_budget
    skill_state = _make_state(
        primary_intent="skill_continuation",
        secondary_intent=None,
        step_instruction="Invite the user to identify their thought.",
    )
    assert _compute_l1_budget(skill_state) == 450


def test_compose_prompt_l1_budget_stays_at_450_for_info_request_primary():
    """L1 budget does not flex when primary_intent is info_request."""
    from sage_poc.prompts.composer import _compute_l1_budget
    state = _make_state(
        primary_intent="info_request",
        secondary_intent=None,
        step_instruction=None,
    )
    assert _compute_l1_budget(state) == 450


def test_compose_prompt_l1_budget_stays_at_450_for_info_request_secondary():
    """L1 budget does not flex when secondary_intent is info_request."""
    from sage_poc.prompts.composer import _compute_l1_budget
    state = _make_state(
        primary_intent="general_chat",
        secondary_intent="info_request",
        step_instruction=None,
    )
    assert _compute_l1_budget(state) == 450


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
    passages = [{"text": "Anxiety is a feeling of worry or fear.", "source_id": "ax-001", "citation": "APA (2013)"}]
    block = _build_l4_knowledge_block(passages, abstain=False)
    assert "[1]" in block
    assert "Anxiety is a feeling" in block


def test_l4_knowledge_block_includes_abstain_instruction():
    passages = [{"text": "Some snippet.", "source_id": "src-001", "citation": ""}]
    block = _build_l4_knowledge_block(passages, abstain=False)
    assert "not certain" in block


def test_l4_knowledge_block_returns_none_for_empty_passages():
    assert _build_l4_knowledge_block([], abstain=False) is None


def test_l4_knowledge_block_abstain_returns_no_fabricate_instruction():
    block = _build_l4_knowledge_block([], abstain=True)
    assert block is not None
    assert "fabricate" in block.lower()


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
    assert "SUPPORT APPROACH" in user_str
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
        system_str, _, layers = compose_prompt(state)
    assert "clinical_adaptation" in layers
    assert "SUPPORT ADAPTATIONS" in system_str, (
        "Injected adaptation header must say 'SUPPORT ADAPTATIONS', not 'CLINICAL ADAPTATIONS'"
    )
    assert "CLINICAL ADAPTATIONS" not in system_str


def test_compose_prompt_knowledge_layer_fires_for_info_request():
    state = _make_state(
        primary_intent="info_request",
        message_en="what is anxiety",
        knowledge_passages=[
            {"text": "Anxiety is a feeling of worry or fear.", "source_id": "ax-001", "citation": "APA (2013)"}
        ],
        knowledge_abstain=False,
    )
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
        _, user_str, _ = compose_prompt(state)
    assert user_str.endswith("USER: this is my message")


def test_compose_prompt_shrinks_l1_on_overflow():
    long_msg = " ".join(["word"] * 50)
    history = [{"role": "user", "content": long_msg} for _ in range(10)]
    state = _make_state(conversation_history=history)
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        system_str, user_str, layers = compose_prompt(state)
    assert "history" in layers
    total = len(system_str.split()) + len(user_str.split())
    assert total <= _TOTAL_WORD_BUDGET + 100


# ---------------------------------------------------------------------------
# Task 6: Conversation summariser
# ---------------------------------------------------------------------------
from unittest.mock import AsyncMock, patch as async_patch


@pytest.mark.asyncio
async def test_summarise_history_calls_llm_and_returns_string():
    from sage_poc.prompts.summarizer import summarise_history
    mock_llm = AsyncMock()
    with async_patch(
        "sage_poc.prompts.summarizer.resilient_invoke",
        new=AsyncMock(return_value="The user is an expat struggling with job search."),
    ):
        history = [
            {"role": "user", "content": "I moved to Dubai and can't find a job."},
            {"role": "assistant", "content": "That sounds exhausting."},
        ]
        result = await summarise_history(history, llm=mock_llm)
    assert isinstance(result, str)
    assert len(result) > 10


@pytest.mark.asyncio
async def test_summarise_history_passes_full_history_to_llm():
    from sage_poc.prompts.summarizer import summarise_history
    captured_messages = []

    async def capture(llm, messages, **kwargs):
        captured_messages.extend(messages)
        return "Summary text."

    mock_llm = AsyncMock()
    with async_patch("sage_poc.prompts.summarizer.resilient_invoke", new=capture):
        history = [
            {"role": "user", "content": "Turn 1 user content"},
            {"role": "assistant", "content": "Turn 1 assistant content"},
        ]
        await summarise_history(history, llm=mock_llm)

    user_message_content = captured_messages[1]["content"]
    assert "Turn 1 user content" in user_message_content
    assert "Turn 1 assistant content" in user_message_content


# Task 6c: _build_l1_history_block summary integration

def test_l1_history_prepends_summary_when_present():
    """When a conversation_summary exists, it appears before the recent turns."""
    history = [
        {"role": "user", "content": "Turn A"},
        {"role": "assistant", "content": "Turn B"},
    ]
    block = _build_l1_history_block(
        history,
        conversation_summary="The user is an expat who feels isolated.",
    )
    assert block is not None
    assert "The user is an expat who feels isolated." in block
    assert "Turn A" in block
    assert block.index("isolated") < block.index("Turn A")


def test_l1_history_no_summary_prefix_when_summary_is_none():
    history = [{"role": "user", "content": "Hello"}]
    block = _build_l1_history_block(history, conversation_summary=None)
    assert "SUMMARY" not in block


def test_l4_block_uses_knowledge_passages_from_state():
    """When state has knowledge_passages, L4 evidence block includes citation text."""
    from sage_poc.prompts.composer import compose_prompt
    state = {
        "message_en": "what is CBT?",
        "detected_language": "en",
        "raw_message": "what is CBT?",
        "primary_intent": "info_request",
        "secondary_intent": None,
        "clinical_flags": [],
        "emotional_intensity": 4,
        "engagement": 6,
        "active_skill_id": None,
        "step_instruction": None,
        "executed_step_id": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "code_switching": False,
        "crisis_state": "none",
        "third_party_crisis": False,
        "knowledge_passages": [
            {
                "text": "CBT is Cognitive Behavioral Therapy, evidence-based for depression.",
                "source_id": "cbt-001-en",
                "citation": "Beck (1979)",
                "relevance_score": 0.88,
            }
        ],
        "knowledge_abstain": False,
        "knowledge_source": "node_6",
    }
    _, user_str, layers = compose_prompt(state)
    assert "knowledge" in layers
    assert "Beck (1979)" in user_str or "cbt-001-en" in user_str


# ── T3/T5: _FLAG_DESCRIPTIONS lifecycle (composer dead-code and regression) ──

def test_T3_third_party_si_removed_from_flag_descriptions():
    """T3: third_party_si was dead code — it never entered clinical_flags (detection
    path is third_party_crisis, not clinical_flag). It must not appear in
    _FLAG_DESCRIPTIONS after the Task 9 cleanup."""
    from sage_poc.prompts.composer import _FLAG_DESCRIPTIONS
    assert "third_party_si" not in _FLAG_DESCRIPTIONS, (
        "third_party_si must be removed from _FLAG_DESCRIPTIONS — it is never a clinical_flag"
    )


def test_T5_escalating_distress_still_in_flag_descriptions():
    """T5: escalating_distress IS a live signal (computed this turn, injected via extra[]).
    It must remain in _FLAG_DESCRIPTIONS so the L5 prompt layer fires correctly."""
    from sage_poc.prompts.composer import _FLAG_DESCRIPTIONS
    assert "escalating_distress" in _FLAG_DESCRIPTIONS, (
        "escalating_distress must remain in _FLAG_DESCRIPTIONS — it is still a live current-turn signal"
    )


def test_l4_block_injects_abstain_instruction_when_no_passages():
    """When knowledge_abstain is True, L4 injects 'do not fabricate' instruction."""
    from sage_poc.prompts.composer import compose_prompt
    state = {
        "message_en": "what is advanced EMDR?",
        "detected_language": "en",
        "raw_message": "what is advanced EMDR?",
        "primary_intent": "info_request",
        "secondary_intent": None,
        "clinical_flags": [],
        "emotional_intensity": 4,
        "engagement": 6,
        "active_skill_id": None,
        "step_instruction": None,
        "executed_step_id": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "code_switching": False,
        "crisis_state": "none",
        "third_party_crisis": False,
        "knowledge_passages": [],
        "knowledge_abstain": True,
        "knowledge_source": "node_6",
    }
    _, user_str, layers = compose_prompt(state)
    assert "fabricate" in user_str.lower() or "do not invent" in user_str.lower() or "no evidence" in user_str.lower() or "no relevant" in user_str.lower()


# ---- Task 0: cap reduction verification ----

import json
import os

_SKILLS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "src", "sage_poc", "skills"
)
_CAP_WORDS = 200  # must match _CULTURAL_OVERRIDE_BUDGET_WORDS after Task 0


def _block_words(overrides: dict) -> int:
    from sage_poc.prompts.tokens import count_words
    lines = "\n".join(f"- {v}" for v in overrides.values())
    block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{lines}"
    return count_words(block)


def test_all_skills_cultural_overrides_within_cap():
    """Every skill's cultural_overrides must fit within _CULTURAL_OVERRIDE_BUDGET_WORDS.
    Fails with the exact word count and file name for each violation — fix the JSON,
    not the test.
    """
    over_budget = []
    for fname in sorted(os.listdir(_SKILLS_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(_SKILLS_DIR, fname)) as f:
            data = json.load(f)
        overrides = data.get("cultural_overrides") or {}
        if overrides:
            wc = _block_words(overrides)
            if wc > _CAP_WORDS:
                over_budget.append((data["skill_id"], wc))
    assert not over_budget, (
        f"Skills exceed {_CAP_WORDS}-word override cap "
        f"(fix the JSON files, not the constant):\n"
        + "\n".join(f"  {sid}: {wc}w" for sid, wc in over_budget)
    )


# ---- _compute_l1_budget override_words tests ----

from sage_poc.prompts.composer import _compute_l1_budget


def _skill_state(**overrides):
    """State with a skill step active (base L1 = 450)."""
    return _make_composer_state(
        step_instruction="Check how the user is feeling",
        active_skill_id="post_crisis_check_in",
        **overrides,
    )


def _freeflow_state(**overrides):
    """State with no skill or knowledge (base L1 = 600)."""
    return _make_composer_state(
        step_instruction=None,
        active_skill_id=None,
        primary_intent="general_chat",
        **overrides,
    )


def test_compute_l1_budget_unaffected_without_overrides():
    """With no override words, budget is the normal base (450 for skill turn)."""
    assert _compute_l1_budget(_skill_state(), override_words=0) == 450


def test_compute_l1_budget_subtracts_override_words():
    """200-word override on a skill turn: 450 - 200 = 250."""
    assert _compute_l1_budget(_skill_state(), override_words=200) == 250


def test_compute_l1_budget_floors_at_minimum():
    """Hypothetical 445-word override: max(150, 450-445) = 150. Defensive only — unreachable
    on current skills after Task 0 lowers cap to 200w."""
    assert _compute_l1_budget(_skill_state(), override_words=445) == 150


def test_compute_l1_budget_freeflow_base_also_reduced():
    """Freeflow base is 600. 200-word override: 600 - 200 = 400.
    Note: freeflow turns have no active_skill_id so override_words will be 0 in practice.
    This tests the arithmetic in isolation."""
    assert _compute_l1_budget(_freeflow_state(), override_words=200) == 400
