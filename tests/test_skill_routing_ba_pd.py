import pytest
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.nodes.skill_select import _SKILLS
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP


def _tier1_match(phrase: str) -> str | None:
    """Mirror production Tier 1 scan: iterate SKILL_REGISTRY order, skip KEYWORD_SEMANTIC_SKIP,
    return first skill whose keyword is a substring of phrase (case-insensitive).
    Uses SKILL_REGISTRY explicitly — not _SKILLS.keys() — so scan order is guaranteed stable."""
    phrase_lower = phrase.lower()
    for sid in SKILL_REGISTRY:
        if sid not in _SKILLS or sid in KEYWORD_SEMANTIC_SKIP:
            continue
        for kw in _SKILLS[sid].target_presentations:
            if kw.lower() in phrase_lower:
                return sid
    return None


@pytest.mark.xfail(
    reason="6 pre-existing exact duplicates pending separate clinical review; "
           "promote to hard gate after pre-existing cleanup PR ships",
    strict=False,
)
def test_no_cross_skill_keyword_duplicates():
    """Exact-duplicate invariant: no keyword string appears in more than one skill's
    target_presentations. A duplicate creates scan-order-dependent routing."""
    kw_to_skills: dict[str, list[str]] = {}
    for sid in SKILL_REGISTRY:
        if sid not in _SKILLS or sid in KEYWORD_SEMANTIC_SKIP:
            continue
        for kw in _SKILLS[sid].target_presentations:
            kw_to_skills.setdefault(kw.lower(), []).append(sid)
    dupes = {kw: skills for kw, skills in kw_to_skills.items() if len(skills) > 1}
    assert not dupes, f"Keywords in multiple skills (scan-order dependent): {dupes}"


# Canonical set of known substring collisions (as of 2026-06-07 full-pairwise audit).
# Format: (short_keyword, skill_owning_short, long_keyword_shadowed, skill_owning_long).
# Each entry is a pre-existing issue documented in the 26-collision audit table.
# If an entry is resolved, remove it here. If a new collision is added, the test fails.
_KNOWN_SUBSTRING_SHADOWS: frozenset[tuple[str, str, str, str]] = frozenset({
    ("failure",                     "cbt_thought_record",      "i am a failure",                              "act_psychological_flexibility"),
    ("worthless",                   "cbt_thought_record",      "i am worthless",                              "act_psychological_flexibility"),
    ("فاشل",                        "cbt_thought_record",      "أنا فاشل",                                    "act_psychological_flexibility"),
    ("مو كافي",                     "cbt_thought_record",      "الراتب مو كافي",                              "financial_anxiety"),
    ("مو زين",                      "cbt_thought_record",      "نومي مو زين",                                 "sleep_hygiene"),
    ("مو زين",                      "cbt_thought_record",      "مزاجي مو زين",                                "mood_check_in"),
    ("مو زين",                      "cbt_thought_record",      "تفكيري مو زين",                               "cognitive_restructuring"),
    ("panic",                       "grounding_5_4_3_2_1",     "explain panic attacks",                       "psychoed_anxiety"),
    ("panic",                       "grounding_5_4_3_2_1",     "panic attack explained",                      "psychoed_anxiety"),
    ("panic",                       "grounding_5_4_3_2_1",     "what is panic",                               "psychoed_anxiety"),
    ("panic",                       "grounding_5_4_3_2_1",     "why do i get panic attacks",                  "psychoed_anxiety"),
    ("panic",                       "grounding_5_4_3_2_1",     "why do i panic",                              "psychoed_anxiety"),
    ("panic attack",                "grounding_5_4_3_2_1",     "explain panic attacks",                       "psychoed_anxiety"),
    ("panic attack",                "grounding_5_4_3_2_1",     "panic attack explained",                      "psychoed_anxiety"),
    ("panic attack",                "grounding_5_4_3_2_1",     "why do i get panic attacks",                  "psychoed_anxiety"),
    ("خايف",                        "grounding_5_4_3_2_1",     "خايف أخسر شغلتي",                             "financial_anxiety"),
    ("تعبان",                       "mood_check_in",           "جسمي تعبان من التوتر",                        "progressive_muscle_relaxation"),
    ("تعبان",                       "mood_check_in",           "دايم تعبان وما في طاقة",                      "psychoed_stress"),
    ("how to say no",               "assertive_communication", "i don't know how to say no",                  "interpersonal_effectiveness"),
    ("i know it's irrational but",  "cognitive_restructuring", "i know it's irrational but i still feel it",  "act_psychological_flexibility"),
    # Task 3 (2026-06-10): "i keep catastrophizing" and "always catastrophizing" are intentional
    # longer keywords in cognitive_restructuring that shadow bare "catastrophizing" in
    # cbt_thought_record. Clinically acceptable — both skills address cognitive distortions.
    ("catastrophizing",             "cbt_thought_record",      "i keep catastrophizing",                      "cognitive_restructuring"),
    ("catastrophizing",             "cbt_thought_record",      "always catastrophizing",                      "cognitive_restructuring"),
})


