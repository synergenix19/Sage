"""Anti-overfit distinctness check (A2.3).

An authored eval utterance must be a paraphrase of the construct, never a near-verbatim of a
`target_presentations` string the router embeds. Token-Jaccard against every skill's
presentations catches near-verbatim matches (Jaccard ≥ threshold) while leaving a short
keyword used naturally inside a longer sentence distinct (low Jaccard). Used per-case in the
fan-out so volume can't quietly reintroduce the overfit the rule exists to prevent.
"""
from __future__ import annotations

import re


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[\w']+", s.lower()))


def load_all_target_presentations() -> dict[str, list[str]]:
    """Map skill_id -> its target_presentations (the strings the router embeds)."""
    from sage_poc.skill_ids import SKILL_REGISTRY
    from sage_poc.skills.schema import load_skill
    return {sid: load_skill(sid).target_presentations for sid in SKILL_REGISTRY}


def check_distinct(
    utterance: str,
    target_presentations_by_skill: dict[str, list[str]],
    *,
    max_jaccard: float = 0.7,
) -> tuple[bool, float, str | None, str | None]:
    """Return (is_distinct, worst_jaccard, nearest_presentation, nearest_skill).

    Not distinct when the utterance's token-Jaccard with any skill's presentation reaches
    max_jaccard (near-verbatim). Checks against ALL skills — a near-copy of any embedded
    string is overfit, not only the intended skill's.
    """
    u = _tokens(utterance)
    worst_j, worst_tp, worst_sid = 0.0, None, None
    if u:
        for sid, tps in target_presentations_by_skill.items():
            for tp in tps:
                t = _tokens(tp)
                if not t:
                    continue
                j = len(u & t) / len(u | t)
                if j > worst_j:
                    worst_j, worst_tp, worst_sid = j, tp, sid
    return (worst_j < max_jaccard, worst_j, worst_tp, worst_sid)
