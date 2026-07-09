# NOTE (2026-07-10): this is the MINIMAL placeholder detector. The 231-line regex
# hardening (30de34c) was REJECTED on adversarial review (13.3% novel recall, 20% novel
# false-positive). §3a detection is a classification/scope problem; robust detection is a
# pending redesign = semantic recall (BA-offerable) + a clinician-owned precision gate,
# with the deterministic crisis-firing guarantee staying on the SI-answer catch (safety_check),
# NOT here. Clinician eval set: rules/data/safety/low_mood_3a_triggers.json + governance doc.
# Do NOT extend this inline.
"""§3a low-mood disclosure detection (deterministic, no LLM).

Task 2 of the §3a low-mood validate-first + woven-safety flow (see
tests/test_low_mood_screen.py for the flow overview). Detects a low-mood /
anhedonia disclosure across the five clinician-signed §3a trigger families:
energy/effort, anhedonia/interest, motivation, social withdrawal, affective
flatness. Deterministic substring match only, mirroring
ocd_compulsion.is_ocd_compulsion in style: no LLM, no semantic matcher, so the
interception in skill_select.py can rely on it as a first-class safety gate.

The pattern list below is exactly the §3a trigger vocabulary given in the
Task 2 brief (clinician-signed, settled, HARD BOUNDARY). Extending it requires
a fresh clinical sign-off, not a future context window's judgment call.
Patterns are deliberately specific (e.g. "lost interest in everything" rather
than the bare "lost interest") so ordinary, non-clinical uses of the same
words ("lost interest in the movie", "flat day") do not false-positive into a
screen whose SI answer we cannot parse.
"""
from __future__ import annotations

LOW_MOOD_PATTERNS: tuple[str, ...] = (
    "lost interest in everything",
    "no energy to do anything",
    "nothing feels enjoyable",
    "don't feel like doing anything",
    "dont feel like doing anything",
    "want to stay in bed",
    "feel flat",
    "feel numb",
    "feel empty",
    "withdrawing from everyone",
)
_NORMALIZED: tuple[str, ...] = tuple(p.lower() for p in LOW_MOOD_PATTERNS)


def is_low_mood_disclosure(message_en: str) -> bool:
    """True when `message_en` contains a §3a low-mood trigger pattern.

    Deterministic, no model call, no LLM. Matched against message_en (the
    translated English for Arabic sessions, though the interception in
    skill_select.py gates on detected_language == "en" before calling this).
    Empty/None -> False.
    """
    normalized = (message_en or "").lower()
    return any(phrase in normalized for phrase in _NORMALIZED)
