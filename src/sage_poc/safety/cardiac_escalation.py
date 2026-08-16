"""Deterministic cardiac-ambiguous escalation (Node-1). BUILT INERT 2026-07-31 — activation gated on
Vee's one-tick (the unconditional realization of her item-3 ruling, 2026-07-30, PO relay).

The class: death-fear AND air-hunger co-occurring ("going to die + can't breathe"). Vee's item-3 ruled it
STAYS AT CRISIS (no downgrade without a clean medical screen; no single-turn clean screen exists). The
override-level deference (panic_override, increment 2) covers only the intent=crisis door; the measured
N=20 characterization (2026-07-30, record in inc2 addendum) found the pinned LLM routes the demonstrated
phrasing to freeflow with NO crisis resources in 6/20 fresh drives, time-correlated (window-dependent).
This Node-1 rule escalates the class BEFORE any LLM touches the turn — unconditional, window-independent.

Pattern SOURCE is panic_override's _DEATH_FEAR/_AIR_HUNGER tuples (imported, never copied) so the
override's deference and this escalation can never drift apart: the same conjunction the override refuses
to ground is the one this rule escalates. Registered in disposition_ownership.json (cardiac_escalation).

EN-only lexicon (the characterized class is English; AR rides the AR track per the standing honesty rule).
"""
from sage_poc.nodes.panic_override import _AIR_HUNGER, _DEATH_FEAR

CARDIAC_FLAG_ID = "cardiac_ambiguous_deterministic"


def cardiac_ambiguous_present(message_en: str, raw_message: str) -> bool:
    """True when death-fear AND air-hunger co-occur in the turn's text (case-insensitive substring,
    same convention as the crisis lexicons). Both must be present; either alone is the ordinary panic
    presentation and stays with its existing routing (the signed grounding capability survives)."""
    t = f"{message_en or ''} {raw_message or ''}".lower()
    return any(d in t for d in _DEATH_FEAR) and any(a in t for a in _AIR_HUNGER)
