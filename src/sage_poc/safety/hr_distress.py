"""HR-1 Stage 2 Task 1: deterministic distress parser + branch resolver.

SAFETY-CRITICAL. This module implements the doc's §3 branch condition: the
answer to "on a scale of 0 to 10, how distressing is this for you right now"
deterministically routes the user to "999/ER now" (higher-severity) or "see
a doctor promptly" (lower-severity). There is no LLM in this path (design
doc Requirement 1: "NO evaluate_completion_criteria / LLM call on this
path"). A false parse routes deterministically, so every choice below is
made to fail SAFE: when a case is ambiguous, we do not parse a score, and
the caller's default (fail-to-higher, see resolve_hr_branch) absorbs the
ambiguity instead of us guessing.

Two independent detectors feed the branch:
  - parse_distress(text): STRICT numeric scale parse + risk/agitation phrase
    screen (design doc's own bundling of these two signals in Requirement 1).
  - mania_behavior_underway(text): the spending/risk-taking subset of CF-007
    (see src/sage_poc/rules/data/safety/clinical_flag_patterns.json), i.e.
    the "risky behavior already underway" evidence type from §3. Kept
    separate from DistressParse because it is not part of the *reply to the
    distress question* per se, it's a second, independent evidence type the
    resolver must OR in (Finding 1: §3 is a conjunction of evidence types,
    not a score cutoff) -- see resolve_hr_branch's escalate_regardless.

No em dashes anywhere in this module (project convention for anything that
could reach an LLM prompt or user-facing string; there are no user-facing
strings here, but the convention is followed regardless).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


HR_HIGH_FLOOR = 7
"""Distress score at/above which the branch is higher-severity (999/ER).
Clinician-confirmed constant per the Stage 2 packet. Lives here for now;
the node reads it from here today and from config later (packet note)."""


@dataclass(frozen=True)
class DistressParse:
    """Result of parsing one user reply to the §1 distress question.

    score: 0-10 if (and only if) the reply matched a strict scale-form.
        None means "no score could be safely extracted" -- this is the
        common, expected outcome for non-answers and is NOT an error.
    risk_language: True if the reply itself contains agitation/danger/
        threat phrase-class content (doc §3's "signs of agitation, danger,
        or risky behavior already underway" -- the language-evidenced half
        of that clause; the behavior-underway half is
        mania_behavior_underway, deliberately kept as a separate function,
        see module docstring).
    """

    score: Optional[int]
    risk_language: bool


# ---------------------------------------------------------------------------
# Strict numeric scale parse (Finding 2)
# ---------------------------------------------------------------------------
#
# Design intent: a score is produced ONLY when the ENTIRE reply (after
# stripping whitespace and a single trailing terminator) is one of these
# scale-forms. This is why every pattern below is fully anchored with
# ^...$: a digit that is merely PRESENT somewhere inside a longer content
# clause ("I haven't slept for 4 days", "there are 3 of them outside",
# "I've spent 10 thousand") must NOT parse, because the number there names
# something else (days slept, a headcount, a sum of money) and is not an
# answer to "how distressing is this, 0-10". Anchoring the whole string is
# what makes "a digit adjacent to a content noun does not parse" true by
# construction rather than by an explicit noun blocklist, which would be
# an unbounded (and therefore unsafe) list to maintain.
#
# Allowed forms (verbatim from the brief):
#   - bare number as the whole/near-whole reply: "7", "0", "10"
#   - "N/10": "7/10"
#   - "N out of 10": "7 out of 10"
#   - "(maybe )(a )N": "a 7", "maybe a 7"
#   - "(a )<verbal-number zero..ten>": "seven", "a seven", "maybe a seven"
#
# A trailing "." "!" or "," is tolerated (people punctuate short replies);
# nothing else is. Case-insensitive for the verbal-number forms.

_VERBAL_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_TRAILING_PUNCT = r"\s*[.,!]?\s*"

# "7/10"
_RE_FRACTION = re.compile(r"^\s*(\d{1,2})\s*/\s*10" + _TRAILING_PUNCT + r"$")

# "7 out of 10"
_RE_OUT_OF_10 = re.compile(
    r"^\s*(\d{1,2})\s+out\s+of\s+10" + _TRAILING_PUNCT + r"$", re.IGNORECASE
)

# "7", "a 7", "maybe a 7", "maybe 7"
_RE_BARE_DIGIT = re.compile(
    r"^\s*(?:maybe\s+)?(?:a\s+)?(\d{1,2})" + _TRAILING_PUNCT + r"$", re.IGNORECASE
)

# "seven", "a seven", "maybe a seven", "maybe seven"
_RE_VERBAL = re.compile(
    r"^\s*(?:maybe\s+)?(?:a\s+)?("
    + "|".join(_VERBAL_NUMBERS)
    + r")"
    + _TRAILING_PUNCT
    + r"$",
    re.IGNORECASE,
)

_SCALE_MIN = 0
_SCALE_MAX = 10


def _extract_score(text: str) -> Optional[int]:
    """Try each strict scale-form in turn. Returns None (do NOT parse) if
    none match the whole reply, or if a matched number falls outside the
    0-10 scale (e.g. "15" -- a bare number is still rejected if it is not a
    valid distress score; parsing it would silently produce a nonsense
    score rather than the safe None)."""
    for pattern in (_RE_FRACTION, _RE_OUT_OF_10, _RE_BARE_DIGIT):
        match = pattern.match(text)
        if match:
            value = int(match.group(1))
            if _SCALE_MIN <= value <= _SCALE_MAX:
                return value
            return None  # out-of-range bare number ("15"): fail to no-parse, not clamp

    match = _RE_VERBAL.match(text)
    if match:
        return _VERBAL_NUMBERS[match.group(1).lower()]

    return None


# ---------------------------------------------------------------------------
# risk_language phrase-class
# ---------------------------------------------------------------------------
#
# Same discipline as the clinical_flag phrase-class rules (see
# src/sage_poc/rules/data/safety/clinical_flag_patterns.json): lowercased
# substring match over a fixed, doc-derived phrase list. This is
# deliberately generous (substring, not full-reply anchor) unlike the
# numeric parser above, because a false POSITIVE here only pushes the user
# toward the higher-severity (999/ER) branch, which is the doc's own
# fail-safe direction. There is no symmetric risk of a false positive
# routing someone to a WORSE outcome, so strictness is not required here
# the way it is for the numeric parse.
_RISK_LANGUAGE_PHRASES = (
    "they're outside right now",
    "they are outside right now",
    "i can't stay here",
    "i cant stay here",
    "i'm not safe",
    "im not safe",
)


def _has_risk_language(text_lower: str) -> bool:
    return any(phrase in text_lower for phrase in _RISK_LANGUAGE_PHRASES)


def parse_distress(text: str) -> DistressParse:
    """Parse one user reply to the §1 distress question.

    Deterministic only, no LLM, no network (design doc Requirement 1).
    risk_language is checked over the raw (lowercased) reply independent of
    whether a score also parsed. score is produced only via the strict
    scale-forms in _extract_score; everything else (non-answers, content
    clauses with an embedded digit, out-of-range numbers) yields None,
    which the branch resolver treats as "no evidence", not "no risk".
    """
    text = text or ""
    text_lower = text.strip().lower()

    score = _extract_score(text.strip())
    risk_language = _has_risk_language(text_lower)

    return DistressParse(score=score, risk_language=risk_language)


# ---------------------------------------------------------------------------
# mania_behavior_underway (Finding 1)
# ---------------------------------------------------------------------------
#
# The spending/risk-taking subset of CF-007 (mania_disclosure), i.e. only
# the two CF-007 patterns that describe a behavior already IN PROGRESS
# ("i've been spending loads of money", "i'm taking huge risks"). The rest
# of CF-007's patterns ("i feel unstoppable", "i feel invincible", "i don't
# need sleep", "my thoughts are racing all the time", etc.) are MOOD-only
# and must NOT escalate on their own -- the design doc's §3 clause is
# specifically "risky behavior already underway", not "elevated mood".
# Verbatim copied from clinical_flag_patterns.json CF-007 rather than
# imported from it, because CF-007 ships active:false / unsigned pending
# clinician ratification of the FULL mania-10 detection rule, while this
# behavior-underway subset is scoped and load-bearing for Stage 2's branch
# resolver independent of that ratification (this is a deterministic
# safety-control decision per the design doc's "RESOLVED" section, not a
# clinical_flag detection rule).
_MANIA_BEHAVIOR_PHRASES = (
    "i've been spending loads of money",
    "ive been spending loads of money",
    "i'm taking huge risks",
    "im taking huge risks",
)


def mania_behavior_underway(text: str) -> bool:
    """True iff the reply contains one of the §3 "risky behavior already
    underway" mania phrases (spending/risk-taking subset of CF-007).
    Mood-only mania language ("i feel amazing", "i don't need sleep", "i
    feel unstoppable") returns False: those don't escalate on their own.
    """
    text_lower = (text or "").strip().lower()
    return any(phrase in text_lower for phrase in _MANIA_BEHAVIOR_PHRASES)


# ---------------------------------------------------------------------------
# Branch resolver
# ---------------------------------------------------------------------------


def resolve_hr_branch(
    parse: DistressParse, *, is_reask: bool, escalate_regardless: bool
) -> str:
    """Resolve the §3 branch for this turn: "higher" | "lower" | "reask".

    Finding 1: §3 is a CONJUNCTION of evidence types, not a score cutoff.
    `escalate_regardless` is how the caller carries in independent
    behavior-underway evidence (mania_behavior_underway) so a low numeric
    score can never mask it -- the critical case this resolver exists to
    get right is a manic user who reports LOW distress while a risky
    behavior is already underway; that must still route "higher".

    Branch condition (verbatim from the brief):
      "higher" if parse.risk_language OR escalate_regardless OR
          (parse.score is not None AND parse.score >= HR_HIGH_FLOOR)
      "lower" only if a score is present AND below the floor AND neither
          risk_language nor escalate_regardless (the doc's "lower
          distress, no immediate danger indicated" -- BOTH conditions).
      No score and not is_reask -> "reask" (ask once more, gently).
      No score and is_reask -> "higher" (fail-to-higher: the doc forbids a
          third ask, so if the second reply still didn't parse, we do not
          gamble on "lower").
    """
    if parse.risk_language or escalate_regardless:
        return "higher"

    if parse.score is not None and parse.score >= HR_HIGH_FLOOR:
        return "higher"

    if parse.score is not None:
        # score present, below floor, no risk_language, no escalate_regardless
        return "lower"

    # parse.score is None from here on
    if is_reask:
        return "higher"  # fail-to-higher: second non-answer, no third ask

    return "reask"
