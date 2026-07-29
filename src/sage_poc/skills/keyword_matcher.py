"""Shared skill-trigger keyword matcher — the SINGLE source of keyword matching for both
Node 4 (skill_select's keyword tier) and the Node 2 keyword pre-pass (v7.2). Factored out so the
two nodes can never diverge (Constraint 2 of the pre-pass design). Triggers are single-sourced from
the skill JSONs' `target_presentations` (compiled once at load); there is no duplicated keyword list.

Match rule (identical to the original skill_select tier): case-insensitive substring, longest match
wins per skill. EN matched against message_en; Arabic-script keywords matched against raw_message
(a translated English string cannot contain Arabic-script triggers).
"""
import logging
import os

from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

# Compiled once at import from the same registry skill_select uses. Editing a trigger in the CMS
# updates the skill JSON -> both nodes recompile from it. No second keyword list to drift.
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

# ---- TEMPORARY DIAGNOSTIC (K3/K4 prod-only no-offer, 2026-07-29) — REVERT AFTER PROBE ----
# Scoped debug for the deploy-owner-authorized probe into why K3/K4 keywords are deployed but inert
# on prod while reproducing nowhere locally. PRIVACY: gated flag-OFF by default AND only ever logs
# when the ORIGINAL raw_message is EXACTLY one of these hardcoded benign probe phrases — it can never
# capture arbitrary user content. This is a probe instrument, not a resident capability; it is removed
# in the same session (time-boxed with the deploy). See governance record 2026-07-29-k3k4-*.
_KWDBG_LOG = logging.getLogger("sage.kwdbg")
_KWDBG_PROBES = {
    "my mood has dropped", "i have pulled back from everyone",   # K1 (works on prod) — controls
    "no motivation", "set boundaries",                            # pre-#377 controls (work on prod)
    "i want to reconnect with people", "reconnect",              # K4 (inert on prod)
    "i need to stop crossing a line",                            # K3 (inert on prod)
}


def _kwdbg_enabled() -> bool:
    return os.getenv("SAGE_KEYWORD_MATCH_DEBUG", "false").lower() == "true"


def _kwdbg(where: str, message_en: str, raw_message: str, **fields) -> None:
    if not _kwdbg_enabled():
        return
    probe = (raw_message or message_en or "").lower().strip()
    if probe not in _KWDBG_PROBES:   # never log anything but a registered probe phrase
        return
    extra = " ".join(f"{k}={v!r}" for k, v in fields.items())
    _KWDBG_LOG.warning("[KWDBG] where=%s raw=%r msg_en=%r %s",
                       where, (raw_message or "").lower().strip(),
                       (message_en or "").lower().strip(), extra)
# ---- END TEMPORARY DIAGNOSTIC ----


def match_skill_keywords(message_en: str, raw_message: str, detected_language: str) -> dict[str, int]:
    """Return {skill_id: longest_matched_keyword_length} across all non-skipped skills.
    Empty dict when nothing matches. Deterministic; no model call; sub-millisecond."""
    message_en = (message_en or "").lower()
    raw_message = raw_message or ""
    kw_matches: dict[str, int] = {}
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            kw_lower = keyword.lower()
            if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
                if len(kw_lower) > kw_matches.get(skill_id, 0):
                    kw_matches[skill_id] = len(kw_lower)
    if _kwdbg_enabled():   # TEMPORARY DIAGNOSTIC — REVERT AFTER PROBE
        _ba = _SKILLS.get("behavioral_activation")
        _ie = _SKILLS.get("interpersonal_effectiveness")
        _ba_tp = [t.lower() for t in _ba.target_presentations] if _ba else []
        _ie_tp = [t.lower() for t in _ie.target_presentations] if _ie else []
        _kwdbg("match_skill_keywords", message_en, raw_message,
               detected_language=detected_language, kw_matches=kw_matches,
               BA_tp_count=len(_ba_tp), IE_tp_count=len(_ie_tp),
               reconnect_in_BA=("reconnect" in _ba_tp),
               want_to_reconnect_in_BA=("want to reconnect" in _ba_tp),
               mood_has_dropped_in_BA=("mood has dropped" in _ba_tp),
               crossing_a_line_in_IE=("crossing a line" in _ie_tp),
               stop_crossing_a_line_in_IE=("stop crossing a line" in _ie_tp))
    return kw_matches


def ranked_skill_matches(message_en: str, raw_message: str, detected_language: str) -> list[str]:
    """Skill ids ranked by longest matched keyword (most specific first)."""
    kw = match_skill_keywords(message_en, raw_message, detected_language)
    return [sid for sid, _ in sorted(kw.items(), key=lambda x: x[1], reverse=True)]
