"""S2a — deterministic grief-presence deference (crisis-path). BUILT INERT 2026-08-04 — boundary sheet
pending Vee's ruling (2026-08-04-grief-deference-boundary-to-vee.md); flag default OFF, byte-identical.

The inverse of Part A's shape: intent_route's LLM re-flags a safety_check-CLEAN fresh-grief disclosure as
crisis ("passed away and I can't cope" → crisis card — an emergency-framed response to a bereaved user,
measured live 1/5, diagnosis PR#380). Vee's S2a ruling is presence-mode grief_loss, not the crisis card.
This predicate restores the deterministic clean verdict for a clear bereavement disclosure carrying NO
harm-adjacency — and DEFERS (escalation stands) on any harm hint, the same conservative dial as Part A.

Single-sourcing (the cardiac pattern): the harm set is IMPORTED from panic_override._HARM_TERMS — the
same harm language that stops panic-grounding stops grief-deference, definitionally, no drift. Note what
that inherits: "can't keep going" / "can't go on" are harm terms, so grief + "I can't go on" ESCALATES;
plain "I can't cope" is not a harm term and defers. Fires only on a safety_check-clean turn, so it can
never suppress a crisis the deterministic tier caught — including the cardiac Node-1 flag when active.

_GRIEF_TERMS is the PROPOSED bereavement signature — Vee confirms/extends/narrows on the boundary sheet.
Deliberately loss-of-person phrasings only (no bare "lost my", which sweeps jobs/keys/pets-adjacent);
matching is case-insensitive substring, the crisis-lexicon convention. EN-only (AR rides the AR track).
"""
from __future__ import annotations

from sage_poc.nodes.panic_override import _HARM_TERMS
from sage_poc.safety.s3_semantic import S3_THRESHOLD

GRIEF_S3_SUB_THRESHOLD_CLEAN: float = S3_THRESHOLD

_GRIEF_TERMS: tuple[str, ...] = (
    "passed away", "passed on", "she died", "he died", "they died", "died last", "died this",
    "death of my", "her death", "his death", "their death", "the funeral", "his funeral", "her funeral",
    "we buried", "i buried", "lost my mother", "lost my mum", "lost my mom", "lost my father",
    "lost my dad", "lost my husband", "lost my wife", "lost my brother", "lost my sister",
    "lost my son", "lost my daughter", "lost my friend", "lost my best friend",
    "lost my grandmother", "lost my grandma", "lost my grandfather", "lost my grandpa",
    "since the loss", "since we lost", "since i lost", "grieving", "my grief", "the grief",
    "bereaved", "bereavement", "no longer with us",
)


def _norm(text: str) -> str:
    return (text or "").lower()


def _has_grief_signature(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _GRIEF_TERMS)


def _has_harm_language(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _HARM_TERMS)


def should_defer_grief_over_crisis(state) -> bool:
    """True when the deterministic grief-presence deference applies this turn (pure; flag-checked by
    the caller, mirroring panic_override).

    ALL must hold: the turn is EN (detected_language == "en" or unset — non-EN turns never downgrade,
    translated text must not drive a crisis downgrade, the #329/#330 class); intent_route returned crisis;
    safety_check was CLEAN (no crisis_flags — which includes the cardiac Node-1 flag when active — no
    medical_flags, S3 below the hard threshold); a clear bereavement signature is present; and there is
    NO harm-adjacency. Any harm hint, any safety_check signal, absent grief signature, or a non-EN turn
    -> False (escalation stands).
    """
    if (state.get("detected_language") or "en") != "en":
        return False   # EN-only term lists; AR rides the AR track (docstring contract).
                       # Translated text must not drive a crisis downgrade (#329/#330 class).
    if state.get("primary_intent") != "crisis":
        return False
    if state.get("crisis_flags"):
        return False
    if state.get("medical_flags"):
        return False
    if float(state.get("s3_score") or 0.0) >= GRIEF_S3_SUB_THRESHOLD_CLEAN:
        return False
    text = state.get("message_en") or state.get("raw_message") or ""
    if _has_harm_language(text):
        return False
    return _has_grief_signature(text)
