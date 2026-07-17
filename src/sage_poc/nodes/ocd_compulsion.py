"""OCD-compulsion iatrogenic-routing veto (Node 4 / skill_select).

Deterministic safety control. When a user discloses an OCD compulsion or ritual (checking,
counting/magic/undoing, scrupulosity, rereading/redoing, contamination/reassurance/symmetry),
skill_select must NOT route to a self-help skill: worry, rumination, thought-record and grounding
tools REINFORCE compulsions, so any such route is iatrogenic. The veto ABSTAINS (defers to Node 3
low_confidence_respond), which is the correct terminal for every matched case.

ARM-INDEPENDENT by design: this is deterministic Node-4 content, NOT gated on SKILL_ROUTING_V2, so
it behaves identically under flags-off (V1, the prod hotfix surface) and flags-on (V2). It runs
BEFORE both routing tiers (keyword Tier 1 and semantic Tier 2), so no compulsion can reach either.

Patterns are single-sourced from rules/data/safety/ocd_compulsion_patterns.json (CMS-owned content),
mirroring the ipv_preempt lexicon pattern. Match rule: case-insensitive substring, keyed on the
compulsive ACTION/ritual (not on repetition/looping, which ordinary worry legitimately owns).

Approved: escalation 2026-07-07-v1-iatrogenic-ocd-routing-escalation.md (clinical lead), expedited.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "rules" / "data" / "safety" / "ocd_compulsion_patterns.json"
)
_data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))

# Public: the verbatim compulsion-veto lexicon. Single-sourced so the production copy and any test
# ground truth cannot diverge.
COMPULSION_PATTERNS: tuple[str, ...] = tuple(_data["patterns"])
_NORMALIZED: tuple[str, ...] = tuple(p.lower() for p in COMPULSION_PATTERNS)


def is_ocd_compulsion(*texts: str) -> bool:
    """True when ANY provided text contains an OCD-compulsion pattern (case-insensitive substring).

    Deterministic, no model call, no LLM. LANGUAGE CONTRACT: safety detection reads the RAW input,
    not only the translated message_en — callers pass (message_en, raw_message) so an Arabic
    compulsion matches the native AR patterns directly instead of riding a lossy translation (the
    #330 live bypass root cause). Empty/None args are ignored; no args -> False.
    """
    hay = " \n ".join(t for t in texts if t).lower()
    return any(phrase in hay for phrase in _NORMALIZED)
