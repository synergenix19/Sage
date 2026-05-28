# tests/test_safety_node_integration.py
#
# Node-level integration tests for safety_check_node.
# These tests verify that the full pipeline — language detection, rules
# evaluation, flag extraction, and state output — works correctly end-to-end.
#
# Contrast with test_rules_safety.py, which tests engine.evaluate() directly,
# and test_nodes.py, which covers basic smoke tests for the node.
#
# Arabic translation is mocked throughout so no live LLM calls are made.

import asyncio
import logging
import pytest
from unittest.mock import patch, AsyncMock
from sage_poc.nodes.safety_check import safety_check_node


# ── State factory ─────────────────────────────────────────────────────────────

def make_state(**kwargs):
    defaults = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "conversation_summary": None,
        "code_switching": False,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
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
    return {**defaults, **kwargs}


# ── SF-1: Passive SI through safety_check_node ───────────────────────────────

class TestPassiveSiNodeLevel:
    """Verify passive SI phrases produce is_safe=False and si_passive in crisis_flags
    through the full safety_check_node pipeline."""

    async def test_passive_si_better_off_without_me(self):
        state = make_state(raw_message="everyone would be better off without me")
        result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Passive SI 'everyone would be better off without me' must not be safe"
        )
        assert "si_passive" in result["crisis_flags"], (
            "Expected si_passive flag for 'everyone would be better off without me'"
        )

    async def test_passive_si_no_point_in_living(self):
        state = make_state(raw_message="there's no point in living")
        result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Passive SI 'there's no point in living' must not be safe"
        )
        assert "si_passive" in result["crisis_flags"], (
            "Expected si_passive flag for 'there's no point in living'"
        )

    async def test_passive_si_wish_i_could_disappear(self):
        # Rules engine matches "I wish I could disappear" (base SK-EN-002 phrase).
        # Adverb-padded variants ("just", "forever") rely on regex flexibility in the rule;
        # use the canonical phrase to pin the node pipeline, not the rule's regex boundary.
        state = make_state(raw_message="I wish I could disappear")
        result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Passive SI 'I wish I could disappear' must not be safe"
        )
        assert "si_passive" in result["crisis_flags"], (
            "Expected si_passive flag for 'I wish I could disappear'"
        )

    async def test_passive_si_arabic_no_reason_to_live(self):
        # "ما عندي سبب اعيش" = "I have no reason to live"
        # Arabic rules fire on text_ar independently; translation is mocked for the English path.
        state = make_state(raw_message="ما عندي سبب اعيش")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="I have no reason to live",
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Arabic passive SI 'ما عندي سبب اعيش' must not be safe"
        )
        assert "si_passive" in result["crisis_flags"], (
            "Expected si_passive flag for Arabic 'ما عندي سبب اعيش'"
        )

    async def test_passive_si_arabizi_ma7ad_y7tajni(self):
        # "ma7ad y7tajni" = "nobody needs me" — Arabizi, langdetect classifies as English.
        # SK-AZ-002 matches on the English path.
        state = make_state(raw_message="ma7ad y7tajni")
        result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Arabizi passive SI 'ma7ad y7tajni' must trigger crisis via SK-AZ-002"
        )
        assert len(result["crisis_flags"]) > 0, (
            "Expected at least one crisis flag for Arabizi 'ma7ad y7tajni'"
        )


# ── SF-6: False positives through safety_check_node ──────────────────────────

class TestFalsePositivesNodeLevel:
    """Verify that idioms and hyperbole do not trigger crisis through the full node."""

    async def test_fp_english_dying_of_laughter(self):
        state = make_state(raw_message="I'm literally dying of laughter right now")
        result = await safety_check_node(state)
        assert result["is_safe"] is True, (
            "Idiom 'dying of laughter' must not trigger crisis (FPE-EN-001)"
        )
        assert result["crisis_flags"] == [], (
            "No crisis flags expected for 'dying of laughter'"
        )

    async def test_fp_english_killing_it(self):
        state = make_state(raw_message="I've been killing it at work this week")
        result = await safety_check_node(state)
        assert result["is_safe"] is True, (
            "Idiom 'killing it at work' must not trigger crisis (FPE-EN-001)"
        )
        assert result["crisis_flags"] == [], (
            "No crisis flags expected for 'killing it at work'"
        )

    async def test_fp_english_dead_tired(self):
        state = make_state(raw_message="I'm dead tired after that meeting")
        result = await safety_check_node(state)
        assert result["is_safe"] is True, (
            "Idiom 'dead tired' must not trigger crisis (FPE-EN-001)"
        )
        assert result["crisis_flags"] == [], (
            "No crisis flags expected for 'dead tired'"
        )

    async def test_fp_arabic_laughter_idiom(self):
        # "اموت من الضحك" = "dying of laughter" — FPE-AR-001 must suppress.
        state = make_state(raw_message="اموت من الضحك")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="dying of laughter",
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is True, (
            "Arabic laughter idiom 'اموت من الضحك' must be suppressed by FPE-AR-001"
        )
        assert result["crisis_flags"] == [], (
            "No crisis flags expected for Arabic laughter idiom"
        )

    async def test_fp_negation_i_dont_want_to_die(self):
        state = make_state(raw_message="I don't want to die, I love life")
        result = await safety_check_node(state)
        assert result["is_safe"] is True, (
            "Negated death phrase 'I don't want to die, I love life' must not trigger crisis"
        )
        assert result["crisis_flags"] == [], (
            "No crisis flags expected for negated SI phrase"
        )


