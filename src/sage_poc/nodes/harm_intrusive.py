"""Harm-intrusive iatrogenic-routing veto (Node 4 / skill_select).

Deterministic safety control. When a user discloses postpartum / parental EGO-DYSTONIC harm-intrusive
phenomenology (unwanted, distressing intrusive images or thoughts of harming a baby or child that the
person does not want and tries to stop), skill_select must NOT route to a self-help skill: worry,
rumination, thought-record and grounding tools REINFORCE the intrusive-thought cycle, so any such route
is iatrogenic. The veto ABSTAINS (defers to Node 3 low_confidence_respond), which is the correct terminal
for every matched case today (Stage 1). Stage 2 upgrades this destination abstain -> contain.

SCOPED NARROWLY to harm-intrusive-to-child phenomenology ONLY. It deliberately does NOT widen to general
OCD (checking/counting/contamination/symmetry) — that is the separate ocd_compulsion veto.

CRISIS SUPREMACY: active intent/plan to harm is CRISIS, intercepted upstream at Node 1 (crisis override)
which runs BEFORE Node 4. This veto only fires on content that already passed the Node 1 short-circuit;
abstaining is safe for the ego-dystonic case and never routes to a self-help skill.

ARM-INDEPENDENT by design: this is deterministic Node-4 content, NOT gated on SKILL_ROUTING_V2, so it
behaves identically under flags-off (V1, the prod hotfix surface) and flags-on (V2). It runs BEFORE both
routing tiers (keyword Tier 1 and semantic Tier 2), so no harm-intrusive disclosure can reach either.

Patterns are single-sourced from rules/data/safety/harm_intrusive_patterns.json (clinician-owned content),
mirroring the ocd_compulsion / ipv_preempt lexicon pattern. Match rule: case-insensitive substring, keyed
on HARM directed at a baby/child, or on an intrusive image/thought OF HARMING.

Governance: Stage 1 of docs/superpowers/plans/2026-07-08-clinical-containment-pathway.md, mirroring the
approved OCD-compulsion veto precedent. DEPLOY GATED ON CLINICIAN PATTERN SIGN-OFF.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "rules" / "data" / "safety" / "harm_intrusive_patterns.json"
)
_data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))

# Public: the verbatim harm-intrusive-veto lexicon. Single-sourced so the production copy and any test
# ground truth cannot diverge.
HARM_INTRUSIVE_PATTERNS: tuple[str, ...] = tuple(_data["patterns"])
_NORMALIZED: tuple[str, ...] = tuple(p.lower() for p in HARM_INTRUSIVE_PATTERNS)


def is_harm_intrusive(*texts: str) -> bool:
    """True when ANY provided text contains a harm-intrusive pattern (case-insensitive substring).

    Deterministic, no model call, no LLM. LANGUAGE CONTRACT: safety detection reads the RAW input,
    not only the translated message_en — callers pass (message_en, raw_message). Today the Arabic
    patterns are absent (translation currently catches the AR ego-dystonic disclosure), so this
    change makes the raw path AVAILABLE for the clinician-authored AR patterns (#330, harm_intrusive
    standard cadence) without waiting on a second code change. Empty/None ignored; no args -> False.
    """
    hay = " \n ".join(t for t in texts if t).lower()
    return any(phrase in hay for phrase in _NORMALIZED)
