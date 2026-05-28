# tests/test_rules_integration.py
import pytest
from unittest.mock import patch
from sage_poc.rules.loader import reload_all
from sage_poc.nodes.safety_check import safety_check_node


@pytest.fixture(autouse=True)
def fresh_rules():
    reload_all()
    yield
    reload_all()


def _state(raw_message, clinical_flags=None):
    return {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": raw_message,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": clinical_flags or [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "code_switching": False,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


# ── Crisis detection via Rules Service ──────────────────────────────────────

async def test_safety_check_node_crisis_sets_is_safe_false():
    result = await safety_check_node(_state("I want to die"))
    assert result["is_safe"] is False
    assert len(result["crisis_flags"]) > 0


async def test_safety_check_node_safe_message():
    result = await safety_check_node(_state("I feel anxious today"))
    assert result["is_safe"] is True
    assert result["crisis_flags"] == []


async def test_safety_check_node_negation_no_crisis():
    result = await safety_check_node(_state("I don't want to die"))
    assert result["is_safe"] is True, "Negation should suppress crisis flag"


async def test_safety_check_node_clinical_flag_substance():
    result = await safety_check_node(_state("I've been drinking to cope"))
    assert "substance_use" in result["clinical_flags"]


# ── Clinical flag carry-forward ──────────────────────────────────────────────

async def test_clinical_flags_carry_forward_across_turns():
    """Flags from a prior turn are merged, not erased, by the next turn."""
    state = _state("I'm feeling better today", clinical_flags=["substance_use"])
    result = await safety_check_node(state)
    assert "substance_use" in result["clinical_flags"], (
        "substance_use flag from prior turn must persist into turn 2"
    )


async def test_new_clinical_flag_merges_with_existing():
    """New flag from current turn merges with flag persisted from prior turn."""
    state = _state("I was assaulted and I drink too much", clinical_flags=["substance_use"])
    result = await safety_check_node(state)
    assert "substance_use" in result["clinical_flags"]
    assert "trauma_indicator" in result["clinical_flags"]


async def test_no_duplicate_flags():
    """If the same flag fires again, it appears once, not twice."""
    state = _state("I drink a lot", clinical_flags=["substance_use"])
    result = await safety_check_node(state)
    assert result["clinical_flags"].count("substance_use") == 1


# ── Crisis content ───────────────────────────────────────────────────────────
from sage_poc.rules import engine as rules_engine


def test_crisis_content_en_returns_uae_number():
    result = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "acute"})
    assert result.fired
    text = result.fired[0].action["response_text"]
    assert "800" in text and "46342" in text


def test_crisis_content_ar_returns_arabic_text():
    result = rules_engine.evaluate("crisis_content", {"language": "ar", "crisis_level": "acute"})
    assert result.fired
    text = result.fired[0].action["response_text"]
    assert "أنا" in text or "الإمارات" in text


def test_crisis_content_extended_returns_resource_list():
    result = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "extended"})
    assert result.fired
    resources = result.fired[0].action.get("resources", [])
    names = [r["name"] for r in resources]
    assert any("MoHAP" in n or "Lighthouse" in n for n in names)


# ── freeflow_respond compose_prompt via Rules Service ────────────────────────
from sage_poc.nodes.freeflow_respond import compose_prompt


