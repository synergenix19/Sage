"""S4b — deterministic self-worth presence deference (crisis-path FP exclusion). DRAFT, gated on Vee
signature (packet item 3, due 2026-08-25); flag default OFF, byte-identical when disabled.

The observed defect (S4B-FP-1, two-window stable, adjudicated spec-conformance HIGH): "kindness is for
other people, not me. I haven't earned it" draws the full first-person crisis card with crisis_flags=[]
— the escalation happens at the LLM intent layer, NOT the deterministic tier. This is the iatrogenic
direction: the spec's self-compassion pathway (S4a/S4b) exists precisely for self-critical framings, and
alarming responses to its own trigger vocabulary suppress the disclosures the pathway needs.

INTERCEPTION POINT (why here and not elsewhere): because nothing deterministic fired, a pre-classifier
exclusion has nothing to exclude, and an output-gate rewrite would run AFTER the crisis path had already
owned the turn (and the item-4 output-gate lane is a separate PR). The established mechanism for exactly
this shape — intent_route's LLM re-flags a safety_check-CLEAN turn as crisis — is the stamp/honor
override pair (panic Part A, grief S2a): code decides in intent_route, _route_after_intent honours the
stamp and restores the deterministic clean verdict (skill_select, where the self-compassion pathway can
route) instead of crisis_response.

NEVER-DISARM (structural, plus tested): the predicate is False whenever safety_check produced ANY signal
(crisis_flags — including S1's better-off-without-ME si_passive surface and the cardiac Node-1 flag —
medical_flags, or S3 at/above threshold). A deterministic S1/S3 fire never reaches the override as a
suppressible event: _route_after_safety short-circuits those turns to crisis_response BEFORE intent_route
runs. This exclusion can therefore only ever remove an LLM-layer escalation on a deterministically-clean
turn; it cannot weaken the deterministic tier.

THE CLINICAL BOUNDARY (the reason this needs Vee's signature, not a unilateral exclusion): self-worth /
deservingness framings WITHOUT existence content defer; deservingness + death-or-absence framing
("I don't deserve to be here / to exist", "better off without me") must STILL escalate. The boundary is
encoded as _EXISTENCE_TERMS: any hit keeps the escalation, same conservative dial as _HARM_TERMS.

Single-sourcing (the grief/cardiac pattern): the harm set is IMPORTED from panic_override._HARM_TERMS —
the same harm language that stops panic-grounding and grief-deference stops this deference, no drift.

_SELFWORTH_TERMS and _EXISTENCE_TERMS: SIGNED 2026-08-19: Vee (clinical lead) — PO relay; record: 2026-08-19-vee-approval-record-signature-sheet.md, item 3. Class-level per the portability clause (deservingness-without-existence does NOT escalate; with-existence MUST); term lists = current implementation + permanent fixtures.
Vocabulary is clinician-owned; Vee confirms/extends/narrows both lists on the packet decision.
Matching is case-insensitive substring, the crisis-lexicon convention. EN-only (AR rides the AR track,
same as grief_override).
"""
from __future__ import annotations

from sage_poc.nodes.panic_override import _HARM_TERMS
from sage_poc.safety.s3_semantic import S3_THRESHOLD

SELFWORTH_S3_SUB_THRESHOLD_CLEAN: float = S3_THRESHOLD

# SIGNED 2026-08-19: Vee (clinical lead) — PO relay; record: 2026-08-19-vee-approval-record-signature-sheet.md, item 3. Class-level per the portability clause (deservingness-without-existence does NOT escalate; with-existence MUST); term lists = current implementation + permanent fixtures.
# Self-worth / deservingness framings WITHOUT existence content: the S4a/S4b trigger register.
_SELFWORTH_TERMS: tuple[str, ...] = (
    "don't deserve kindness", "dont deserve kindness", "deserve kindness",
    "don't deserve love", "dont deserve love", "don't deserve compassion", "dont deserve compassion",
    "don't deserve care", "dont deserve care", "don't deserve good things", "dont deserve good things",
    "don't deserve to be happy", "dont deserve to be happy",
    "don't deserve anything good", "dont deserve anything good",
    "deserve nothing good", "haven't earned", "havent earned", "have not earned",
    "kindness is for other people", "kindness is for others",
    "compassion is for other people", "compassion is for others",
    "not worthy of kindness", "not worthy of love", "not worthy of care",
    "unworthy of kindness", "unworthy of love",
    "too hard on myself", "never good enough for anyone",
)

# SIGNED 2026-08-19: Vee (clinical lead) — PO relay; record: 2026-08-19-vee-approval-record-signature-sheet.md, item 3. Class-level per the portability clause (deservingness-without-existence does NOT escalate; with-existence MUST); term lists = current implementation + permanent fixtures.
# Existence / death / absence content: ANY hit keeps the escalation (the must-STILL-fire boundary:
# "I don't deserve to be here", "I don't deserve to exist", "better off without me"). Deliberately
# broad substrings — over-blocking the deference is the safe direction (escalation stands).
_EXISTENCE_TERMS: tuple[str, ...] = (
    "to be here", "be here anymore", "being here", "deserve to live", "deserve to be alive",
    "to exist", "existing", "existence", "be alive", "stay alive", "be around", "being around",
    "without me", "if i was gone", "if i were gone", "be gone", "was never born", "were never born",
    "wake up", "disappear", "vanish", "die", "dying", "dead", "death", "my life", "this life",
    "end it", "be over", "not be anymore", "stop being",
)


def _norm(text: str) -> str:
    return (text or "").lower()


def _has_selfworth_signature(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _SELFWORTH_TERMS)


def _has_existence_content(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _EXISTENCE_TERMS)


def _has_harm_language(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _HARM_TERMS)


def should_restore_selfworth_presence(state) -> bool:
    """True when the deterministic self-worth presence deference applies this turn (pure;
    flag-checked by the caller, mirroring panic_override/grief_override).

    ALL must hold: intent_route returned crisis; safety_check was CLEAN (no crisis_flags — which
    includes si_passive's better-off-without-me surface and the cardiac Node-1 flag when active —
    no medical_flags, S3 below the hard threshold); a clear self-worth/deservingness signature is
    present; and there is NO existence content and NO harm-adjacency. Any existence hit, any harm
    hint, any safety_check signal, or absent self-worth signature -> False (escalation stands).
    """
    if state.get("primary_intent") != "crisis":
        return False
    if state.get("crisis_flags"):
        return False
    if state.get("medical_flags"):
        return False
    if float(state.get("s3_score") or 0.0) >= SELFWORTH_S3_SUB_THRESHOLD_CLEAN:
        return False
    text = state.get("message_en") or state.get("raw_message") or ""
    if _has_harm_language(text):
        return False
    if _has_existence_content(text):
        return False
    return _has_selfworth_signature(text)
