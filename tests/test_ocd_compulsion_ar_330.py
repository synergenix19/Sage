"""#330 — OCD-compulsion iatrogenic veto must fire on Arabic compulsions (live prod bypass).

Live-verified (prod 5b33a0e): "أظل أغسل يدي عشرات المرات وأتأكد من القفل… ما أقدر أوقف" routed to
act_psychological_flexibility (a self-help skill) with NO veto in node_path — the exact iatrogenic
routing the veto exists to prevent. Root cause = language-contract violation: is_ocd_compulsion read
ONLY translated message_en (skill_select.py:735), so the raw Arabic never reached the deterministic
matcher and the translation paraphrase-missed the EN patterns.

Fix (this branch): (1) the detector reads raw too (variadic), and skill_select passes raw_message;
(2) an INTERIM Arabic compulsion layer (action-keyed, FP-controlled, dual-clinician-pending). The
veto stays keyed on the compulsive ACTION/ritual, NOT on looping/repetition (which ordinary worry
legitimately owns) — so rumination must NOT false-fire (that would be its own iatrogenic harm).
"""
import pytest
from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion

# AR compulsions (checking/washing rituals) that MUST fire — first is the exact prod bypass probe.
AR_COMPULSION_MUST_FIRE = [
    "أظل أغسل يدي عشرات المرات وأتأكد من القفل مرارًا وتكرارًا وما أقدر أوقف نفسي",
    "لازم أتأكد من الغاز مرات ومرات قبل ما أطلع من البيت",
]

# AR worry/rumination that must NOT fire — the veto is keyed on the ritual, not on looping thought.
AR_WORRY_MUST_NOT_FIRE = [
    "أفكر كثير في مشاكلي وما أقدر أوقف التفكير",   # rumination, no ritual
    "قلبي يدق بسرعة وأنا قلقان",                    # anxiety somatics, unrelated
]

# EN regression — must stay firing.
EN_MUST_FIRE = ["I keep checking the lock and I can't stop"]


@pytest.mark.parametrize("text", AR_COMPULSION_MUST_FIRE)
def test_arabic_compulsion_fires(text):
    assert is_ocd_compulsion(text), f"AR compulsion did not fire the veto: {text!r} — #330 live bypass unfixed"


@pytest.mark.parametrize("text", AR_WORRY_MUST_NOT_FIRE)
def test_arabic_worry_does_not_fire(text):
    assert not is_ocd_compulsion(text), f"veto false-fired on rumination/worry (iatrogenic): {text!r}"


@pytest.mark.parametrize("text", EN_MUST_FIRE)
def test_english_still_fires(text):
    assert is_ocd_compulsion(text), f"EN regression: {text!r} stopped firing"


def test_detector_reads_raw_not_only_translated():
    """Language contract: safety detection reads RAW input. The detector must match an AR compulsion
    supplied as a later positional arg even when the first (translated) text is benign/empty."""
    assert is_ocd_compulsion("", "لازم أتأكد من الغاز مرات ومرات قبل ما أطلع من البيت"), (
        "detector ignores raw text — language-contract violation (safety must read raw, not only message_en)"
    )
