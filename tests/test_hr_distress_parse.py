"""HR-1 Stage 2 Task 1: deterministic distress parser + branch resolver.

Safety-critical: this module decides "999/ER now" vs "see a doctor promptly"
for a user already flagged with high-risk content. A false numeric parse here
routes deterministically to the wrong branch, so `parse_distress` is STRICT
(Finding 2) — a score is produced ONLY from clear scale-forms, never from a
digit embedded in a content sentence. `resolve_hr_branch` implements the
design doc's conjunction-of-evidence-types branch condition (Finding 1): §3
is not a score cutoff, so a low score plus behavior-underway must still
escalate.

Verbatim source: docs/superpowers/specs/2026-07-16-hr1-stage2-terminal-design.md
("RESOLVED" section) and .superpowers/sdd/task-1-brief.md.
"""
from __future__ import annotations

import pytest

from sage_poc.safety.hr_distress import (
    HR_HIGH_FLOOR,
    DistressParse,
    mania_behavior_underway,
    parse_distress,
    resolve_hr_branch,
)


# ---------------------------------------------------------------------------
# parse_distress: must-PARSE (clear scale-forms)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("7", 7),
        ("a 7", 7),
        ("maybe a seven", 7),
        ("7/10", 7),
        ("7 out of 10", 7),
        ("0", 0),
        ("10", 10),
    ],
)
def test_parse_distress_must_parse(text: str, expected: int) -> None:
    result = parse_distress(text)
    assert result.score == expected, f"{text!r} should parse to {expected}, got {result.score}"


# ---------------------------------------------------------------------------
# parse_distress: must-NOT-parse (dead-leg-to-ER controls, Finding 2)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "I haven't slept for 4 days",
        "there are 3 of them outside",
        "I've spent 10 thousand",
        "15",  # out of range, even though it's a bare number
    ],
)
def test_parse_distress_must_not_parse(text: str) -> None:
    result = parse_distress(text)
    assert result.score is None, (
        f"{text!r} must NOT parse a score (dead-leg-to-ER control); got {result.score}"
    )


def test_must_not_parse_count_is_four() -> None:
    """Explicit count so this safety-critical control list can't silently shrink."""
    controls = [
        "I haven't slept for 4 days",
        "there are 3 of them outside",
        "I've spent 10 thousand",
        "15",
    ]
    assert len(controls) == 4
    for text in controls:
        assert parse_distress(text).score is None


# ---------------------------------------------------------------------------
# Broadened lead-in set (terminal anchor kept -- the safety property)
# ---------------------------------------------------------------------------
#
# Closed, enumerated lead-in set (no \w+ anywhere in the prefix): it's, its,
# i'd say, id say, about, around, like, maybe, probably, i think. Each entry
# gets its own must-PARSE fixture below, and every broadened lead-in gets an
# adversarial must-NOT-parse twin proving the terminal $-anchor still blocks
# a non-terminal number (the actual safety property, unaffected by widening
# the prefix).

@pytest.mark.parametrize(
    "text,expected",
    [
        ("it's a 3", 3),
        ("it's 3", 3),
        ("its 4", 4),
        ("i'd say 7", 7),
        ("id say 5", 5),
        ("about a 4", 4),
        ("around a 5", 5),
        ("like a 6", 6),
        ("maybe a 7", 7),
        ("probably a 2", 2),
        ("i think a 8", 8),
    ],
)
def test_parse_distress_broadened_lead_in_must_parse(text: str, expected: int) -> None:
    result = parse_distress(text)
    assert result.score == expected, f"{text!r} should parse to {expected}, got {result.score}"


@pytest.mark.parametrize(
    "text",
    [
        "it's been 3 days since I slept",
        "its been 3 days since I slept",
        "i'd say about 4 people",
        "id say about 4 people",
        "about 4 of them are watching me",
        "around 5 voices",
        "like 6 people showed up",
        "maybe 7 people know",
        "probably 2 hours left",
        "i think 3 of them are following me",
    ],
)
def test_parse_distress_broadened_lead_in_adversarial_twin(text: str) -> None:
    """Adversarial twin for every broadened lead-in (proof the broadening
    cost nothing): the number is not terminal in any of these, so the
    $-anchor must still reject them -- exactly the "3 of them outside"
    dead-leg-to-ER control, just with a wider set of lead-ins to test it
    against."""
    result = parse_distress(text)
    assert result.score is None, (
        f"{text!r} must NOT parse (terminal-anchor control); got {result.score}"
    )


