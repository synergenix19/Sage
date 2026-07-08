"""Unit tests for scripts/register_eval/gender_marker.py::detect_gender_marking.

The shadow-measure's gender policy is "mirror-when-marked, neutral-when-unknown":
mirror the user's own grammatical self-marking of gender when present, fall back
to neutral Arabic otherwise. detect_gender_marking is the deterministic classifier
that drives that stratification — it must never guess: conflicting or absent
markers both resolve to "none", never a coin-flip toward "f" or "m".
"""
from scripts.register_eval.gender_marker import detect_gender_marking


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


def test_conflicting_markers_resolve_to_none():
    # Both a masculine and a feminine predicate adjective present — ambiguous,
    # must not guess either way.
    text = "أنا تعبان بس أختي قالت هي زعلانة"
    assert detect_gender_marking(text) == "none"


def test_third_party_marking_current_behavior():
    # KNOWN LIMITATION: the whole-word matcher has no syntactic subject-tracking,
    # so it cannot distinguish "أختي تعبانة" (describing someone else) from a
    # genuine first-person self-marking. Ideally this would be "none" since the
    # speaker never self-describes. This test asserts the CURRENT (honest, not
    # faked) behavior rather than pretending the limitation doesn't exist: the
    # lexicon match alone fires "f" here. Flagged for the Gulf-native linguist
    # review pass (see the STARTER-lexicon comment in gender_marker.py) to add
    # subject-scoping before this can be trusted for third-party sentences.
    text = "أختي تعبانة اليوم"
    assert detect_gender_marking(text) == "f"


def test_empty_string_is_none():
    assert detect_gender_marking("") == "none"


def test_h_spelling_variant_feminine():
    # تعبانه (ه-spelling variant of تعبانة) must still resolve to "f".
    text = "أنا تعبانه اليوم"
    assert detect_gender_marking(text) == "f"
