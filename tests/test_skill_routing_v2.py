"""SKILL_ROUTING_V2 retrieval-core, cut 1: exemplar embedding + A1 referral exclusion.

The §6.1 "change that does the real work": embed each skill's target_presentations as
exemplar anchors (not just semantic_description + semantic_anchors). v2 also excludes the
referral pathways (psychotic_referral, post_crisis_check_in) from the skill_select index,
per the FROZEN A1 boundary (deterministic-path-only). v1 (current prod path) is unchanged.

Pure anchor-building — no model load.
"""
from sage_poc.nodes.skill_select import _SKILLS, build_anchor_pairs

_SID = "cbt_thought_record"


def _texts_for(sid, *, include_exemplars):
    return [t for s, t in build_anchor_pairs(_SKILLS, include_exemplars=include_exemplars) if s == sid]


def test_v2_adds_exactly_the_target_presentations():
    v1 = _texts_for(_SID, include_exemplars=False)
    v2 = _texts_for(_SID, include_exemplars=True)
    assert len(v2) == len(v1) + len(_SKILLS[_SID].target_presentations)


def test_v2_index_contains_each_target_presentation():
    v2 = _texts_for(_SID, include_exemplars=True)
    for tp in _SKILLS[_SID].target_presentations:
        assert tp in v2


def test_v1_unchanged_description_present_no_exemplars():
    v1 = _texts_for(_SID, include_exemplars=False)
    assert _SKILLS[_SID].semantic_description in v1
    assert len(v1) == (1 if _SKILLS[_SID].semantic_description else 0) + len(_SKILLS[_SID].semantic_anchors)


def test_v2_excludes_referral_pathways_from_index():
    sids = {s for s, _ in build_anchor_pairs(_SKILLS, include_exemplars=True)}
    assert "psychotic_referral" not in sids
    assert "post_crisis_check_in" not in sids


def test_v1_does_not_exclude_referrals_prod_behavior_unchanged():
    # v1 (current prod) must NOT change: referral skills stay in the index as before
    # (unless already in KEYWORD_SEMANTIC_SKIP). The A1 exclusion is a v2-only policy.
    from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
    sids = {s for s, _ in build_anchor_pairs(_SKILLS, include_exemplars=False)}
    for ref in ("psychotic_referral", "post_crisis_check_in"):
        if ref not in KEYWORD_SEMANTIC_SKIP and _SKILLS[ref].semantic_description:
            assert ref in sids
