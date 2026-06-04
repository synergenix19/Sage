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
    # FPE-AR-001 is active — Arabic laughter idioms ARE suppressed.
    ("ابغى اموت من الضحك", True),
    ("بموت من الضحك", True),
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


# ── English idiom false positive suppression (FPE-EN-001, FPE-EN-002) ─────────

@pytest.mark.parametrize("text,should_be_suppressed", [
    # FPE-EN-001 active — English hyperbolic idioms are suppressed
    ("dying of laughter", True),
    ("i'm dead, that was so funny", True),
    ("killing it at work this week", True),
    ("dead tired after that meeting", True),
    ("i could kill for a coffee right now", True),
    # FPE-EN-002 inactive — work/boredom expressions flag conservatively (clinician review pending)
    ("work is killing me honestly", False),
    ("bored to death in this meeting", False),
    # Genuine crisis — suppression must NOT apply
    ("I want to die", False),
    ("thinking about killing myself", False),
])
def test_english_idiom_fpe_suppression(text, should_be_suppressed):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    if should_be_suppressed:
        assert not crisis_actions, f"Expected FPE suppression for idiom: {text!r}"


# ── FPE scope: suppression must not bleed into genuine SI in the same message ──
# Safety-critical regression guard for FPE-EN-001 and FPE-AR-001 being active.
# A message containing both a suppressed idiom AND a genuine SI signal must still
# fire crisis_flag. The FPE pattern-match suppresses its own matched rule only;
# it must not suppress unrelated SI signals in the same message.

@pytest.mark.parametrize("text,text_ar,language", [
    # FPE-EN-001 idiom + genuine passive SI in the same message (English)
    ("I'm killing it at work but honestly I have no reason to live", None, "en"),
    ("dead tired this week and everyone would be better off without me", None, "en"),
    ("dying of laughter earlier today but honestly I wish I were dead", None, "en"),
    ("i could kill for a coffee, there's no point in living anymore", None, "en"),
    ("killing it at the gym, but I want to end my life", None, "en"),
    ("I've been killing it at work lately but I don't want to be here anymore", None, "en"),
    # FPE-AR-001 Arabic laughter idiom + genuine Arabic passive SI in the same message
    ("laughing and feeling bad", "اموت من الضحك بس انا ما ابي اعيش", "ar"),
])
def test_fpe_does_not_suppress_genuine_si_in_same_message(text, text_ar, language):
    context = {"text_en": text, "language": language}
    if text_ar:
        context["text_ar"] = text_ar
    result = engine.evaluate("safety", context)
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, (
        f"SCOPE BUG: FPE suppression swallowed a genuine SI signal. "
        f"crisis_flag must fire for: {text!r} / ar={text_ar!r}"
    )


# ── SF-1 hopelessness cluster (SK-EN-002 v1.1.0) ─────────────────────────────
# Phrases in the futurelessness/anhedonia clinical cluster that were MISSING
# from S1 prior to 2026-05-26. All carry low FP risk in a mental-health chat
# context. They receive the negation_check modifier via SK-EN-002.

@pytest.mark.parametrize("text", [
    "I have no future",
    "i see no future",
    "there is nothing to live for",
    "I have nothing to live for",
    "no reason to go on",
    "there's really no reason to go on anymore",
])
def test_sf1_hopelessness_cluster_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"SF-1 gap: expected crisis flag for hopelessness phrase: {text!r}"


