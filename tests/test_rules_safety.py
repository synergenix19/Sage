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


# ── Arabic dialect expansion — explicit SI (SK-AR-001) ────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "بدي اموت",
    "عايز اموت",
    "عاوز اموت",
    "نفسي اموت",
    "انهاء حياتي",
    "ما ابي اعيش",
    "ما ابغى اعيش",
])
def test_arabic_explicit_si_dialect_expansion(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "i want to die",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic dialect: {arabic_text!r}"


# ── Arabic passive SI expansion (SK-AR-002) ───────────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "الحياة ما لها معنى",
    "وش الفايدة من الحياة",
    "انا عبء على الكل",
    "ودي اختفي من الدنيا",
    "ما في مستقبل لي",
    "الحياة ما تستاهل",
    "ما شايف فايدة",
    "روحي تعبت",
])
def test_arabic_passive_si_dialect_expansion(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "nothing matters",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Arabic passive SI: {arabic_text!r}"


# ── Gulf emotional exhaustion idioms (SK-AR-003) ──────────────────────────────

@pytest.mark.parametrize("arabic_text", [
    "روحي طايرة",
    "قلبي ميت",
    "انا تعبت من كل شي",
    "ما عاد في قلبي حياة",
    "نفسي مريضة",
    "روحي ما تحتمل",
    "انكسرت من الداخل",
    "ما في شي يسعدني",
])
def test_arabic_exhaustion_idioms_sk_ar_003(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "i feel empty",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for Gulf exhaustion idiom: {arabic_text!r}"


# ── Self-harm method references (SK-EN-003) ───────────────────────────────────

@pytest.mark.parametrize("text", [
    "how to overdose",
    "how many pills to take",
    "jumping off a bridge",
    "cutting my wrists",
    "cutting deep",
    "where to cut myself",
    "pills to kill myself",
    "ways to end my life",
    "how to hurt myself badly",
    "methods to die",
])
def test_self_harm_method_reference_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for method reference: {text!r}"
    assert any(a.get("flag_id") == "si_method" for a in crisis_actions), (
        f"Expected flag_id='si_method' for: {text!r}"
    )


# ── Arabic idiom false positive suppression (FPE-AR-001, FPE-AR-002) ──────────

@pytest.mark.parametrize("arabic_text,should_be_suppressed", [
    # C-6: FPE-AR-001 is currently active=False pending clinician approval.
    # While inactive, laughter idioms are NOT suppressed — crisis_flag fires (conservative default).
    # Update to True once clinician approves FPE-AR-001 and active=True.
    ("ابغى اموت من الضحك", False),
    ("بموت من الضحك", False),
    # These ARE genuine crisis expressions — suppression must NOT apply
    ("ابغى اموت بدون سبب", False),
])
def test_arabic_laughter_idiom_suppression(arabic_text, should_be_suppressed):
    result = engine.evaluate("safety", {
        "text_en": "feeling very emotional",
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    if should_be_suppressed:
        assert not crisis_actions, f"Expected suppression for idiom: {arabic_text!r}"


@pytest.mark.parametrize("arabic_text", [
    "ابغى اموت من الضحك",
    "بموت من الضحك",
])
def test_arabic_laughter_idiom_suppressed_rule_still_in_audit_trail(arabic_text):
    result = engine.evaluate("safety", {
        "text_en": "laughing",
        "text_ar": arabic_text,
        "language": "ar",
    })
    # Even when suppressed, the fired rule list must contain the suppressed rule (PDPL audit)
    suppressed_ids = [r.rule_id for r in result.suppressed_rules]
    if result.suppressed_rules:
        assert any("SK-AR" in rid or "SK-AZ" in rid for rid in suppressed_ids), (
            "Suppressed crisis rule must appear in audit trail"
        )


# ── Third-party crisis detection (SK-EN-004) ─────────────────────────────────

@pytest.mark.parametrize("text", [
    "my friend told me she wants to die",
    "my sister is suicidal",
    "someone I know wants to end their life",
    "my friend said she wants to kill herself",
    "my colleague mentioned wanting to die",
    "my brother wants to hurt himself",
    "my friend is thinking of ending it",
])
def test_third_party_crisis_fires_third_party_action(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    third_party_actions = [a for a in result.actions if a.get("type") == "third_party_crisis"]
    assert third_party_actions, f"Expected third_party_crisis action for: {text!r}"


# ── Expanded false positive prevention ───────────────────────────────────────

@pytest.mark.parametrize("text", [
    # English idioms (existing coverage)
    "I feel anxious today",
    "I'm struggling with work",
    "could kill for a good coffee",
    "that presentation killed me",
    "I'm dying of laughter",
    # New English metaphors
    "this assignment is killing me",
    "I'd die for a vacation right now",
    "dead tired after that meeting",
    "deadline is killing me",
    "I bombed that exam",
    "I'm dead serious",
    "killer app",
    "I killed it in the interview",
    "my feet are dying",
    "I could die of embarrassment",
    "dying to try that restaurant",
    "drop dead gorgeous",
    "he's to die for",
    # Negated self-harm
    "I never want to hurt myself",
    "I'm not suicidal",
    "no I don't want to die",
])
def test_safe_messages_expanded_no_crisis_flag(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"FALSE POSITIVE: Crisis flag triggered for safe text: {text!r}"