def test_no_new_substring_keyword_shadowing():
    """Substring-shadowing invariant: no NEW keyword A in skill X shadows keyword B in skill Y
    (where A is a strict substring of B and X is scanned before Y).

    Tests the dominant failure mode (20 of 26 known collisions are substring, not exact-duplicate).
    The 20 pre-existing collisions are documented in _KNOWN_SUBSTRING_SHADOWS above.
    This test passes if current collisions ⊆ known — i.e., no new ones were added.
    When a known collision is resolved, remove its entry from _KNOWN_SUBSTRING_SHADOWS.
    """
    scan_order = [s for s in SKILL_REGISTRY if s not in KEYWORD_SEMANTIC_SKIP and s in _SKILLS]
    all_kw = [
        (kw.lower(), sid, scan_order.index(sid))
        for sid in scan_order
        for kw in _SKILLS[sid].target_presentations
    ]

    current_shadows: set[tuple[str, str, str, str]] = set()
    for kw_short, sid_short, idx_short in all_kw:
        for kw_long, sid_long, idx_long in all_kw:
            if sid_short == sid_long:
                continue
            if kw_short in kw_long and kw_short != kw_long and idx_short < idx_long:
                current_shadows.add((kw_short, sid_short, kw_long, sid_long))

    new_collisions = current_shadows - _KNOWN_SUBSTRING_SHADOWS
    assert not new_collisions, (
        f"New substring-shadowing collisions introduced — add to known or fix: {new_collisions}"
    )


@pytest.mark.parametrize("phrase,expected_skill", [
    # BA-intent phrases — must route to BA after fix
    ("I used to enjoy things but I stopped",          "behavioral_activation"),
    ("I've lost interest in things I used to enjoy",  "behavioral_activation"),
    ("I've lost interest in the things I used to do", "behavioral_activation"),
    ("I stopped doing the things I used to love",     "behavioral_activation"),
    ("no motivation to do anything I used to enjoy",  "behavioral_activation"),
    ("I lost all interest in activities",             "behavioral_activation"),
    ("activities I used to love feel pointless",      "behavioral_activation"),
    # PD education-seeking — must still route to PD after fix
    ("what is depression",                            "psychoed_depression"),
    ("am I depressed or just sad",                    "psychoed_depression"),
    ("explain the cognitive triad",                   "psychoed_depression"),
    ("why do I feel flat",                            "psychoed_depression"),
    ("teach me about depression",                     "psychoed_depression"),
])
def test_ba_pd_routing(phrase, expected_skill):
    result = _tier1_match(phrase)
    assert result == expected_skill, (
        f"'{phrase}' → {result!r}, expected {expected_skill!r}"
    )


# Activity-deficit / anhedonia colloquial phrasings observed in a real test-user
# session (session 40a8ba18, 2026-06-07): the user disclosed loss of interest and
# "nothing to do" across turns but no existing BA keyword matched his exact wording,
# so Tier 1 never fired and Tier 2 surfaced grounding instead of BA. These are his
# verbatim turn fragments plus close paraphrases; all must route to BA.
@pytest.mark.parametrize("phrase", [
    "there's nothing for us to do",
    "I am not able to do anything that interests me",
    "no activities that interest me or excite me",
    "there's no activities that interest me",
    "I don't feel like doing anything anymore",
    "we have no hobbies and nothing to do today",
])
def test_ba_anhedonia_colloquial_routing(phrase):
    assert _tier1_match(phrase) == "behavioral_activation", (
        f"'{phrase}' → {_tier1_match(phrase)!r}, expected 'behavioral_activation'"
    )


# False-positive guard: the high-frequency idiom "nothing to do with X" must NOT be
# read as activity-deficit. This is why the bare keyword "nothing to do" was rejected
# during design (it false-matched "it has nothing to do with my job").
@pytest.mark.parametrize("phrase", [
    "it has nothing to do with my job",
    "that has nothing to do with it",
    "there is nothing to do about the weather now",
])
def test_ba_idiom_not_misrouted(phrase):
    assert _tier1_match(phrase) != "behavioral_activation", (
        f"idiom '{phrase}' wrongly routed to behavioral_activation"
    )
