"""Single matching surface for explicit-modality-request detection (EMR Phase 1).

Plan: docs/superpowers/plans/2026-07-28-explicit-modality-request-handling.md.
Architectural constraint (review-imposed): ONE deterministic detector, THREE consumers.
`detect_explicit_modality_request` runs once per turn at the head of intent_route,
BEFORE and independently of the LLM intent classification, and its result is carried in
the declared `explicit_modality_request` state channel. The executor, the info_request
early-return, and the offer-reply resolution (Phase 2) consume the same flag — all
trajectories converge on the same deterministic signal, which is what neutralizes the
Node-2 bistability finding for this defect class. An explicit ask for a tool is not a
probabilistic inference and is not routed through one (Cardinal Rule 4, one layer out).

Latency budget: one case-insensitive substring pass over a <=32-entry lexicon; no model
call, no embedding call (<=1ms, asserted in tests).

Language gate (B2): EN sessions only. AR sessions arrive here with translated
message_en that WOULD match the EN lexicon, so the gate is on session language, not on
which list matched; AR support waits on the validated AR lexicon (Lane 3).
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "rules" / "data" / "skill_matching" / "skill_request_phrases.json"

with open(_DATA_FILE, encoding="utf-8") as _f:
    _DATA = json.load(_f)

REQUEST_PHRASES: tuple[dict, ...] = tuple(_DATA["request_phrases"])
BINDING_TABLE: dict = dict(_DATA["binding_table"])

NOT_REQUESTED: dict = {"requested": False, "modality_hint": None}


def detect_explicit_modality_request(message_en: str, raw_message: str, lang: str) -> dict:
    """Deterministic per-turn detector. Returns {"requested": bool, "modality_hint": str|None}.

    First matching lexicon entry wins for the hint; hinted entries are checked after
    unhinted ones ONLY by data-file order, so a message matching both a generic request
    phrasing and a modality-specific one carries the specific hint when the specific
    entry matched at all (any hinted match overrides a None hint).
    """
    if lang != "en":
        return dict(NOT_REQUESTED)
    text = (message_en or "").lower()
    if not text:
        return dict(NOT_REQUESTED)
    requested = False
    hint: str | None = None
    for entry in REQUEST_PHRASES:
        if entry["phrase"] in text:
            requested = True
            if entry["modality_hint"] and hint is None:
                hint = entry["modality_hint"]
    if not requested:
        return dict(NOT_REQUESTED)
    return {"requested": True, "modality_hint": hint}


# ---------------------------------------------------------------------------
# EMR Phase 2 — screening state (the shared delivery gate; plan section
# "Screening gates delivery (B1+C1)", signed copy per modality_screen.json).
#
# recent_presentation is the M1 stand-in for the enriched-state Active Issues
# List (not implemented in the POC): a session-scoped accumulation channel,
# updated deterministically each turn by intent_route when the flag is ON.
# Consumers never deliver a skill offer unless screen["cleared"] is True;
# `chronicity unknown` NEVER clears (duration is the mandatory "more than
# mild" discriminator). Chronic clears WITH referral_alongside=True (the
# signed section-2 "alongside" reading, Vee 2026-07-29 item 3).
# ---------------------------------------------------------------------------

_SCREEN_FILE = Path(__file__).parent / "rules" / "data" / "skill_matching" / "modality_screen.json"

with open(_SCREEN_FILE, encoding="utf-8") as _sf:
    _SCREEN = json.load(_sf)

SCREEN_LEAD_IN: str = _SCREEN["lead_in"]
SCREEN_QUESTIONS: dict = dict(_SCREEN["questions"])
_MANDATORY: tuple[str, ...] = tuple(_SCREEN["mandatory_clearing_set"])
_CHRONIC = tuple(_SCREEN["duration_markers"]["chronic"])
_ACUTE = tuple(_SCREEN["duration_markers"]["acute"])
_ONSET = tuple(_SCREEN["onset_markers"])
_PHYSICAL = tuple(_SCREEN["physical_symptom_markers"])
_RED_FLAG = tuple(_SCREEN["red_flag_markers"])


def empty_presentation_context() -> dict:
    return {
        "physical_symptoms_mentioned": False,
        "red_flag_language": False,
        "duration_class": None,       # "acute" | "chronic" | None (None NEVER clears)
        "onset_supplied": False,
        "quality_checked": False,
        "screen_asked": [],           # question keys already asked this session
        "cleared": False,
        "referral_alongside": False,  # chronic case: skill WITH referral (signed reading)
    }


def update_presentation_context(prev: dict | None, message_en: str, lang: str) -> dict:
    """Deterministic per-turn accumulation. Monotonic: supplied facts never un-supply
    (red_flag_language latches; a later benign turn cannot clear it). EN-gated with the
    same B2 rule as the detector. A turn following an asked quality question marks
    quality_checked (the user answered SOMETHING to it; content adjudication is the
    medical guard's job, not the screen's)."""
    ctx = dict(prev) if prev else empty_presentation_context()
    ctx["screen_asked"] = list(ctx.get("screen_asked") or [])
    if lang != "en":
        return _derive(ctx)
    text = (message_en or "").lower()
    if not text:
        return _derive(ctx)
    if any(m in text for m in _PHYSICAL):
        ctx["physical_symptoms_mentioned"] = True
    if any(m in text for m in _RED_FLAG):
        ctx["red_flag_language"] = True
    if ctx["duration_class"] is None:
        if any(m in text for m in _CHRONIC):
            ctx["duration_class"] = "chronic"
        elif any(m in text for m in _ACUTE):
            ctx["duration_class"] = "acute"
    if not ctx["onset_supplied"] and any(m in text for m in _ONSET):
        ctx["onset_supplied"] = True
    if "quality" in ctx["screen_asked"] and not ctx["quality_checked"]:
        # this user turn is the reply to the quality question
        ctx["quality_checked"] = True
    return _derive(ctx)


def _derive(ctx: dict) -> dict:
    """cleared + referral_alongside are DERIVED, never stored facts of their own."""
    quality_needed = ctx["physical_symptoms_mentioned"] and not ctx["quality_checked"]
    ctx["cleared"] = (
        ctx["duration_class"] is not None      # chronicity unknown never passes
        and ctx["onset_supplied"]
        and not quality_needed
        and not ctx["red_flag_language"]       # red-flag language never screen-clears;
                                               # the medical guard surface owns it
    )
    ctx["referral_alongside"] = ctx["duration_class"] == "chronic"
    return ctx


def next_screen_question(ctx: dict) -> dict | None:
    """The adaptive screen: the single next question to ask, or None when nothing is
    askable (cleared, or all mandatory questions exhausted unanswered, or red-flag
    language present, which is the medical guard's turn, not the screen's). One
    question at a time; never asks what the session already supplied; quality is
    conditional on physical-symptom mention (never blanket)."""
    if ctx["cleared"] or ctx["red_flag_language"]:
        return None
    asked = set(ctx.get("screen_asked") or [])
    if ctx["duration_class"] is None and "duration" not in asked:
        key = "duration"
    elif not ctx["onset_supplied"] and "onset" not in asked:
        key = "onset"
    elif ctx["physical_symptoms_mentioned"] and not ctx["quality_checked"] and "quality" not in asked:
        key = "quality"
    else:
        return None
    return {"key": key, "lead_in": SCREEN_LEAD_IN, "question": SCREEN_QUESTIONS[key]}