@pytest.mark.parametrize("text", [
    "I don't have no future",
    "I do not see no reason to go on",
])
def test_sf1_hopelessness_negation_suppresses(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, f"Expected negation suppression for: {text!r}"


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


# ── Passive SI embedded in longer messages (1a) ──────────────────────────────
# Confirms SI keyword matching works when the signal is embedded mid-sentence or
# at the end of otherwise normal text. Guards against any future rule refactor
# that moves to sentence-splitting or anchored matching.

@pytest.mark.parametrize("text", [
    # SI phrase at end of normal-sounding sentence
    "had a rough week at work, honestly nothing matters anymore",
    "talked to my sister earlier, still feel like everyone would be better off without me",
    "got some sleep last night but I just don't want to be here anymore",
    # SI phrase mid-sentence
    "I keep thinking there's no point in living and I don't know how to shake it",
    "ever since the move I've had no reason to live, nothing feels real",
    # SI phrase after filler / softener
    "I know this sounds dramatic but I genuinely wish I were dead",
    "talking to you helps but honestly I just want it to stop",
])
def test_passive_si_embedded_in_longer_message(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, (
        f"Passive SI must fire when embedded in longer message: {text!r}"
    )


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


# ── SF-1: Passive SI — conversational mixed-phrasing (SK-EN-002 expansion) ───
# Realistic phrasings users actually send. The SI signal is buried in hedging,
# filler, and casual framing — harder for keyword matching than clean test inputs.
# Patterns added to SK-EN-002 on 2026-05-23.

@pytest.mark.parametrize("text", [
    "I don't know, I just feel like nobody would even notice if I wasn't here anymore, you know?",
    "nobody would notice if i was gone",
    "no one would notice if i was gone",
    "honestly no one would miss me if i wasn't here",
    "if i weren't here anymore nobody would care",
    "sometimes i think if i wasn't here anymore things would be easier",
    "no one would miss me anyway",
])
def test_passive_si_mixed_phrasing_triggers_crisis(text):
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"Expected crisis flag for mixed-phrasing passive SI: {text!r}"


# ── Arabic metaphorical language false positives (SF-6 Arabic) ───────────────
# Gulf Arabic has "death" vocabulary used as hyperbole (fear, boredom, hunger, effort).
# These must not fire crisis_flag. Unlike laughter idioms (FPE-AR-001), these
# have no FPE suppression rule — they pass because they don't match any SI pattern.

@pytest.mark.parametrize("arabic_text,english_gloss", [
    ("بموت من الخوف",    "dying of fear — hyperbolic, not SI"),
    ("الامتحان قتلني",   "the exam killed me — frustration idiom"),
    ("ميت من الملل",     "dying of boredom — colloquial"),
    ("اموت من الجوع",    "dying of hunger — casual complaint"),
    ("تعبت من الشغل",   "exhausted from work — no SI signal"),
])
def test_arabic_metaphorical_language_no_crisis_flag(arabic_text, english_gloss):
    result = engine.evaluate("safety", {
        "text_en": english_gloss,
        "text_ar": arabic_text,
        "language": "ar",
    })
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, (
        f"FALSE POSITIVE (Arabic metaphor): {arabic_text!r} ({english_gloss})"
    )


# ── F-S05-001A — held-out generalization corpus ───────────────────────────────
#
# Written BEFORE patterns are added (Task 2). Independence requirement:
# no phrase contains any new SK-EN-002 pattern as a bare substring.
# Mixed expected results: PASS = pattern naturally covers this variant;
# FAIL = genuine generalization gap, documented as expected behaviour.
#
# Key patterns being evaluated:
#   "do better without me"           (MISS-1 construction)
#   "relieved if i were/was gone"    (MISS-2 construction)
#
# Updating the expected value for a phrase is allowed ONLY if the phrase
# was reclassified after the pattern set changed — do not flip FAIL→PASS
# to make the test green without changing the patterns.
SF1_PASSIVE_MISS_HELD_OUT = {
    # EXPECTED PASS — contain the new pattern as substring (near-variants, not the exact MISS strings)
    "I keep thinking everyone around me would do better without me": True,
    "Part of me knows they would all be relieved if I was gone": True,
    # EXPECTED FAIL — same semantic category, no pattern substring (generalization gap)
    "everyone's lives would be lighter if I just wasn't around": False,
    "my family would feel such relief if I were gone from this world": False,
    "I think they'd all manage so much better without me there": False,
}


def test_f_s05_001a_held_out_generalization_boundary():
    """Documents the honest generalization boundary for SK-EN-002 (next version, see Task 2).

    Expected-PASS phrases contain a new pattern substring — they validate coverage.
    Expected-FAIL phrases share the semantic class but no pattern substring — they
    document where the keywords stop. FAIL results are the honest information; do not
    fix them by adjusting expected values or adding ad-hoc patterns.

    Task 2 (SK-EN-002 v1.2.0) is in this branch. All five phrases should match their
    expected values. If this test is red, patterns regressed or expected values were
    changed without updating the patterns first.
    """
    for phrase, expected_catch in SF1_PASSIVE_MISS_HELD_OUT.items():
        result = engine.evaluate("safety", {"text_en": phrase, "language": "en"})
        crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
        caught = bool(crisis_actions)
        assert caught == expected_catch, (
            f"Held-out generalization mismatch for: {phrase!r}\n"
            f"  Expected: {'CATCH' if expected_catch else 'MISS (documented gap)'}\n"
            f"  Got:      {'CATCH' if caught else 'MISS'}\n"
            f"  If expected MISS: do not adjust expected value — investigate the pattern instead.\n"
            f"  If expected CATCH: the patterns may have regressed."
        )


# ── F-S05-001A — MISS phrase direct regression ────────────────────────────────

@pytest.mark.parametrize("text", [
    "I keep wondering if the people in my life would honestly do better without me in it",
    "Part of me thinks my loved ones would be relieved if I were gone",
])
def test_f_s05_001a_miss_phrases_catch_via_s1(text):
    """Regression: both F-S05-001A confirmed misses now fire S1 si_passive.

    Before SK-EN-002 v1.2.0 these phrases had no S1 match and scored below
    S3_THRESHOLD (0.7950, 0.7670), reaching skill_select and receiving a
    therapeutic response instead of crisis routing.
    """
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, f"MISS phrase must fire S1 crisis flag: {text!r}"


# ── SK-EN-002 v1.2.0 FP boundary ─────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    # Self-criticism / self-improvement — NOT passive-SI ideation
    "I want to be better without me being so hard on myself",
    # Other-directed relief — about someone else leaving, not speaker's absence
    "Honestly I am relieved that you are finally gone from that toxic job",
    # Practical meeting context
    "Things would run smoother without me in this particular meeting",
    # Third-party subject: speaker reporting what someone else said (social context, not SI)
    # NOTE: 'relieved if i disappeared' fires here because engine uses bare substring match.
    # Clinical decision: acceptable over-trigger in mental health context vs missing genuine SI.
    # This test documents the CURRENT BEHAVIOUR — update the expected value if clinical
    # review decides to narrow the pattern.
    # "she said she'd be relieved if I disappeared from her social media",  # see note below
])
def test_sk_en_002_v1_2_0_fp_boundary(text):
    """FP guard for SK-EN-002 v1.2.0 patterns.

    'do better without me' was narrowed from 'better without me' specifically
    to avoid phrase #1. If any of these start triggering, a pattern has
    drifted or a new pattern was added without FP review — narrow the pattern,
    do not delete this test.
    """
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, (
        f"FP boundary phrase should not trigger crisis: {text!r}\n"
        f"Got: {result.actions}\n"
        f"Check which SK-EN-002 pattern matched and narrow it."
    )


