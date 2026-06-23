"""Anti-overfit distinctness check (A2.3) — the inline gate for fan-out authoring.

Every authored utterance must be a *paraphrase* of the construct, never a near-verbatim of
a `target_presentations` string the router embeds — otherwise the eval reports false-green
against its own training data. At volume this is the rule most likely to erode, so it is a
per-case check: flag near-verbatim matches, but allow a short keyword appearing naturally
inside a longer sentence (that's normal language, not overfit).
"""
from sage_poc.routing_eval.distinctness import check_distinct, intra_set_redundancy


def test_verbatim_presentation_string_is_flagged():
    tps = {"behavioral_activation": ["no motivation", "lost motivation"]}
    distinct, j, tp, sid = check_distinct("no motivation", tps, max_jaccard=0.7)
    assert distinct is False
    assert tp == "no motivation"


def test_natural_paraphrase_is_distinct():
    tps = {"behavioral_activation": ["no motivation", "lost motivation", "can't get out of bed"]}
    distinct, *_ = check_distinct(
        "I've completely lost the drive to do anything and just stay in bed all day",
        tps, max_jaccard=0.7,
    )
    assert distinct is True


def test_short_keyword_inside_a_longer_sentence_is_allowed():
    tps = {"grief_loss": ["grief", "bereavement"]}
    distinct, *_ = check_distinct(
        "I'm struggling with grief after my father passed away last month",
        tps, max_jaccard=0.7,
    )
    assert distinct is True


def test_checks_against_all_skills_not_just_one():
    # a near-verbatim of ANY skill's presentation is flagged, not only the intended skill's
    tps = {"sleep_hygiene": ["can't sleep", "insomnia"], "worry_time": ["constant worry"]}
    distinct, j, tp, sid = check_distinct("constant worry", tps, max_jaccard=0.7)
    assert distinct is False and sid == "worry_time"


def test_intra_set_flags_mutual_near_duplicates():
    us = [
        "I can't get out of bed and I've stopped doing anything I enjoy",
        "I can't get out of bed and I've stopped doing the things I enjoy",  # near-dupe of #1
        "Money worries keep me awake every single night",                     # distinct
    ]
    pairs = intra_set_redundancy(us, max_jaccard=0.5)
    assert len(pairs) == 1
    assert pairs[0][0] >= 0.5


def test_intra_set_passes_when_all_distinct():
    us = [
        "everything feels like my fault even when it isn't",
        "I lie awake for hours unable to fall asleep",
        "I keep avoiding things because I'm scared of failing",
    ]
    assert intra_set_redundancy(us, max_jaccard=0.5) == []
