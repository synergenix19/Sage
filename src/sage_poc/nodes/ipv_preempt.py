"""E7 — §6a coercive-control / relationship-safety pre-emption (BOT BEHAVIOUR §6a).

Flag-gated (SAGE_IPV_PREEMPTION, default OFF) supplement to the approved CF-005 domestic_situation
lexicon. OFF -> {} : byte-identical v7 (only CF-005's 9+7 phrases fire, passive referral only).
ON  -> the 19 §6a-guard expansion phrases ALSO fire domestic_situation, so the route reaches the
       ≥95% recall the §6 pre-emption depends on. Mirrors safety_precedence.apply_precedence: a pure,
       call-time-flag-checked delta that safety_check_node merges into its return.

⚠️ CONSOLIDATION OBLIGATION (tracked in the E7 PR, NOT a memory): this flag-gated path is the SHIP
MECHANISM, not the destination. When the flag flips ON permanently (governed: E7 recall ≥95% +
clinician CMS approval, per Rohan's CF-005 workflow), the 19 phrases fold into CF-005 vNext via
CMS draft→review→approve and this module + its data file retire. domestic_situation must not live
under two governance regimes (approved CF-005 + this supplement) indefinitely.

Step 1 here is DETECTION only (domestic_situation fires on the 19). The active §6-skill pre-emption
consequence (scoped to the coaching_confrontation class; grounding/offload/sleep stay available) is
step 3 and lands separately behind the same flag.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "rules" / "data" / "safety" / "ipv_preempt_expansion.json"
)
_expansion = json.loads(_DATA_PATH.read_text())

# Public: the verbatim §6a expansion set. test_ipv_preempt asserts this equals the fixture's
# src=6a positives, so the production copy and the recall ground truth can never diverge.
EXPANSION_PHRASES: tuple[str, ...] = tuple(_expansion["phrases"])
_NORMALIZED: tuple[str, ...] = tuple(p.lower() for p in EXPANSION_PHRASES)


def _matches_expansion(text: str) -> bool:
    # Case-insensitive substring, consistent with CF-005 keyword matching. Naturalistic/paraphrase
    # matching is the same tracked debt as CF-005 (recall is measured on the verbatim fixture).
    normalized = (text or "").lower()
    return any(phrase in normalized for phrase in _NORMALIZED)


# §6 coaching_confrontation-class skills — deterministically contraindicated when domestic_situation
# is set. Encouraging a boundary/assertiveness script in a genuinely unsafe dynamic can increase risk
# (§6a guard). Scoped: ONLY these; grounding/offload/sleep stay available (don't punish disclosure).
#
# ⚠️ PRE-E2 BRIDGE — TRACKED OBLIGATION (same discipline as the CF-005 consolidation above; note in
# the E7 PR). This literal set is a stopgap until E2's coaching_confrontation contraindication class
# lands. When E2 ships, REPLACE this set with class membership so §6 skills added later — e.g. the
# planned §6c Draft/Role-Play skill from the content inventory — inherit the guard AUTOMATICALLY
# instead of requiring someone to remember to update a Python set here.
COACHING_CONFRONTATION_SKILLS: frozenset[str] = frozenset({
    "assertive_communication",
    "interpersonal_effectiveness",
})


def ipv_preempt_active(state) -> bool:
    """True when E7 §6 pre-emption is in force this turn: flag ON AND domestic_situation set.

    domestic_situation is immutable within a session (flag_lifecycle_config), so once disclosed the
    suppression persists across turns without any per-turn re-detection — the property step 4 proves.
    """
    from sage_poc import config  # noqa: PLC0415 — call-time read of the kill-switch

    return config.IPV_PREEMPTION_ENABLED and "domestic_situation" in (
        state.get("clinical_flags") or []
    )


def apply_ipv_preempt(state) -> dict:
    """Flag-gated state delta for safety_check_node to merge into its return.

    Flag OFF -> {} (byte-identical). Flag ON + an expansion phrase present -> adds domestic_situation
    to clinical_flags (union; never duplicates or drops existing flags). Reads config at call time so
    the kill-switch is honoured live and monkeypatchable in tests.
    """
    from sage_poc import config  # noqa: PLC0415 — call-time read of the kill-switch

    if not config.IPV_PREEMPTION_ENABLED:
        return {}
    text = state.get("message_en") or state.get("raw_message") or ""
    if not _matches_expansion(text):
        return {}
    flags = list(state.get("clinical_flags") or [])
    if "domestic_situation" not in flags:
        flags.append("domestic_situation")
    return {"clinical_flags": flags}