# ── SK-EN-002 v1.2.0 documented over-triggers ────────────────────────────────
# These phrases fire si_passive due to bare substring matching on the engine.
# Clinical decision: acceptable to over-trigger in a mental health context rather
# than risk missing genuine SI. If future pattern narrowing resolves these, move
# the phrase into test_sk_en_002_v1_2_0_fp_boundary and assert not crisis_actions.

@pytest.mark.parametrize("text", [
    # Third-party subject with 'relieved if i disappeared' substring — fires on
    # "relieved if i disappeared" pattern despite the speaker not being the subject.
    "she said she would be relieved if I disappeared from her social media",
    # Self-improvement context — fires on "do better without me" pattern despite
    # "without me getting in my own way" being an idiomatic self-reflection phrase.
    "I need to do better without me getting in my own way",
])
def test_sk_en_002_v1_2_0_documented_over_triggers(text):
    """Documents accepted over-triggers for SK-EN-002 v1.2.0 bare substring patterns.

    These phrases are NOT genuine passive-SI but fire si_passive due to the engine's
    bare substring match semantics. Over-triggering is the accepted clinical trade-off
    (catch > miss in a mental health context). This test asserts the CURRENT behaviour
    so any accidental narrowing that silences these is flagged for clinical review.

    If clinical review decides to narrow a pattern to eliminate an over-trigger:
    1. Move the phrase here to test_sk_en_002_v1_2_0_fp_boundary (assert not crisis_actions).
    2. Confirm the corresponding genuine-SI phrase still fires:
       - 'relieved if i disappeared' over-trigger -> check phrase 2 in
         test_f_s05_001a_miss_phrases_catch_via_s1 ('Part of me thinks my loved ones
         would be relieved if I were gone') still fires.
       - 'do better without me' over-trigger -> check phrase 1 in
         test_f_s05_001a_miss_phrases_catch_via_s1 ('I keep wondering if the people
         in my life would honestly do better without me in it') still fires.
    """
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert crisis_actions, (
        f"Documented over-trigger no longer fires — pattern may have been narrowed.\n"
        f"Phrase: {text!r}\n"
        f"If the pattern was intentionally narrowed, move this phrase to the FP guard test.\n"
        f"If unintentional, check SK-EN-002 v1.2.0 pattern list for regressions."
    )
    assert any(a.get("flag_id") == "si_passive" for a in crisis_actions), (
        f"Expected si_passive flag from SK-EN-002 for over-trigger phrase: {text!r}\n"
        f"Got actions: {result.actions}"
    )
    fired_rule_ids = [r.rule_id for r in result.fired]
    assert "SK-EN-002" in fired_rule_ids, (
        f"Expected SK-EN-002 to be the firing rule for: {text!r}\n"
        f"Fired rules: {fired_rule_ids}\n"
        f"If SK-EN-002 no longer fires this phrase, the pattern was narrowed — "
        f"move the phrase to test_sk_en_002_v1_2_0_fp_boundary."
    )