def test_parse_distress_verbal_number_with_broadened_prefix() -> None:
    """"about a seven" (word-number + broadened prefix): confirms the
    verbal-number path rides the same broadened prefix as the bare-digit
    path, not a separately-maintained copy."""
    result = parse_distress("about a seven")
    assert result.score == 7


def test_parse_distress_trailing_self_assessment_does_not_parse() -> None:
    """PINNED KNOWN LIMITATION (v1): a trailing self-assessment tail after
    the number ("I'm okay") breaks the terminal anchor, so this does NOT
    parse and falls through to reask. A general trailing tail is forbidden
    here because it would resurrect the "3 of them outside" dead-leg
    through the back door; a closed benign-tail set ("I'm okay", "I guess")
    is a possible v2 only if probe data shows it's common enough to justify
    the added surface. The re-ask covers this case in v1."""
    result = parse_distress("it's about a 3, I'm okay")
    assert result.score is None


# ---------------------------------------------------------------------------
# risk_language
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "they're outside right now",
        "I can't stay here",
        "I'm not safe",
    ],
)
def test_risk_language_true(text: str) -> None:
    assert parse_distress(text).risk_language is True


@pytest.mark.parametrize(
    "text",
    [
        "7",
        "I haven't slept for 4 days",
        "the voices are loud",
        "I feel amazing",
    ],
)
def test_risk_language_false_on_non_risk_text(text: str) -> None:
    assert parse_distress(text).risk_language is False


# ---------------------------------------------------------------------------
# mania_behavior_underway (Finding 1 — behavior, not mood)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "I've been spending loads of money",
        "I'm taking huge risks",
    ],
)
def test_mania_behavior_underway_true(text: str) -> None:
    assert mania_behavior_underway(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "I feel amazing",
        "I don't need sleep",
    ],
)
def test_mania_behavior_underway_false_mood_only(text: str) -> None:
    assert mania_behavior_underway(text) is False


# ---------------------------------------------------------------------------
# Non-answer content: no score, no risk, no behavior-underway
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "who told you that",
        "the voices are loud",
    ],
)
def test_non_answer_content(text: str) -> None:
    result = parse_distress(text)
    assert result.score is None
    assert result.risk_language is False
    assert mania_behavior_underway(text) is False


# ---------------------------------------------------------------------------
# resolve_hr_branch
# ---------------------------------------------------------------------------

def test_hr_high_floor_is_seven() -> None:
    assert HR_HIGH_FLOOR == 7


def test_branch_critical_case_low_score_but_behavior_underway_escalates() -> None:
    """THE CRITICAL BRANCH CASE: a manic user reports low distress while
    spending — must NOT be "lower". escalate_regardless carries the
    mania_behavior_underway evidence into the resolver (Finding 1: §3 is a
    conjunction of evidence types, not a score cutoff)."""
    parse = DistressParse(score=2, risk_language=False)
    branch = resolve_hr_branch(parse, is_reask=False, escalate_regardless=True)
    assert branch == "higher"


def test_branch_low_score_no_risk_no_behavior_is_lower() -> None:
    parse = DistressParse(score=2, risk_language=False)
    branch = resolve_hr_branch(parse, is_reask=False, escalate_regardless=False)
    assert branch == "lower"


@pytest.mark.parametrize("is_reask", [True, False])
def test_branch_risk_language_always_higher_regardless_of_reask(is_reask: bool) -> None:
    parse = DistressParse(score=2, risk_language=True)
    branch = resolve_hr_branch(parse, is_reask=is_reask, escalate_regardless=False)
    assert branch == "higher"


def test_branch_no_score_not_reask_is_reask_branch() -> None:
    parse = DistressParse(score=None, risk_language=False)
    branch = resolve_hr_branch(parse, is_reask=False, escalate_regardless=False)
    assert branch == "reask"


def test_branch_no_score_is_reask_fails_to_higher() -> None:
    parse = DistressParse(score=None, risk_language=False)
    branch = resolve_hr_branch(parse, is_reask=True, escalate_regardless=False)
    assert branch == "higher"


def test_branch_score_at_floor_is_higher() -> None:
    parse = DistressParse(score=HR_HIGH_FLOOR, risk_language=False)
    branch = resolve_hr_branch(parse, is_reask=False, escalate_regardless=False)
    assert branch == "higher"


def test_branch_score_just_below_floor_is_lower() -> None:
    parse = DistressParse(score=HR_HIGH_FLOOR - 1, risk_language=False)
    branch = resolve_hr_branch(parse, is_reask=False, escalate_regardless=False)
    assert branch == "lower"
