# tests/test_rules_safety.py
import pytest
from sage_poc.rules import engine
from sage_poc.rules.loader import reload_all


@pytest.fixture(autouse=True)
def fresh_cache():
    reload_all()
    yield
    reload_all()


# ── Explicit SI (English) ────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "I want to die",
    "thinking about ending my life",
    "I've been thinking of ending it",
    "I am suicidal",
    "I want to kill myself",
    "better off dead",
    "I don't want to be alive anymore",
])
def test_explicit_si_english_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for: {text!r}"


# ── Passive SI (English) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "nothing matters anymore",
    "everyone would be better off without me",
    "there's no point in living",
    "I wish I could disappear",
    "I have no reason to live",
])
def test_passive_si_english_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for passive SI: {text!r}"


# ── Negation suppression (false positive prevention) ────────────────────────

@pytest.mark.parametrize("text", [
    "I don't want to die",
    "I never want to die",
    "no I don't want to end my life",
    "I do not want to kill myself",
])
def test_negation_suppresses_false_positive(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"Expected NO crisis flag for negated: {text!r}"


# ── ZWSP obfuscation bypass ──────────────────────────────────────────────────

def test_zwsp_bypass_still_detected():
    text = "i am s​uicidal"  # ZWSP inside 'suicidal'
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    assert any(a.get("type") == "crisis_flag" for a in result.actions)


# ── Arabizi (Gulf English) SI ────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "wallah i want to die",
    "abi amoot",
    "khalas i give up",
])
def test_arabizi_si_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabizi: {text!r}"


# ── Arabic explicit SI ───────────────────────────────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "أبي أموت",          # Gulf alef-hamza-above
    "ابي اموت",          # bare alef (same after normalization)
    "أريد الموت",        # MSA
    "أبغى أختفي",        # Gulf: want to disappear
    "ابغى اختفي",        # bare alef variant
])
def test_arabic_explicit_si_triggers_crisis(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "i want to die",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic: {arabic_text!r}"


# ── Arabic passive SI ────────────────────────────────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "نفسي تعبت",           # "my soul is tired"
    "ما عاد قادر",         # "I can no longer cope"
    "مافي فايدة",          # Gulf: "no use/no point"
    "ياريت انام ولا اصحى", # "I wish I'd sleep and not wake up"
])
def test_arabic_passive_si_triggers_crisis(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "nothing matters",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic passive SI: {arabic_text!r}"


# ── Clinical flags ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_flag", [
    ("I've been drinking a lot to cope", "substance_use"),
    ("I'm on antidepressants", "medication_mention"),
    ("I was assaulted last year", "trauma_indicator"),
    ("I've been binge eating and purging", "eating_concern"),
])
def test_clinical_flag_detection(text, expected_flag):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, f"Expected {expected_flag!r} for: {text!r}"


# ── No false positives on safe messages ─────────────────────────────────────

@pytest.mark.parametrize("text", [
    "I feel anxious today",
    "I'm struggling with work",
    "could kill for a good coffee",
    "that presentation killed me",
    "I'm dying of laughter",
])
def test_safe_message_no_crisis_flag(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"Expected NO crisis flag for: {text!r}"


# ── Arabic clinical flag patterns (language="any" must check norm_ar) ────────

@pytest.mark.parametrize("arabic_text,expected_flag", [
    ("أنا أشرب الكحول كثيراً", "substance_use"),
    ("أنا مدمن", "substance_use"),
])
def test_arabic_clinical_flags_detected_via_arabic_patterns(arabic_text, expected_flag):
    result = engine.evaluate("safety", {
        "text_en": "some neutral translation",
        "text_ar": arabic_text,
        "language": "ar",
    })
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, (
        f"Expected {expected_flag!r} for Arabic text: {arabic_text!r}"
    )


# ── CF-005 domestic_situation ─────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_flag", [
    ("he hits me", "domestic_situation"),
    ("I'm in an abusive relationship", "domestic_situation"),
    ("domestic violence in my home", "domestic_situation"),
    ("my partner hurts me", "domestic_situation"),
    ("he won't let me leave", "domestic_situation"),
    ("she controls everything I do", "domestic_situation"),
])
def test_domestic_situation_flag_detection_english(text, expected_flag):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, f"Expected {expected_flag!r} for: {text!r}"


@pytest.mark.parametrize("arabic_text,expected_flag", [
    ("يضربني زوجي", "domestic_situation"),
    ("أنا في علاقة مسيئة", "domestic_situation"),
    ("عنف أسري", "domestic_situation"),
])
def test_domestic_situation_flag_detection_arabic(arabic_text, expected_flag):
    result = engine.evaluate("safety", {
        "text_en": "my partner hurts me",
        "text_ar": arabic_text,
        "language": "ar",
    })
    flag_ids = [a["flag_id"] for a in result.actions if a.get("type") == "clinical_flag"]
    assert expected_flag in flag_ids, f"Expected {expected_flag!r} for Arabic: {arabic_text!r}"


# ── Arabizi explicit SI expansion (SK-AZ-001) ─────────────────────────────────

@pytest.mark.parametrize("text", [
    "aby amoot",
    "abi amwt",
    "bidi amoot",
    "bedi amoot",
    "mabi akoon",
    "ma abgha akamil",
    "ta3abt mn el7ayat",
    "ta3abt mn alhayat",
])
def test_arabizi_explicit_si_expansion_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabizi: {text!r}"


# ── Arabizi passive SI (SK-AZ-002) ────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "ma7ad y7tajni",
    "kolhum a7san bdooni",
    "ma fee amal",
    "ma fi amal",
    "ta3abt mn nafsy",
    "hayati khalsa",
    "hayati 5alsa",
    "ma7ad ra7 yef2adni",
    "mafi fayda",
])
def test_arabizi_passive_si_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabizi passive SI: {text!r}"


# ── C-SSRS passive SI expansion (SK-EN-002) ───────────────────────────────────

@pytest.mark.parametrize("text", [
    "I wish I were dead",
    "I wish I was dead",
    "wish to be dead",
    "I want to go to sleep and not wake up",
    "wish I could fall asleep and not wake up",
    "life is not worth living",
    "nothing will ever get better",
    "there's no way out",
    "I make everything worse",
    "they'd be happier without me",
    "I just want it to stop",
    "I don't care about anything anymore",
    "I've stopped caring what happens to me",
    "I have no future",
    "nothing brings me joy anymore",
    "I've given up on everything",
    "what is the point of anything",
    "can't see a future for myself",
])
def test_passive_si_english_expansion_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for passive SI: {text!r}"