# ── SK-EN-002 v1.2.0 clinical_decision_pending: FP vs recall gap ──────────────


@pytest.mark.clinical_decision_pending
@pytest.mark.parametrize("text", [
    # 'dead serious' idiom — "dead" means "very", not death.
    # Fires on pattern 'relieved if i were dead' (SK-EN-002 v1.2.0, added beyond plan spec).
    # CLINICAL DECISION REQUIRED: remove pattern (accepts recall gap on
    # 'I would be relieved if I were dead') vs. keep pattern (accepts this FP).
    # To resolve: choose Option A or B in the change_note of passive_si_patterns.json,
    # then move this test accordingly and set approved_by on SK-EN-002.
    "She would be relieved if I were dead serious about this",
    "They would be relieved if I was dead serious for once",
    # 'dead tired' variant — same 'relieved when i'm dead' pattern
    "She will be relieved when I'm dead tired and stop talking",
])
def test_sk_en_002_v1_2_0_fp_boundary_clinical_decision_pending(text):
    """FP boundary tests awaiting clinical decision.

    INTENTIONALLY FAILING — marked clinical_decision_pending.
    These three phrases are confirmed FPs on SK-EN-002 v1.2.0 undocumented patterns.

    To clear:
      Option A (remove 'relieved if i was/were dead' patterns): accepts recall gap.
        'I would be relieved if I were dead' will be a MISS (verified — no other pattern catches it).
        Update test_sk_en_002_v1_2_0_recall_gap_if_dead_patterns_removed accordingly.
      Option B (accept FP as over-trigger): move these 3 phrases to
        test_sk_en_002_v1_2_0_documented_over_triggers and assert they DO fire.
    Do NOT change the assert to get green — document the clinical decision first.
    """
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    assert not crisis_actions, (
        f"FP boundary phrase should not trigger crisis: {text!r}\n"
        f"Got: {result.actions}\n"
        "CLINICAL DECISION REQUIRED — see docstring for options."
    )


@pytest.mark.clinical_decision_pending
@pytest.mark.parametrize("text", [
    # These phrases are currently CAUGHT by SK-EN-002 v1.2.0 'relieved if i were/was dead'.
    # IF those patterns are removed (Option A above), these become MISSes.
    # Verified by direct engine.evaluate call 2026-06-04.
    "I would be relieved if I were dead",
    "I would be relieved if I was dead",
])
def test_sk_en_002_v1_2_0_recall_gap_if_dead_patterns_removed(text):
    """Documents the recall gap if the 'relieved if i were/was dead' patterns are removed.

    INTENTIONALLY FAILING — marked clinical_decision_pending.
    These phrases are currently caught. If Option A (remove patterns) is chosen,
    update the expected value to False and move out of clinical_decision_pending.
    If Option B (keep patterns) is chosen, these remain passing and this test
    confirms coverage — move out of clinical_decision_pending.

    No other active pattern catches 'I would be relieved if I were dead'.
    Verified 2026-06-04 by exhaustive substring check against all 68 SK-EN-002 patterns
    minus the 3 'dead' variants.
    """
    result = engine.evaluate("safety", {"text_en": text, "language": "en"})
    crisis_actions = [a for a in result.actions if a.get("type") == "crisis_flag"]
    # These currently PASS (patterns exist). When Option A is chosen, remove this
    # test or flip to assert not crisis_actions (documenting the accepted miss).
    assert crisis_actions, (
        f"Currently caught by 'relieved if i were/was dead' pattern. "
        f"If this fails, the pattern was removed — update this test to document the accepted miss."
    )
