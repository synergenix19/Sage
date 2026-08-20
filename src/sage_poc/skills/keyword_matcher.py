"""Shared skill-trigger keyword matcher — the SINGLE source of keyword matching for both
Node 4 (skill_select's keyword tier) and the Node 2 keyword pre-pass (v7.2). Factored out so the
two nodes can never diverge (Constraint 2 of the pre-pass design). Triggers are single-sourced from
the skill JSONs' `target_presentations` (compiled once at load); there is no duplicated keyword list.

Match rule (identical to the original skill_select tier): case-insensitive substring, longest match
wins per skill. EN matched against message_en; Arabic-script keywords matched against raw_message
(a translated English string cannot contain Arabic-script triggers).
"""
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills import get_skill
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

# P2 Task 4: the former `_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}` preload
# (a SECOND frozen copy of every skill, parsed independently at this module's own import) is
# retired. This module now shares get_skill's ONE mtime-keyed, invalidatable cache instead
# (fix round 1, M2: importing the package still warms every registry id once -- see
# sage_poc/skills/__init__.py's warm-up loop -- so there is no NEW import-time cost here,
# just one shared warm-up through an invalidatable cache replacing three separate frozen
# ones). Triggers stay single-sourced from the skill JSONs' `target_presentations`: editing a
# trigger in the CMS updates the skill JSON -> both nodes recompile from it. No second
# keyword list to drift.


def match_skill_keywords(message_en: str, raw_message: str, detected_language: str) -> dict[str, int]:
    """Return {skill_id: longest_matched_keyword_length} across all non-skipped skills.
    Empty dict when nothing matches. Deterministic; no model call; sub-millisecond."""
    message_en = (message_en or "").lower()
    raw_message = raw_message or ""
    kw_matches: dict[str, int] = {}
    for skill_id in SKILL_REGISTRY:
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        skill = get_skill(skill_id)
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
