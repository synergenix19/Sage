# tests/test_safety_detection.py
#
# Unified safety detection test suite — SF-1 (passive SI / veiled ideation) + SF-6 (false positives).
#
# Architecture:
#   test_safety_hard_gate     — hard assertions for all cases where known_fn=False
#   test_safety_known_gap     — xfail assertions documenting current FN gaps (negation gap, veiled ideation)
#
# Both test classes run through safety_check_node (full Node 1 pipeline) with Arabic
# translation mocked to a benign phrase so no live LLM calls are made.
#
# Subsystem assertions:
#   S1 crisis detection:  crisis_flags contains expected_flag (si_explicit/si_passive/si_method/command_hallucination)
#   S3 detection:         crisis_flags contains "s3_semantic" (tested in test_safety_node_integration.py @slow)
#   Clinical flags only:  is_safe=True AND expected_flag in clinical_flags AND crisis_flags==[]
#   FP suppression:       is_safe=True AND crisis_flags==[]
#
# For baseline recall measurement, run:
#   python scripts/safety_confusion_matrix.py

from __future__ import annotations

import pytest
from contextlib import contextmanager, nullcontext
from unittest.mock import patch

from sage_poc.nodes.safety_check import safety_check_node
from tests.fixtures.safety.cases import (
    SAFETY_CASES,
    HARD_GATE_CASES,
    KNOWN_GAP_CASES,
    SafetyCase,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_state(phrase: str) -> dict:
    return {
        "raw_message": phrase,
        "detected_language": "en",
        "message_en": phrase,
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


@contextmanager
def _translation_mock_if_arabic(case: SafetyCase):
    """Mock async_translate_to_english for Arabic-script phrases.

    Returns a benign English phrase so the S1 English path does not interfere with
    the Arabic S1 path being tested. Arabizi (language='az') uses pure Latin; no mock
    needed — the node classifies it as English and passes text_raw to the rules engine.
    """
    if case.language == "ar":
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="I expressed a feeling in Arabic",
        ):
            yield
    else:
        with nullcontext():
            yield


def _case_id(case: SafetyCase) -> str:
    # Trim long phrases for readable parametrize IDs
    short = case.phrase[:60].replace(" ", "_")
    return f"{case.category}|{case.language}|{short}"


# ── Hard gate — cases with known_fn=False ────────────────────────────────────

@pytest.mark.parametrize("case", HARD_GATE_CASES, ids=[_case_id(c) for c in HARD_GATE_CASES])
async def test_safety_hard_gate(case: SafetyCase):
    """Hard assertion for all cases where the current system is expected to correctly classify.

    For crisis-positive cases: is_safe must be False AND expected_flag in crisis_flags.
    For crisis-negative cases: is_safe must be True AND crisis_flags must be empty.
    For tn_clinical_only: additionally asserts expected_flag appears in clinical_flags.

    Subsystem pinning: asserting expected_flag (e.g. 'si_passive', 'si_explicit') identifies
    which S1 rule fired — not just that the node returned is_safe=False.
    """
    with _translation_mock_if_arabic(case):
        result = await safety_check_node(_make_state(case.phrase))

    if case.expected_is_crisis:
        assert result["is_safe"] is False, (
            f"[{case.rule_hint or case.mechanism}] Expected crisis for: {case.phrase!r}\n"
            f"Note: {case.note}\n"
            f"Got crisis_flags={result['crisis_flags']}"
        )
        if case.expected_flag is not None:
            assert case.expected_flag in result["crisis_flags"], (
                f"Expected flag {case.expected_flag!r} missing from crisis_flags={result['crisis_flags']}\n"
                f"Phrase: {case.phrase!r}\n"
                f"Rule: {case.rule_hint} | Mechanism: {case.mechanism}"
            )
    else:
        assert result["is_safe"] is True, (
            f"[FP] Crisis triggered for non-crisis phrase: {case.phrase!r}\n"
            f"Unexpected crisis_flags={result['crisis_flags']}\n"
            f"Note: {case.note}"
        )
        assert result["crisis_flags"] == [], (
            f"Expected empty crisis_flags for: {case.phrase!r}\n"
            f"Got: {result['crisis_flags']}"
        )
        if case.category == "tn_clinical_only" and case.expected_flag is not None:
            assert case.expected_flag in result["clinical_flags"], (
                f"Expected clinical flag {case.expected_flag!r} missing from clinical_flags={result['clinical_flags']}\n"
                f"Phrase: {case.phrase!r}\n"
                f"Rule: {case.rule_hint}"
            )


# ── Known gaps — cases with known_fn=True ────────────────────────────────────
#
# These are clinical positives that the current S1 system misses. Marked xfail so the
# test suite passes while documenting the gap. If S1 is extended to cover these phrases,
# the test will unexpectedly pass (XPASS) — at that point, move the case to HARD_GATE_CASES.
#
# Gap taxonomy:
#   negation_check_fn — S1 pattern matched but suppressed by negation_check incorrectly
#   veiled_miss       — vocabulary in phrase diverges from SK-EN-002 patterns; no substring match

@pytest.mark.xfail(
    reason="Known S1 detection gap — negation_check FN or SF-1 veiled ideation miss. "
           "Run scripts/safety_confusion_matrix.py for the full baseline count."
)
@pytest.mark.parametrize("case", KNOWN_GAP_CASES, ids=[_case_id(c) for c in KNOWN_GAP_CASES])
async def test_safety_known_gap(case: SafetyCase):
    """Asserts that these clinical-positive phrases trigger crisis.

    Each will fail (xfail) because S1 misses them today. The assertion is identical
    to the hard gate: is_safe must be False. If/when a fix lands, the test transitions
    from XFAIL to XPASS — then promote it to test_safety_hard_gate.
    """
    with _translation_mock_if_arabic(case):
        result = await safety_check_node(_make_state(case.phrase))

    assert result["is_safe"] is False, (
        f"[KNOWN GAP — {case.mechanism}] System missed: {case.phrase!r}\n"
        f"Note: {case.note}\n"
        f"crisis_flags={result['crisis_flags']}"
    )
