"""#311 salvage (per V's 2026-07-17 #324 ruling (a)): strengthen dbt_tipp's OWN recognition with the
severable, non-colliding acute triggers — WITHOUT removing grounding's bucketed phrases (those stay
per the signed 2026-06-13 decision). p2 ('shock my system') reaches TIPP; the bucket-lock is untouched.
"""
from sage_poc.skills.keyword_matcher import match_skill_keywords

# The severable additions must keyword-match dbt_tipp.
def test_severable_triggers_reach_dbt_tipp():
    for t in ("shock my system", "shock your system", "emotions out of control"):
        assert "dbt_tipp" in match_skill_keywords(t, "", "en"), f"{t!r} did not reach dbt_tipp"

# p2 (textbook TIPP, no grounding-bucketed phrase) -> dbt_tipp keyword. Closes #311's real concern.
def test_p2_reaches_dbt_tipp():
    p2 = "too agitated, adrenaline buzzing, need something intense and physical to shock my system"
    assert "dbt_tipp" in match_skill_keywords(p2, "", "en")

# Bucket-lock PRESERVED: the signed grounding phrases are NOT added to dbt_tipp — standalone, they must
# NOT keyword-match dbt_tipp (they route to grounding, per 2026-06-13 + V's C1/A3 ruling).
def test_grounding_bucketed_phrases_not_added_to_dbt_tipp():
    for t in ("need to calm down fast", "I need to calm down", "مشاعري أقوى من قدرتي", "محتاج أهدى بسرعة"):
        assert "dbt_tipp" not in match_skill_keywords(t, "", "en"), \
            f"{t!r} keyword-matched dbt_tipp — bucket-lock violated (must stay grounding)"