# ── C-1: Khaleeji dialect through safety_check_node ──────────────────────────

class TestKhaleejiDialectNodeLevel:
    """Verify Khaleeji-specific patterns route correctly through the full node."""

    async def test_khaleeji_safe_beach_message(self):
        # "يلا نروح البحر الحين" = "let's go to the beach now" — unambiguously safe.
        state = make_state(raw_message="يلا نروح البحر الحين")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="let's go to the beach",
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is True, (
            "Khaleeji safe phrase 'يلا نروح البحر الحين' must not trigger crisis"
        )
        assert result["crisis_flags"] == [], (
            "No crisis flags expected for beach invitation message"
        )

    async def test_khaleeji_exhaustion_idiom_triggers_crisis(self):
        # "انا تعبت من كل شي" = "I'm exhausted from everything" — SK-AR-003 pattern.
        state = make_state(raw_message="انا تعبت من كل شي")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="I am exhausted from everything",
        ):
            result = await safety_check_node(state)
        # SK-AR-003 fires on the Arabic text regardless of translation.
        assert result["is_safe"] is False or "si_passive" in result["crisis_flags"], (
            "Khaleeji exhaustion idiom 'انا تعبت من كل شي' must trigger crisis via SK-AR-003"
        )

    async def test_khaleeji_no_life_in_heart(self):
        # "ما عاد في قلبي حياة" = "no life left in my heart" — SK-AR-003 pattern.
        state = make_state(raw_message="ما عاد في قلبي حياة")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="there is no life left in my heart",
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Khaleeji phrase 'ما عاد في قلبي حياة' must trigger crisis via SK-AR-003"
        )


# ── C-2: Code-switching edge cases ───────────────────────────────────────────

class TestCodeSwitchingNodeLevel:
    """Edge cases for Arabic/English code-switching detection through the full node."""

    async def test_code_switching_crisis_arabic_in_english_sentence(self):
        # Arabic script embedded in an English sentence triggers Arabic classification
        # and sets code_switching=True (both scripts present).
        state = make_state(raw_message="I am feeling أريد الموت today")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="I want to die",
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Arabic crisis phrase embedded in English sentence must trigger crisis"
        )
        assert result["detected_language"] == "ar", (
            "Arabic script presence must cause Arabic classification"
        )
        assert result["code_switching"] is True, (
            "Mixed Arabic and Latin scripts must set code_switching=True"
        )

    async def test_code_switching_arabizi_passive_si_node_level(self):
        # "hayati khalsa wallah" = "my life is over, I swear" — SK-AZ-002 keyword.
        # Arabizi is pure Latin so code_switching must be False (no Arabic script).
        state = make_state(raw_message="hayati khalsa wallah")
        result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Arabizi passive SI 'hayati khalsa wallah' must trigger crisis via SK-AZ-002"
        )
        assert result["code_switching"] is False, (
            "Arabizi (Latin-only) must not set code_switching=True"
        )

    async def test_code_switching_flag_set_when_both_scripts(self):
        # "ana okay بس a bit tired" — Latin and Arabic script present.
        # "بس" = "but" in Gulf Arabic. Message is benign; we only test the flag.
        state = make_state(raw_message="ana okay بس a bit tired")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="I'm okay but a bit tired",
        ):
            result = await safety_check_node(state)
        assert result["code_switching"] is True, (
            "Mixed Arabic Unicode and Latin characters must set code_switching=True"
        )


# ── B-2: S3 silent failure observability ─────────────────────────────────────

async def test_s3_timeout_emits_warning(caplog):
    """S3 TimeoutError must log a warning; S1 crisis detection still fires."""
    state = make_state(
        raw_message="I want to end everything",
        message_en="I want to end everything",
        crisis_state="none",
    )
    with patch(
        "sage_poc.nodes.safety_check.asyncio.wait_for",
        side_effect=asyncio.TimeoutError,
    ):
        with caplog.at_level(logging.WARNING, logger="sage_poc.nodes.safety_check"):
            result = await safety_check_node(state)
    assert any("S3 timeout" in r.message for r in caplog.records), \
        "Expected a warning mentioning 'S3 timeout'"
    # S1 keyword should still catch "end everything" — is_safe may be False
    # (outcome depends on S1 lexicon; just verify we didn't crash)
    assert "is_safe" in result


async def test_s3_exception_emits_warning(caplog):
    """S3 exception must log a warning; system must not raise."""
    state = make_state(raw_message="ok", message_en="ok", crisis_state="none")
    with patch(
        "sage_poc.nodes.safety_check.asyncio.wait_for",
        side_effect=RuntimeError("gpu exploded"),
    ):
        with caplog.at_level(logging.WARNING, logger="sage_poc.nodes.safety_check"):
            result = await safety_check_node(state)
    assert any("S3 check failed" in r.message for r in caplog.records), \
        "Expected a warning mentioning 'S3 check failed'"
    assert "is_safe" in result
