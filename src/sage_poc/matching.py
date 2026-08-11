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
