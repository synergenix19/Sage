"""Part A — §1c panic-grounding override (crisis-path). Vee-signed boundary 2026-07-28; SCOPED BACK 2026-07-30
(item-1: pure-panic only, derealization -> CF-010 referral, HR-family terms -> their own mechanisms) with the
item-3 cardiac deference (death-fear x air-hunger stays crisis). Rulings via PO relay, PR#374 packet.

Restores the Cardinal Rule that the deterministic crisis tier (safety_check) owns the crisis call. When
safety_check has CLEARED a turn but intent_route's LLM re-flags it crisis on panic phrasing, this deterministic
predicate force-grounds ONLY a clear panic disclosure carrying NO harm-adjacency — and DEFERS (escalation
stands) on any harm hint (Vee's conservative dial). It can never suppress a crisis safety_check caught, because
it fires only on a clean turn.

Matching is case-insensitive substring, same convention as CF-005 / the crisis lexicons. The harm set is
INTENT-based ("want to die"), deliberately NOT fear-of-dying ("going to die", "feel like dying") which is the
panic presentation itself. The §1c-B fixtures are the ship gate: every one carries a harm term and must escalate.
"""
from __future__ import annotations

from sage_poc.safety.s3_semantic import S3_THRESHOLD

# Override only ever considered on a turn safety_check scored BELOW the hard S3 crisis threshold.
S3_SUB_THRESHOLD_CLEAN: float = S3_THRESHOLD

# HARM-ADJACENCY — intent / passive-SI / self-harm / harm-to-others. Broad by design (conservative dial:
# any hint defers to escalation). NOTE the deliberate exclusions: "going to die", "feel like dying",
# "can't take this", "can't breathe" are PANIC, not harm — they are NOT here.
_HARM_TERMS: tuple[str, ...] = (
    "want to die", "wanna die", "want to be dead", "rather be dead", "better off dead",
    "don't want to live", "dont want to live", "not want to live", "no reason to live",
    "nothing to live for", "don't want to be here", "dont want to be here", "not want to be here",
    "kill myself", "killing myself", "end my life", "ending my life", "take my life",
    "end it all", "ending it all", "end it", "ending it",
    "want it to be over", "wants it to be over", "want this to be over", "it to be over",
    "hurt myself", "hurting myself", "harm myself", "harming myself", "cut myself", "cutting myself",
    "want to disappear", "wanna disappear", "disappear for good", "want to be gone", "want to vanish",
    "can't keep going", "cant keep going", "keep going like this", "can't go on", "cannot go on",
    "hurt them", "hurt him", "hurt her", "hurt someone", "kill them", "hurt people",
)

# PURE-PANIC signature — SCOPED BACK 2026-07-30 (item-1 ruling, Vee via PO relay, PR#374 packet):
# breathing / chest / heart / dizzy / trembling / closing-in / panic-attack clusters plus fear-of-death
# phrasing (the panic presentation itself). REMOVED: the derealization set ("detached", "unreal",
# "outside my body", "watching myself", "not real", "derealiz") — CF-010's referral territory (doc L151),
# and the HR-family-owned terms ("thoughts are racing", "mind is racing" CF-007; "losing my mind",
# "losing it" CF-009-adjacent; "out of control", "coming apart", "falling apart" non-somatic) — the
# disposition-ownership registry's four overlap findings. Escalation stands on all removed surface.
_PANIC_TERMS: tuple[str, ...] = (
    "can't breathe", "cant breathe", "can't get", "cant get", "get enough air", "get any air", "no air",
    "chest is tight", "chest tight", "tight chest", "chest is really tight",
    "heart is pounding", "heart pounding", "heart is racing", "heart racing", "racing heart",
    "heart is hammering", "hammering", "heart won't stop", "heart wont stop",
    "room is spinning", "spinning", "dizzy", "lightheaded",
    "closing in", "trembling", "shaking", "shaky",
    "panic attack", "panicking", "hyperventilat", "can't calm down", "cant calm down",
    "going to die", "gonna die", "feel like dying",
)

# CARDIAC-AMBIGUOUS deference — item-3 ruling 2026-07-30: the "going to die + can't breathe" class
# (death-fear AND air-hunger co-occurring, no harm word) STAYS AT CRISIS. A live probe proved D1's
# red-flag surface does not intercept panic air-hunger, so "no medical_flags" cannot certify this class
# medically clean — and Vee's Ruling 3 permits a downgrade only WITH a clean screen. No single-turn clean
# screen exists; therefore no downgrade. This knowingly reverses the 07-28 demonstrated anchor.
_DEATH_FEAR: tuple[str, ...] = (
    "going to die", "gonna die", "feel like dying", "about to die",
    "think i'm dying", "think im dying", "i'm dying", "im dying", "certain i'm dying",
)
_AIR_HUNGER: tuple[str, ...] = (
    "can't breathe", "cant breathe", "cannot breathe", "get enough air", "get any air", "no air",
    "can't get air", "cant get air", "short of breath", "struggling to breathe", "gasping",
)


def _norm(text: str) -> str:
    return (text or "").lower()


def _has_harm_language(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _HARM_TERMS)


def _has_panic_signature(text: str) -> bool:
    t = _norm(text)
    return any(term in t for term in _PANIC_TERMS)


def should_ground_over_crisis(state) -> bool:
    """True when the deterministic panic-grounding override applies this turn (pure; flag-checked by caller).

    ALL must hold: the turn is EN (detected_language == "en" or unset — non-EN turns never downgrade,
    translated text must not drive a crisis downgrade, the #329/#330 class); intent_route returned crisis;
    safety_check was CLEAN (no crisis_flags, S3 below the hard threshold, no medical_flags); a clear panic
    signature is present; and there is NO harm-adjacency. Any harm hint, any safety_check signal, absent
    panic signature, or a non-EN turn -> False (escalation stands).
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
    if float(state.get("s3_score") or 0.0) >= S3_SUB_THRESHOLD_CLEAN:
        return False
    text = state.get("message_en") or state.get("raw_message") or ""
    if _has_harm_language(text):
        return False
    t = _norm(text)
    if any(d in t for d in _DEATH_FEAR) and any(a in t for a in _AIR_HUNGER):
        return False  # cardiac-ambiguous class stays at crisis (item-3 ruling 2026-07-30)
    return _has_panic_signature(text)
