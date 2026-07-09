"""Shared skill-trigger keyword matcher — the SINGLE source of keyword matching for both
Node 4 (skill_select's keyword tier) and the Node 2 keyword pre-pass (v7.2). Factored out so the
two nodes can never diverge (Constraint 2 of the pre-pass design). Triggers are single-sourced from
the skill JSONs' `target_presentations` (compiled once at load); there is no duplicated keyword list.

Match rule (identical to the original skill_select tier): case-insensitive substring, longest match
wins per skill. EN matched against message_en; Arabic-script keywords matched against raw_message
(a translated English string cannot contain Arabic-script triggers).
"""
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

# Compiled once at import from the same registry skill_select uses. Editing a trigger in the CMS
# updates the skill JSON -> both nodes recompile from it. No second keyword list to drift.
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}


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
    return kw_matches


def ranked_skill_matches(message_en: str, raw_message: str, detected_language: str) -> list[str]:
    """Skill ids ranked by longest matched keyword (most specific first)."""
    kw = match_skill_keywords(message_en, raw_message, detected_language)
    return [sid for sid, _ in sorted(kw.items(), key=lambda x: x[1], reverse=True)]
