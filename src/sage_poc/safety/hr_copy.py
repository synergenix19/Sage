"""HR-1 Stage 2 — deterministic variant-pool copy for the high_risk_response terminal.

Refines Task 3's single fixed-copy strings (config.py's old HR_DISTRESS_QUESTION /
HR_SUPPORTIVE_MESSAGE / HR_REDIRECT_HIGHER_LEAD / HR_REDIRECT_LOWER / HR_REASK) into
POOLS of clinician-ratifiable variants, picked deterministically per (session_id,
slot_key). NO runtime LLM anywhere in this module: pick_hr_variant is a pure index
lookup into a fixed tuple of literal strings, the same "never LLM-rendered,
crisis_copy_templated-style" discipline as the rest of the safety copy.

# DRAFT — pending clinician ratification; do not flip SAGE_HIGH_RISK_TERMINAL live
# until these carry sign-off. The five POOL constants below are offline-authored
# candidates (source: the HR-1 Stage 2 clinician ratification packet's variant-draft
# pass), shipped the same way CF-007/008/009 ship active:false/unsigned pending
# ratification in clinical_flag_patterns.json: present in the tree, wired end-to-end,
# inert until a human sign-off promotes them. SAGE_HIGH_RISK_TERMINAL is already
# default-OFF (config.py), so nothing here reaches a user until that flag is flipped
# AND the pools below carry an approved_by note, matching L0_persona.json /
# crisis_content/*.json convention.

Two placeholder families, resolved at different points:
  - ``{{crisis_emergency}}`` / ``{{crisis_number}}`` / ``{{crisis_label}}`` /
    ``{{crisis_hours}}`` resolve via crisis_copy.resolve_crisis_placeholders, same
    single-sourced CRISIS_CONFIG path as every other crisis string in the codebase.
  - ``{{first_name}}`` is the ONLY other permitted interpolation (name-only
    personalization, §5). Resolved by pick_hr_variant itself, never by the LLM: if no
    first name is available in state, the selector does not pick a name-bearing
    variant in the first place (falls back to the pool's name-free variants), so the
    placeholder is structurally absent from the returned string in the common case.
    _strip_first_name_placeholder is a defensive backstop only, exercised when a pool
    has no name-free variant to fall back to.

No em dashes anywhere in this module (project convention for copy that could reach an
LLM prompt or a user-facing string).
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# DRAFT candidate pools (verbatim from the ratification packet's variant draft).
# Order is significant only in that it fixes the index space pick_hr_variant hashes
# into; it carries no priority/preference ranking.
# ---------------------------------------------------------------------------

# Slot 1 -- the one distress question (§1). Also reused (warmed) as the basis for the
# single re-ask pool below.
HR_DISTRESS_QUESTION_POOL: tuple[str, ...] = (
    "On a scale of 0 to 10, how distressing does this feel for you right now?",
    "{{first_name}}, if 0 means calm and 10 means unbearable, where would you put "
    "yourself right now?",
    "I want to understand how much this is weighing on you right now. On a scale "
    "of 0 to 10, what number feels right?",
    "Can you give me a number, 0 to 10, for how distressing this is for you right now?",
)

# Slot 2 -- supportive message (§2): thank-you + difficulty acknowledgment + bridge to
# professional support, sent once alongside the branch redirect.
HR_SUPPORTIVE_MESSAGE_POOL: tuple[str, ...] = (
    "Thank you for telling me what's going on for you. What you're describing "
    "sounds really difficult, and I want to make sure you get support from "
    "someone who can help properly with this.",
    "Thank you for trusting me with this. I can hear how hard it's been, and I "
    "want you to have support from someone who can really help.",
    "{{first_name}}, thank you for telling me. This sounds like a lot to carry "
    "right now, and I want to make sure you get help from someone who's trained "
    "for this.",
    "I'm glad you told me what's going on. It sounds really hard right now, and "
    "you deserve support from someone who can properly help with this.",
)

# Slot 3 -- higher-severity redirect (§3, encourage 999/ER now). LEAD-IN only: the
# node appends the actual UAE resource directory separately (select_crisis_resources()
# / CRISIS_CONFIG), so the resource set stays single-sourced and never duplicated here.
HR_REDIRECT_HIGHER_POOL: tuple[str, ...] = (
    "Please call {{crisis_emergency}} right now, or get to your nearest emergency "
    "department. This needs help in person, right away, and I want you safe.",
    "{{first_name}}, I think this needs more help than I can give right now. "
    "Please call {{crisis_emergency}}, or go to the nearest emergency room right "
    "away.",
    "This is serious enough that I want you to get help in person now. Call "
    "{{crisis_emergency}}, or head to your nearest ER, please don't wait on this.",
    "Right now, the safest step is calling {{crisis_emergency}} or going "
    "straight to the nearest emergency department. Please do that now, I'm glad "
    "you're not alone in this.",
)

# Slot 4 -- lower-severity redirect (§3, see a doctor/mental health professional
# promptly). Prompt but non-emergency framing; no content echo.
HR_REDIRECT_LOWER_POOL: tuple[str, ...] = (
    "This is something a doctor or mental health professional should look at "
    "with you soon. Please reach out to one in the next day or so.",
    "{{first_name}}, I'd feel better knowing a doctor or mental health "
    "professional is looking at this with you soon. Can you reach out to one "
    "in the next few days?",
    "I think it's worth getting this in front of a doctor or mental health "
    "professional soon, they can help in ways I can't.",
    "This deserves a closer look from a doctor or mental health professional. "
    "Please try to see one soon.",
)

# Slot 5 -- the single gentle re-ask (T2 non-answer). Warm re-ask of the SAME §1
# question only; never probes content, never stacked with a second question.
HR_REASK_POOL: tuple[str, ...] = (
    "I hear you. Just so I understand, on a scale of 0 to 10, how distressing "
    "is this for you right now?",
    "{{first_name}}, I just need one number from you, 0 to 10, for how "
    "distressing this feels right now.",
    "Take your time. Somewhere between 0 and 10, how distressing is this for "
    "you right now?",
    "One more time, just so I know where you're at: 0 to 10, how distressing "
    "is this right now?",
)


# ---------------------------------------------------------------------------
# Deterministic selector
# ---------------------------------------------------------------------------

_FIRST_NAME_PLACEHOLDER = "{{first_name}}"


def _stable_hash(text: str) -> int:
    """Process-independent, non-salted hash. Python's builtin hash() is salted per
    process (PYTHONHASHSEED) precisely to resist DoS attacks on dict keys -- exactly
    the property that would break "same session_id+slot -> same variant every time"
    across server restarts / worker processes / audit replay. sha256 over the exact
    utf-8 bytes has none of that: same input, same output, forever, on any machine.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _strip_first_name_placeholder(text: str) -> str:
    """Defensive backstop: remove a `{{first_name}}` placeholder with no dangling
    punctuation, for the case where a candidate pool has no name-free variant to fall
    back to (none of the five shipped pools hit this today -- each has 3 of 4
    variants name-free -- but pick_hr_variant must not be able to leak a raw
    placeholder into a delivered message if a future pool ever does)."""
    if _FIRST_NAME_PLACEHOLDER not in text:
        return text
    lead_form = _FIRST_NAME_PLACEHOLDER + ", "
    if text.startswith(lead_form):
        rest = text[len(lead_form):]
        return (rest[:1].upper() + rest[1:]) if rest else rest
    # Mid-sentence (or any other position): drop the placeholder plus one adjacent
    # comma/space on either side, then collapse any resulting double space.
    cleaned = re.sub(r"\s*,?\s*" + re.escape(_FIRST_NAME_PLACEHOLDER) + r"\s*,?\s*", " ", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def pick_hr_variant(
    pool: tuple[str, ...],
    session_id: str | None,
    slot_key: str,
    first_name: str | None = None,
) -> str:
    """Deterministically pick one variant from *pool* for (session_id, slot_key).

    index = stable_hash(f"{session_id}|{slot_key}") % len(candidate_pool)

    Reproducible: the same (session_id, slot_key, first_name-presence) always yields
    the same variant -- required both for audit (the delivered string must be
    re-derivable from the logged session_id/slot) and for within-session consistency
    (a re-ask reuses the same distress-question voice as the original ask). Varies
    across session_id so not every user sees the identical wording.

    Name-only personalization (§5): if *first_name* is falsy, the candidate pool is
    first narrowed to variants that do NOT contain `{{first_name}}` (falling back to
    the full pool only if that narrowing would leave nothing, which none of the
    shipped pools trigger) -- the selector never PICKS a name-bearing variant when
    there is no name to fill it with, rather than picking one and hoping the strip
    step is invoked. When *first_name* is provided, the full pool is eligible and the
    placeholder is interpolated verbatim (nothing else is ever substituted).
    """
    if not pool:
        raise ValueError("pick_hr_variant: pool must be non-empty")

    if first_name:
        candidates = pool
    else:
        name_free = tuple(v for v in pool if _FIRST_NAME_PLACEHOLDER not in v)
        candidates = name_free or pool

    index = _stable_hash(f"{session_id}|{slot_key}") % len(candidates)
    variant = candidates[index]

    if first_name:
        return variant.replace(_FIRST_NAME_PLACEHOLDER, first_name)
    return _strip_first_name_placeholder(variant)
