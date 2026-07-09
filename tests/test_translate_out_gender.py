"""Live production defect: the Khaleeji translate-out step mis-genders users.

_build_khaleeji_translation_prompt's few-shot exemplars (khaleeji_translation_exemplars.json)
are all masculine-addressed (وياك/عليك/تحس), so every feminine-marked user was addressed in
the wrong grammatical gender. Fix applies the signed "mirror-when-marked, neutral-when-unknown"
policy at the translation hop: marked -> correct gendered Arabic, unmarked -> neutral. This runs
AFTER all safety/cultural/identity gates (they operate on response_en), so it cannot disconnect
any gate -- it only changes the Arabic address forms of the already-approved English content.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sage_poc.language import _build_khaleeji_translation_prompt


# ---- _build_khaleeji_translation_prompt gender directive -------------------------------

def test_feminine_directive_names_correct_forms():
    prompt = _build_khaleeji_translation_prompt("Take your time.", gender="f")
    assert "عليج" in prompt
    assert "وياج" in prompt
    assert "تحسّين" in prompt
    assert "FEMININE" in prompt


def test_masculine_directive_is_explicit():
    prompt = _build_khaleeji_translation_prompt("Take your time.", gender="m")
    assert "MASCULINE" in prompt
    # Masculine forms named explicitly, matching the (currently masculine-only) exemplars.
    assert "عليك" in prompt
    assert "وياك" in prompt


def test_neutral_directive_is_strong_and_positive():
    """The neutral directive must be positive + concrete (name the constructions to USE) and
    explicitly forbid the masculine default -- not merely 'avoid gender'. The weak form let the
    masculine exemplars leak in prod (functional test 2026-07-09: unmarked reply came back
    masculine). Strengthened to match the feminine directive's specificity."""
    prompt = _build_khaleeji_translation_prompt("Take your time.", gender="none")
    assert "gender-free" in prompt.lower()
    assert "خلنا" in prompt          # collaborative construction named
    assert "ينحل" in prompt          # impersonal/passive named
    assert "أنا هني" in prompt       # first-person presence named
    assert "عليك" in prompt and "إنك" in prompt   # masculine default explicitly forbidden


def test_default_gender_is_none_and_neutral_directive_present():
    """Callers that do not pass gender get the (strong) neutral directive as the safe default."""
    prompt = _build_khaleeji_translation_prompt("Take your time.")
    assert "gender-free" in prompt.lower()


# ---- async_translate_to_arabic threads gender into the prompt --------------------------

@pytest.mark.asyncio
async def test_async_translate_to_arabic_threads_gender_into_prompt():
    import sage_poc.resilience as resilience
    import sage_poc.language as language

    captured = {}

    async def _fake_invoke(llm, messages, **kwargs):
        captured["content"] = messages[0]["content"]
        return "ترجمة"

    with patch.object(resilience, "resilient_invoke", _fake_invoke), \
         patch.object(language, "get_translator", lambda: object()):
        await language.async_translate_to_arabic("Take your time.", gender="f")

    assert "عليج" in captured["content"]


@pytest.mark.asyncio
async def test_async_translate_to_arabic_default_gender_none_unchanged_prompt():
    """Regression guard: omitting gender (existing callers) still produces the neutral
    directive, not a crash and not an accidental masculine/feminine guess."""
    import sage_poc.resilience as resilience
    import sage_poc.language as language

    captured = {}

    async def _fake_invoke(llm, messages, **kwargs):
        captured["content"] = messages[0]["content"]
        return "ترجمة"

    with patch.object(resilience, "resilient_invoke", _fake_invoke), \
         patch.object(language, "get_translator", lambda: object()):
        await language.async_translate_to_arabic("Take your time.")

    assert "neutral" in captured["content"].lower()


# ---- output_gate integration: computes gender from raw_message, passes it through ------

def _gate_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "I can't sleep", "response_en": "Tell me about your sleep.",
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
        "raw_message": "",
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_output_gate_passes_feminine_gender_from_raw_message():
    from sage_poc.nodes.output_gate import output_gate_node

    mock_translate = AsyncMock(return_value="...")
    state = _gate_state(raw_message="أنا تعبانة وحاسة إني مب أنا")

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", mock_translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(state)

    assert mock_translate.await_args.kwargs.get("gender") == "f"


@pytest.mark.asyncio
async def test_output_gate_passes_none_gender_for_unmarked_raw_message():
    from sage_poc.nodes.output_gate import output_gate_node

    mock_translate = AsyncMock(return_value="...")
    state = _gate_state(raw_message="عندي deadline يوم الخميس")

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", mock_translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(state)

    assert mock_translate.await_args.kwargs.get("gender") == "none"


@pytest.mark.asyncio
async def test_output_gate_passes_masculine_gender_from_raw_message():
    from sage_poc.nodes.output_gate import output_gate_node

    mock_translate = AsyncMock(return_value="...")
    state = _gate_state(raw_message="أنا تعبان وما عاد أقدر")

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", mock_translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(state)

    assert mock_translate.await_args.kwargs.get("gender") == "m"


@pytest.mark.asyncio
async def test_output_gate_gender_computed_from_raw_message_not_message_en():
    """Must key off raw_message (raw AR user text), not message_en (translated EN) --
    message_en carries no Arabic grammatical gender marking to detect."""
    from sage_poc.nodes.output_gate import output_gate_node

    mock_translate = AsyncMock(return_value="...")
    # message_en has no Arabic markers at all; raw_message is feminine-marked.
    state = _gate_state(
        message_en="I feel exhausted",
        raw_message="حاسة إني تعبانة",
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])), \
         patch("sage_poc.nodes.output_gate.async_translate_to_arabic", mock_translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(state)

    assert mock_translate.await_args.kwargs.get("gender") == "f"
