"""#329 — B1 medical red-flag guard must fire on Arabic cardiac red-flags.

Live-verified bypass (prod 5b33a0e, flag-ON): the AR probe below routed to progressive_muscle_
relaxation with NO medical-emergency prompt, because `medical_redflag_phrases.json` has zero
Arabic entries and the upstream machine-translation paraphrase-missed the EN literal list. The
detector already receives BOTH message_en and raw (safety_check.py:286 `detect_medical_redflag(
message_en, raw)`), so native AR phrases fire against `raw` — this is the interim fix.

INTERIM safety-floor (transcription of the spec's §1 descriptor classes into Arabic), NOT coverage:
Gulf dialect / code-switched / full symptom vocabulary is the clinician-authored Tier-2 follow-up.
"""
import pytest
from sage_poc.safety.medical_redflag import detect_medical_redflag

# AR cardiac red-flags that MUST fire (spec §1 descriptor classes: crushing/searing chest pain,
# radiation to arm, one-sided numbness). The first is the exact prod-verified bypass probe.
# ADDENDUM (post-audit): spec L216 REAL inability to breathe + L148 fainting are ALSO red flags.
AR_REDFLAGS_MUST_FIRE = [
    "عندي ألم ضاغط في صدري وينتشر إلى ذراعي اليسرى",   # crushing + radiation-to-arm (prod bypass probe)
    "ألم حارق في صدري",                                  # searing chest pain
    "عندي خدر في جهة واحدة من جسمي",                     # one-sided numbness
    "ما أقدر أتنفس نهائيًا وحسيت إني راح يغمى علي",       # ADDENDUM: real inability to breathe + faint (L216/L148)
]

# AR benign anxiety that must NOT fire. Spec L102 excludes SHALLOW/panic breathlessness (core anxiety
# symptom) — but L216 MANDATES *real inability to breathe* as a red flag. The must-fire above and the
# must-not-fire below straddle that boundary; the exact phrase discriminator is a clinician call (packet
# addendum blank), so these probes sit deliberately on the clear side of each.
AR_BENIGN_MUST_NOT_FIRE = [
    "قلبي يدق بسرعة وأنا قلقان",          # racing heart + anxious (L102)
    "أشعر بالقلق وضيق في التنفس",         # anxiety + shallow/panic breathlessness (L102) — NOT real inability
]

# EN regression + ADDENDUM real-inability (both were spec red flags missing from the EN base list too).
EN_MUST_FIRE = [
    "I have crushing chest pain spreading to my arm",
    "I can't breathe at all",                            # ADDENDUM: real inability (L216) — EN gap predates #329
]


@pytest.mark.parametrize("text", AR_REDFLAGS_MUST_FIRE)
def test_arabic_cardiac_redflag_fires(text):
    assert detect_medical_redflag(text), (
        f"AR cardiac red-flag did not fire the medical guard: {text!r} — #329 live bypass unfixed"
    )


@pytest.mark.parametrize("text", AR_BENIGN_MUST_NOT_FIRE)
def test_arabic_benign_anxiety_does_not_fire(text):
    assert not detect_medical_redflag(text), (
        f"false positive on benign AR anxiety (spec L102 forbids screening on core symptoms): {text!r}"
    )


@pytest.mark.parametrize("text", EN_MUST_FIRE)
def test_english_still_fires(text):
    assert detect_medical_redflag(text), f"EN regression: {text!r} stopped firing"
