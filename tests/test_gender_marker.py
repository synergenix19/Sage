"""Unit tests for sage_poc/gender_marker.py::detect_gender_marking.

Promoted from scripts/register_eval/gender_marker.py (see that module's history) —
this test file follows the detector to its new served-path home in sage_poc.

The shadow-measure's gender policy is "mirror-when-marked, neutral-when-unknown":
mirror the user's own grammatical self-marking of gender when present, fall back
to neutral Arabic otherwise. detect_gender_marking is the deterministic classifier
that drives that stratification — it must never guess: conflicting or absent
markers both resolve to "none", never a coin-flip toward "f" or "m".
"""
from sage_poc.gender_marker import detect_gender_marking


def test_feminine_self_marking_seed_017():
    # Real seed-017 input: "صرلي فترة تعبانة نفسياً، وحاسة إني مب أنا"
    # ("I've been [fem.] tired/exhausted mentally for a while, and I feel [fem.]
    # like I'm not myself") — two feminine predicate-adjective/participle markers
    # (تعبانة, حاسة) describing the speaker.
    text = "صرلي فترة تعبانة نفسياً، وحاسة إني مب أنا"
    assert detect_gender_marking(text) == "f"


def test_masculine_self_marking():
    text = "أنا تعبان وما عاد أقدر"
    assert detect_gender_marking(text) == "m"


def test_no_self_marking_neutral_content():
    text = "عندي deadline يوم الخميس وثلاث meetings"
    assert detect_gender_marking(text) == "none"


def test_no_self_marking_short_neutral_phrase():
    text = "كله نفس الشي"
    assert detect_gender_marking(text) == "none"


def test_conflicting_self_markers_resolve_to_none():
    # A masculine AND a feminine marker, BOTH first-person-anchored (each beside
    # أنا) — a genuine self-marking conflict, must not guess either way.
    text = "أنا تعبان وأنا زعلانة"
    assert detect_gender_marking(text) == "none"


def test_third_party_marker_rejected_by_possessor_guard():
    # "أختي تعبانة اليوم": the feminine marker's immediate predecessor is the
    # third-person possessor أختي (my sister), so it describes HER, not the speaker.
    # The anchor guard rejects it -> "none" (was a false-positive "f" before the guard,
    # which the reduce-then-quantify condition of record required fixing first).
    assert detect_gender_marking("أختي تعبانة اليوم") == "none"


def test_third_party_excluded_but_self_marking_kept():
    # "I'm sad [masc, self] but my sister is tired [fem, about her]": self-masculine
    # is anchored to أنا and kept; the feminine is possessor-guarded out -> "m".
    assert detect_gender_marking("أنا زعلان بس أختي تعبانة") == "m"


def test_pronoun_dropped_marker_without_anchor_is_none():
    # Bare "تعبانة اليوم" (feminine, no nearby first-person anchor): biased toward
    # "none" rather than risk a wrong-gender guess — the accepted false-negative.
    assert detect_gender_marking("تعبانة اليوم") == "none"


def test_empty_string_is_none():
    assert detect_gender_marking("") == "none"


def test_h_spelling_variant_feminine():
    # تعبانه (ه-spelling variant of تعبانة) must still resolve to "f".
    text = "أنا تعبانه اليوم"
    assert detect_gender_marking(text) == "f"