def _freeflow_state(**overrides):
    base = {
        "raw_message": "I feel anxious",
        "detected_language": "en",
        "message_en": "I feel anxious",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "code_switching": False,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    base.update(overrides)
    return base


def test_islamic_framing_injected_when_faith_keyword_present():
    state = _freeflow_state(message_en="I feel my faith in allah is fading")
    system_str, _, _ = compose_prompt(state)
    assert "ISLAMIC" in system_str or "sabr" in system_str or "ibtila" in system_str


def test_no_islamic_framing_without_faith_keyword():
    state = _freeflow_state(message_en="I feel really anxious today")
    system_str, _, _ = compose_prompt(state)
    assert "ibtila" not in system_str


def test_collectivist_framing_injected_when_family_keyword_present():
    state = _freeflow_state(message_en="My family expects me to be an engineer")
    system_str, _, _ = compose_prompt(state)
    assert "COLLECTIVIST" in system_str or "honour" in system_str or "COLLECTIVIST" in system_str.upper()


def test_clinical_adaptation_substance_injected_from_flag():
    state = _freeflow_state(clinical_flags=["substance_use"])
    system_str, _, _ = compose_prompt(state)
    assert "motivational interviewing" in system_str.lower() or "substance" in system_str.lower()


def test_substance_use_uae_legal_context_injected():
    state = _freeflow_state(clinical_flags=["substance_use"])
    system_str, _, _ = compose_prompt(state)
    assert "legal" in system_str.lower() or "uae" in system_str.lower(), (
        "PI-CF-001 must include UAE legal context for substance use"
    )


@pytest.mark.parametrize("flag,expected_keyword", [
    ("trauma_indicator", "trauma"),
    ("eating_concern", "body"),
    ("medication_mention", "prescriber"),
])
def test_clinical_adaptation_injected_per_flag(flag, expected_keyword):
    state = _freeflow_state(clinical_flags=[flag])
    system_str, _, _ = compose_prompt(state)
    assert expected_keyword in system_str.lower(), (
        f"Expected {expected_keyword!r} in system prompt for {flag}"
    )


def test_collectivist_framing_fires_on_arabic_keyword():
    """Arabic عيب (shame) in raw_message triggers collectivist injection even when
    the English translation does not contain a matching keyword."""
    state = _freeflow_state(
        message_en="I feel pressured",
        raw_message="أحس بالعيب",
        detected_language="ar",
    )
    system_str, _, _ = compose_prompt(state)
    assert "COLLECTIVIST" in system_str, (
        "Collectivist framing must fire on Arabic keyword عيب even without matching English translation"
    )


def test_secondary_intent_dialectical_framing_injected():
    state = _freeflow_state(
        primary_intent="new_skill",
        secondary_intent="info_request",
    )
    _, user_str, _ = compose_prompt(state)
    assert "SECONDARY INTENT" in user_str or "dialectical" in user_str.lower()


def test_no_secondary_intent_framing_when_none():
    state = _freeflow_state(primary_intent="new_skill", secondary_intent=None)
    _, user_str, _ = compose_prompt(state)
    assert "SECONDARY INTENT" not in user_str


def test_domestic_situation_adaptation_injected():
    state = _freeflow_state(clinical_flags=["domestic_situation"])
    system_str, _, _ = compose_prompt(state)
    assert "safety" in system_str.lower() or "800111" in system_str or "domestic" in system_str.lower(), (
        "Domestic situation adaptation must reference safety or UAE resource"
    )


async def test_third_party_crisis_is_safe_does_not_block_session():
    """A third-party crisis report is NOT a crisis for the current user — session continues."""
    state = _state("my friend told me she wants to die")
    with (
        patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
        patch("sage_poc.nodes.safety_check.async_translate_to_english", return_value="my friend told me she wants to die"),
    ):
        result = await safety_check_node(state)
    assert result["is_safe"] is True, "Third-party report must not block the session"
    assert result.get("third_party_crisis") is True, "third_party_crisis flag must be set in state"
    assert "third_party_si" not in result.get("clinical_flags", []), "third_party_si must not enter clinical_flags"


async def test_third_party_overrides_direct_crisis_flag():
    """When both crisis_flag and third_party_crisis fire, third_party wins — is_safe stays True."""
    state = _state("my friend wants to kill herself")
    with (
        patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
        patch("sage_poc.nodes.safety_check.async_translate_to_english", return_value="my friend wants to kill herself"),
    ):
        result = await safety_check_node(state)
    assert result["is_safe"] is True
    assert result.get("third_party_crisis") is True
    assert result["crisis_flags"] == []


def test_third_party_guidance_injected_into_prompt():
    """third_party_crisis=True in state triggers a THIRD-PARTY CONCERN block in the user prompt."""
    state = _freeflow_state(third_party_crisis=True)
    _, user_str, layers = compose_prompt(state)
    assert "third_party_crisis" in layers
    assert "THIRD-PARTY CONCERN" in user_str


def test_state_schema_includes_crisis_fields():
    """SageState TypedDict must declare crisis_state, s7_result, and distress_trajectory."""
    from sage_poc.state import SageState
    import typing
    hints = typing.get_type_hints(SageState)
    assert "crisis_state" in hints, "SageState must include crisis_state"
    assert "s7_result" in hints, "SageState must include s7_result"
    assert "distress_trajectory" in hints, "SageState must include distress_trajectory"
    assert "crisis_occurred_this_session" not in hints, "legacy field must be removed"


def test_post_crisis_session_injection_fires_on_subsequent_safe_turn():
    """After a crisis turn (crisis_state='monitoring'), subsequent safe turns get post-crisis guidance."""
    state = _freeflow_state(
        message_en="I feel a bit better today",
        crisis_state="monitoring",
    )
    system_str, _, _ = compose_prompt(state)
    assert "POST-CRISIS" in system_str, (
        "Post-crisis injection must appear in system prompt when crisis_state='monitoring'"
    )


def test_post_crisis_injection_absent_on_normal_session():
    """With crisis_state='none', post-crisis injection must NOT fire."""
    state = _freeflow_state(
        message_en="I feel anxious today",
        crisis_state="none",
    )
    system_str, _, _ = compose_prompt(state)
    assert "POST-CRISIS" not in system_str


# ── Cumulative distress heuristic ────────────────────────────────────────────

async def test_escalating_distress_flag_set_after_streak():
    """3 consecutive turns at intensity ≥6 must set escalating_distress clinical flag."""
    state = _state("I can't cope anymore")
    state["distress_trajectory"] = [7, 8]   # two prior high-intensity turns
    state["emotional_intensity"] = 7         # this turn (one-turn lag: previous turn's score)
    result = await safety_check_node(state)
    assert "escalating_distress" in result["clinical_flags"]


async def test_escalating_distress_flag_absent_below_floor():
    """Scores below floor (< 6) must NOT trigger escalating_distress."""
    state = _state("I feel okay today")
    state["distress_trajectory"] = [3, 4]
    state["emotional_intensity"] = 3
    result = await safety_check_node(state)
    assert "escalating_distress" not in result["clinical_flags"]


async def test_escalating_distress_not_triggered_with_only_two_high_turns():
    """Two high-intensity turns (one short of streak) must NOT set the flag."""
    state = _state("I'm struggling")
    state["distress_trajectory"] = [8]   # one prior high-intensity turn
    state["emotional_intensity"] = 7     # this turn → trajectory becomes [8, 7]
    result = await safety_check_node(state)
    assert "escalating_distress" not in result["clinical_flags"]


def test_cumulative_distress_injection_fires_on_flag():
    """PI-CD-001 must inject cumulative distress guidance when escalating_distress flag is present."""
    state = _freeflow_state(clinical_flags=["escalating_distress"])
    system_str, _, _ = compose_prompt(state)
    assert "CUMULATIVE DISTRESS" in system_str


def test_islamic_framing_absent_for_generic_prayer():
    """'I pray to God every day' must NOT inject Islamic framing (no allah/quran etc)."""
    state = _freeflow_state(message_en="I pray to God every day")
    system_str, _, _ = compose_prompt(state)
    assert "sabr" not in system_str and "ibtila" not in system_str and "tawakkul" not in system_str, (
        "Generic prayer without Islamic keywords must not trigger CU-IS-001"
    )


def test_generic_religious_framing_fires_on_god_keyword():
    """Generic spiritual framing (CU-RG-001) must fire for universal religious language."""
    state = _freeflow_state(message_en="I pray to God every day")
    system_str, _, _ = compose_prompt(state)
    assert "spiritual" in system_str.lower() or "faith" in system_str.lower() or "religious" in system_str.lower(), (
        "CU-RG-001 must inject generic religious context for 'god'/'prayer' keywords"
    )


def test_shame_framing_fires_on_arabic_ayb():
    """CU-SH-001 must inject shame-specific framing when Arabic عيب detected."""
    state = _freeflow_state(
        raw_message="عيب أن أتكلم عن مشاكلي",
        message_en="It is shameful to talk about my problems",
        detected_language="ar",
    )
    system_str, _, _ = compose_prompt(state)
    assert "shame" in system_str.lower() or "social" in system_str.lower() or "bond" in system_str.lower(), (
        "CU-SH-001 must fire on Arabic عيب and inject shame-specific framing"
    )


def test_shame_framing_fires_on_english_disgrace():
    """CU-SH-001 must fire on English shame/disgrace keywords."""
    state = _freeflow_state(message_en="I would bring disgrace to my family if they knew")
    system_str, _, _ = compose_prompt(state)
    assert "shame" in system_str.lower() or "social" in system_str.lower(), (
        "CU-SH-001 must fire on 'disgrace' keyword"
    )


def test_shame_framing_absent_for_generic_sad():
    """CU-SH-001 must NOT fire for generic sadness without shame/disgrace keywords."""
    state = _freeflow_state(message_en="I feel sad and hopeless today")
    system_str, _, _ = compose_prompt(state)
    assert "social bond" not in system_str.lower()


def test_ramadan_framing_fires_on_ramadan_keyword():
    """CU-RR-001 must inject Ramadan context when 'Ramadan' or 'fasting' detected."""
    state = _freeflow_state(message_en="I'm exhausted and irritable during Ramadan")
    system_str, _, _ = compose_prompt(state)
    assert "ramadan" in system_str.lower() or "fasting" in system_str.lower(), (
        "CU-RR-001 must inject Ramadan framing for 'Ramadan' keyword"
    )


def test_ramadan_framing_fires_on_arabic_ramadan():
    """CU-RR-001 must fire on Arabic رمضان keyword via text_ar path."""
    state = _freeflow_state(
        raw_message="رمضان هذه السنة متعب جداً",
        message_en="Ramadan this year is very tiring",
        detected_language="ar",
    )
    system_str, _, _ = compose_prompt(state)
    assert "ramadan" in system_str.lower() or "fasting" in system_str.lower()


def test_ramadan_framing_absent_without_keyword():
    """CU-RR-001 must NOT fire for generic tiredness without Ramadan/fasting keywords."""
    state = _freeflow_state(message_en="I'm exhausted and can't sleep")
    system_str, _, _ = compose_prompt(state)
    assert "ramadan" not in system_str.lower()


def test_dialect_mirroring_fires_on_khaleeji_wayed():
    """CU-DM-001 must inject dialect instruction when Khaleeji وايد detected."""
    state = _freeflow_state(
        raw_message="أنا وايد تعبان اليوم",
        message_en="I am very tired today",
        detected_language="ar",
    )
    system_str, _, _ = compose_prompt(state)
    assert "DIALECT" in system_str, (
        "CU-DM-001 must inject DIALECT instruction for Khaleeji وايد"
    )


def test_dialect_mirroring_fires_on_shloun():
    """CU-DM-001 must fire on other Khaleeji markers like شلون."""
    state = _freeflow_state(
        raw_message="شلون أتعامل مع هذا الموضوع؟",
        message_en="How do I deal with this topic?",
        detected_language="ar",
    )
    system_str, _, _ = compose_prompt(state)
    assert "DIALECT" in system_str


def test_dialect_mirroring_fires_for_msa():
    """CU-DM-001 must fire for formal MSA — the language baseline applies to ALL Arabic,
    not just messages containing Khaleeji markers."""
    state = _freeflow_state(
        raw_message="أشعر بالقلق الشديد هذا اليوم",
        message_en="I feel intense anxiety today",
        detected_language="ar",
    )
    system_str, _, _ = compose_prompt(state)
    assert "DIALECT" in system_str, (
        "CU-DM-001 (dialect_mirroring) uses empty trigger_keywords as a language-only trigger "
        "and must fire for every Arabic message including formal MSA."
    )


# ── Code-switching detection and CU-CS-001 ───────────────────────────────────

async def test_safety_check_node_detects_code_switching():
    """safety_check_node must set code_switching=True for mixed Arabic/English messages."""
    state = _state("أنا feeling really stressed اليوم")
    result = await safety_check_node(state)
    assert result.get("code_switching") is True, (
        "safety_check_node must detect mixed Arabic+Latin script and set code_switching=True"
    )


async def test_safety_check_node_code_switching_false_for_pure_arabic():
    """safety_check_node must set code_switching=False for pure Arabic."""
    state = _state("أنا وايد تعبان اليوم")
    result = await safety_check_node(state)
    assert result.get("code_switching") is False


async def test_safety_check_node_code_switching_false_for_pure_english():
    """safety_check_node must set code_switching=False for pure English."""
    state = _state("I feel really anxious today")
    result = await safety_check_node(state)
    assert result.get("code_switching") is False


def test_code_switch_rule_fires_on_mixed_arabic_english():
    """CU-CS-001 must fire when state has code_switching=True."""
    state = _freeflow_state(
        raw_message="أنا feeling really stressed اليوم",
        message_en="I am feeling really stressed today",
        detected_language="ar",
        code_switching=True,
    )
    system_str, _, _ = compose_prompt(state)
    assert "CODE-SWITCHING" in system_str, (
        "CU-CS-001 must inject code-switching instruction when code_switching=True in state"
    )


def test_code_switch_rule_absent_for_pure_arabic():
    """CU-CS-001 must NOT fire when state has code_switching=False."""
    state = _freeflow_state(
        raw_message="أنا وايد تعبان اليوم",
        message_en="I am very tired today",
        detected_language="ar",
        code_switching=False,
    )
    system_str, _, _ = compose_prompt(state)
    assert "CODE-SWITCHING" not in system_str


def test_cultural_rule_schema_accepts_code_switch_trigger_type():
    """CulturalRule schema must accept trigger_type='code_switch' with empty trigger_keywords."""
    from sage_poc.rules.schemas import CulturalRule
    rule = CulturalRule.model_validate({
        "rule_id": "TEST-CS-001",
        "category": "cultural",
        "effective_date": "2026-05-21",
        "trigger_type": "code_switch",
        "trigger_keywords": [],
        "action": {"type": "test"},
    })
    assert rule.trigger_type == "code_switch"
    assert rule.trigger_keywords == []


def test_existing_cultural_rules_unaffected_by_schema_change():
    """Existing rules with no trigger_type field must default to keyword_match and still fire."""
    from sage_poc.rules.loader import reload_all
    reload_all()
    state = _freeflow_state(message_en="I feel my faith in allah is fading")
    system_str, _, _ = compose_prompt(state)
    assert "ISLAMIC" in system_str or "sabr" in system_str or "ibtila" in system_str, (
        "Existing CU-IS-001 must still fire after schema change (backward compat)"
    )


def test_no_em_dashes_in_any_clinical_flag_adaptation():
    """All PI-CF-* rules must have no em dashes in their content — prevents prompt mirroring."""
    import json, pathlib
    data = json.loads(pathlib.Path(
        "src/sage_poc/rules/data/prompt_injection/clinical_flag_adaptations.json"
    ).read_text(encoding="utf-8"))
    for rule in data["rules"]:
        content = rule["action"].get("content", "")
        assert "—" not in content, (
            f"{rule['rule_id']} action.content contains an em dash — "
            "rule content is injected into the LLM system prompt and causes em-dash mirroring"
        )


def test_all_cultural_rules_use_layer_l5():
    """Every cultural rule must inject at L5 — prevents layer drift from L2 contamination."""
    import json, pathlib
    for path in sorted(pathlib.Path("src/sage_poc/rules/data/cultural").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for rule in data["rules"]:
            layer = rule["action"].get("layer", "MISSING")
            assert layer == "L5", (
                f"{rule['rule_id']} in {path.name} has layer={layer!r}, expected 'L5'"
            )


def test_code_switch_rule_fires_alongside_islamic_rule():
    """CU-CS-001 must still fire even when CU-IS-001 also fires in the same turn."""
    state = _freeflow_state(
        message_en="I feel allah has abandoned me today",
        code_switching=True,
    )
    system_str, _, _ = compose_prompt(state)
    assert "CODE-SWITCHING" in system_str, (
        "CU-CS-001 must inject code-switching context even when CU-IS-001 also fires"
    )
    assert "ISLAMIC" in system_str or "sabr" in system_str.lower(), (
        "CU-IS-001 must also fire when Islamic keyword present"
    )


@pytest.mark.parametrize("text", [
    "I have to build a network all over again",
    "I've been building a network from scratch",
    "I exhausted my network here",
    "I don't know anyone here",
    "I have no friends here",
    "starting over in a new country",
    "this wasn't my first choice of country",
    "Dubai is not my first choice",
    "I have no support system here",
    "moved here for my career but",
    "starting fresh somewhere new",
])
def test_pi_ei_001_fires_on_paraphrase_expat_isolation(text):
    from sage_poc.rules import engine
    result = engine.evaluate("prompt_injection", {
        "text": text,
        "text_ar": None,
        "clinical_flags": [],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "session_flags": [],
    })
    rule_ids = [r.rule_id for r in result.fired]
    assert "PI-EI-001" in rule_ids, f"Expected PI-EI-001 for: {text!r}"


# ── PI-ID-001: identity question injection ───────────────────────────────────

@pytest.mark.parametrize("text,text_ar", [
    ("what are you", None),
    ("who are you", None),
    ("are you a therapist", None),
    ("are you my therapist", None),
    ("are you a coach", None),
    ("are you my coach", None),
    ("are you a counsellor", None),
    ("are you a mental health", None),
    ("you're a therapist", None),
    ("are you human", None),
    ("enta therapist", None),
    ("inta therapist", None),
    ("enta coach", None),
    ("inta doctor", None),
    # Arabic script keywords matched against text_ar
    ("", "ما أنت"),
    ("", "من أنت"),
    ("", "أنت معالج"),
    ("", "أنت مدرب"),
    ("", "أنت مستشار"),
])
def test_pi_id_001_fires_on_identity_question(text, text_ar):
    """PI-ID-001 must fire for identity question keywords — English, Arabic, and Arabizi."""
    from sage_poc.rules import engine
    result = engine.evaluate("prompt_injection", {
        "text": text,
        "text_ar": text_ar,
        "clinical_flags": [],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "session_flags": [],
    })
    rule_ids = [r.rule_id for r in result.fired]
    assert "PI-ID-001" in rule_ids, (
        f"Expected PI-ID-001 for identity question text={text!r} text_ar={text_ar!r}"
    )


def test_pi_id_001_action_injects_to_system():
    """PI-ID-001 action must inject to the system role with 'wellness companion' framing."""
    from sage_poc.rules import engine
    result = engine.evaluate("prompt_injection", {
        "text": "what are you exactly",
        "text_ar": None,
        "clinical_flags": [],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "session_flags": [],
    })
    id_rules = [r for r in result.fired if r.rule_id == "PI-ID-001"]
    assert id_rules, "PI-ID-001 must fire for 'what are you exactly'"
    action = id_rules[0].action
    assert action["target"] == "system"
    assert "wellness companion" in action["content"].lower()
    assert "therapist" in action["content"].lower()
    assert "coach" in action["content"].lower()


def test_pi_id_001_rule_file_loads_and_is_valid():
    """identity_question.json must load as a valid PromptInjectionRule."""
    import json
    from pathlib import Path
    from sage_poc.rules.schemas import PromptInjectionRule

    rule_path = (
        Path(__file__).parent.parent
        / "src" / "sage_poc" / "rules" / "data" / "prompt_injection" / "identity_question.json"
    )
    data = json.loads(rule_path.read_text())
    rules = [PromptInjectionRule(**r) for r in data["rules"]]
    assert len(rules) == 1
    rule = rules[0]
    assert rule.rule_id == "PI-ID-001"
    assert rule.trigger_type == "keyword_match"
    assert "what are you" in rule.trigger_keywords
    assert "ما أنت" in rule.trigger_keywords
    assert "enta therapist" in rule.trigger_keywords
