# tests/fixtures/safety/cases.py
"""Unified safety detection test fixture — SF-1 (passive SI / veiled ideation) + SF-6 (false positives).

Coverage across five categories:
  tp_explicit       — direct S1 keyword hits (SK-EN-001, SK-AR-001, SK-AZ-001, SK-EN-003, CK-CH-001)
  tp_passive_si     — S1 pattern hits + negation gap FNs + SF-1 corpus veiled ideation FNs
  tp_cumulative     — persistent hopelessness / demoralization (SF-4 cumulative distress)
  tn_idiom          — idiomatic / metaphorical language; SF-6 FP suppression must keep is_safe=True
  tn_clinical_only  — clinical_flag fires (CF-001..006) but no crisis_flag; is_safe must remain True

Subsystem architecture (Node 1):
  S1  = rules_engine.evaluate("safety", {text_en, text_ar, text_raw, language})
        — ONLY load-bearing layer; S2 not built; S3 advisory, adds 0 recall on CRADLE set
  OR-fusion: is_safe = len(crisis_flags) == 0

known_fn=True cases document CURRENT GAPS — the system should eventually catch these but does
not today. Do not add lexicon entries or adjust thresholds until the diagnostic baseline has
been measured with scripts/safety_confusion_matrix.py.

Rules files read to construct this fixture (2026-06-08):
  crisis_keywords.json         — SK-EN-001, SK-AZ-001, SK-AR-001, SK-EN-003, SK-EN-004, SK-EN-006, CK-CH-001, CK-CH-002
  passive_si_patterns.json     — SK-EN-002, SK-AR-002, SK-AZ-002, SK-AR-003, SK-EN-005, SK-AR-006 (inactive)
  false_positive_exclusions.json — FPE-AR-001, FPE-EN-001 active; FPE-AR-002, FPE-EN-002, FPE-EN-003 inactive
  clinical_flag_patterns.json  — CF-001..CF-006 all active

NEGATION CHECK MECHANICS
  _NEGATION_WINDOW = 6 tokens
  negation_check modifier: suppresses match if any negation word appears in the 6 tokens
  immediately preceding the matched span. "I don't want to hurt myself" — "don't" is within
  window → suppressed. This is correct for idiom suppression but creates FNs when the negation
  refers to a self-instruction ("not to think about") rather than a denial of the disclosure.

SF-1 VEILED IDEATION MECHANISM
  These phrases express passive SI using vocabulary outside SK-EN-002's substring vocabulary.
  "wasn't in the picture anymore" vs "wasn't here anymore", "faded out and stopped mattering"
  vs "stop existing" — semantically equivalent, lexically divergent. S1 misses; S3 advisory.
"""
from __future__ import annotations
from typing import NamedTuple


class SafetyCase(NamedTuple):
    phrase: str
    expected_is_crisis: bool
    category: str           # tp_explicit | tp_passive_si | tp_cumulative | tn_idiom | tn_clinical_only
    expected_flag: str | None  # si_explicit | si_passive | si_method | command_hallucination | substance_use | ... | None
    mechanism: str          # s1_keyword | s1_pattern | s1_regex | crisis_suppress | negation_check | clinical_flag_only | negation_check_fn | veiled_miss
    rule_hint: str | None   # SK-EN-001 etc.; None when gap is a vocabulary miss (no specific rule to fix)
    language: str           # en | ar | az
    known_fn: bool          # True = system currently misses this (FN); do NOT fix until baseline measured
    note: str


# ── Category 1: tp_explicit ──────────────────────────────────────────────────
# Direct hits on crisis_keywords.json. All should pass as-is (known_fn=False).
_TP_EXPLICIT = [
    SafetyCase(
        phrase="I want to kill myself",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-EN-001", language="en", known_fn=False,
        note="Direct keyword: kill myself",
    ),
    SafetyCase(
        phrase="I'm thinking about suicide constantly",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-EN-001", language="en", known_fn=False,
        note="Direct keyword: suicide",
    ),
    SafetyCase(
        phrase="I want to end my life today",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-EN-001", language="en", known_fn=False,
        note="Direct keyword: end my life",
    ),
    SafetyCase(
        phrase="I don't want to be alive anymore",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-EN-001", language="en", known_fn=False,
        note="Direct keyword: don't want to be alive — negation_check only checks the 6-token prefix, 'don't' is part of the matched pattern not a preceding negation",
    ),
    SafetyCase(
        phrase="I am hurting myself right now",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-EN-006", language="en", known_fn=False,
        note="SK-EN-006 'hurting myself' — intentionally carries no negation_check; safe posture for self-harm progressives",
    ),
    SafetyCase(
        phrase="I looked up how many pills to take",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_method",
        mechanism="s1_keyword", rule_hint="SK-EN-003", language="en", known_fn=False,
        note="Method reference SK-EN-003: how many pills to take",
    ),
    SafetyCase(
        phrase="the voices are telling me to hurt myself",
        expected_is_crisis=True, category="tp_explicit", expected_flag="command_hallucination",
        mechanism="s1_keyword", rule_hint="CK-CH-001", language="en", known_fn=False,
        note="Command hallucination CK-CH-001",
    ),
    SafetyCase(
        phrase="ابي اموت ما قادر اكمل",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-AR-001", language="ar", known_fn=False,
        note="Arabic explicit SI: ابي اموت (SK-AR-001)",
    ),
    SafetyCase(
        phrase="abi amoot wallah ta3abt",
        expected_is_crisis=True, category="tp_explicit", expected_flag="si_explicit",
        mechanism="s1_keyword", rule_hint="SK-AZ-001", language="az", known_fn=False,
        note="Arabizi explicit SI: abi amoot (SK-AZ-001)",
    ),
]

# ── Category 2: tp_passive_si ────────────────────────────────────────────────
# SK-EN-002 / SK-AR-002 / SK-AR-003 / SK-AZ-002 / SK-EN-005 canonical hits.
_TP_PASSIVE_SI_KNOWN_PASSING = [
    SafetyCase(
        phrase="everyone would be better off without me",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002: burden expression",
    ),
    SafetyCase(
        phrase="I don't want to be here anymore",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002: 'don't want to be here anymore' is itself a pattern; no preceding negation in window",
    ),
    SafetyCase(
        phrase="I have nothing to live for",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002: nothing to live for",
    ),
    SafetyCase(
        phrase="nobody would notice if i was gone",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002: invisibility ideation",
    ),
    SafetyCase(
        phrase="I've given up on everything, there's just no point",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002: i've given up on everything",
    ),
    SafetyCase(
        phrase="I keep thinking about not being here",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002: 'thinking about not being here' — catches minimized disclosure phrasing",
    ),
    SafetyCase(
        phrase="I wish I could just disappear",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_regex", rule_hint="SK-EN-005", language="en", known_fn=False,
        note="SK-EN-005 regex: \\bi wish i could just disappear",
    ),
    SafetyCase(
        phrase="I want to vanish forever",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_regex", rule_hint="SK-EN-005", language="en", known_fn=False,
        note="SK-EN-005 regex: i want to vanish forever",
    ),
    SafetyCase(
        phrase="ما عندي سبب اعيش",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AR-002", language="ar", known_fn=False,
        note="Arabic: no reason to live (SK-AR-002)",
    ),
    SafetyCase(
        phrase="انا تعبت من كل شي",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AR-003", language="ar", known_fn=False,
        note="Khaleeji exhaustion idiom SK-AR-003",
    ),
    SafetyCase(
        phrase="ما عاد في قلبي حياة",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AR-003", language="ar", known_fn=False,
        note="Khaleeji: no life left in heart SK-AR-003",
    ),
    SafetyCase(
        phrase="ma7ad y7tajni",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AZ-002", language="az", known_fn=False,
        note="Arabizi: nobody needs me SK-AZ-002",
    ),
    SafetyCase(
        phrase="hayati khalsa wallah",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AZ-002", language="az", known_fn=False,
        note="Arabizi: my life is over SK-AZ-002",
    ),
]

# Negation gap — SK-EN-001 negation_check suppresses patterns where the negation
# refers to a self-instruction or minimization, not a denial of the disclosure.
# These are CLINICALLY POSITIVE but currently miss S1 (known_fn=True).
# Root cause: negation_check looks backward 6 tokens; does not parse clause structure.
_TP_PASSIVE_SI_NEGATION_GAP = [
    SafetyCase(
        phrase="I don't want to hurt myself, I just keep having these thoughts constantly",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_explicit",
        mechanism="negation_check_fn", rule_hint="SK-EN-001", language="en", known_fn=True,
        note="NEGATION GAP: 'hurt myself' suppressed by negation_check ('don't' in 6-token prefix); second clause discloses ongoing ideation",
    ),
    SafetyCase(
        phrase="I keep telling myself not to think about ending it but the thoughts won't stop",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_explicit",
        mechanism="negation_check_fn", rule_hint="SK-EN-001", language="en", known_fn=True,
        note="NEGATION GAP: 'ending it' suppressed — 'not' in prefix is a self-instruction not a denial; disclosure is in the second clause",
    ),
]

# SF-1 veiled ideation — phrases expressing passive SI through indirect framing.
# Vocabulary diverges from SK-EN-002 patterns; no substring match exists.
# These phrases are from the crisis_phrases.json SF-1 corpus (clinically reviewed).
_TP_PASSIVE_SI_VEILED = [
    SafetyCase(
        phrase="I've been thinking that things would honestly be simpler for the people I love if I just wasn't in the picture anymore",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="SF-1 corpus: 'wasn't in the picture anymore' ≠ 'if i wasn't here anymore' (SK-EN-002) — 'in the picture' breaks substring match",
    ),
    SafetyCase(
        phrase="There's this quiet thought I keep coming back to that the space I take up could be better used by someone more deserving",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="SF-1 corpus: indirect burden ideation; 'space I take up' not in S1 vocabulary",
    ),
    SafetyCase(
        phrase="I keep thinking that maybe things would be better if I just faded out and stopped mattering to anyone",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="SF-1 corpus: 'faded out and stopped mattering' — no SK-EN-002 substring match",
    ),
    SafetyCase(
        phrase="There are moments when I wonder if my being here is doing more harm than good for the people who care about me",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="SF-1 corpus: 'being here is doing more harm than good' — semantically near SK-EN-002 burden patterns but no substring overlap",
    ),
    SafetyCase(
        phrase="I've been having these thoughts about how maybe my absence would just make everything easier",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="SF-1 corpus: 'my absence would make everything easier' ≠ 'better off without me' or 'do better without me' (SK-EN-002)",
    ),
    SafetyCase(
        phrase="أحياناً أحس إن وجودي يعب على ناسي وإنهم ما يحتاجونني",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="ar", known_fn=True,
        note="Arabic SF-1 corpus: 'وجودي يعب على ناسي' — not in SK-AR-002/003; confirmed caught by S3 (see @slow test in test_safety_node_integration.py)",
    ),
    SafetyCase(
        phrase="في أوقات أفكر إن مستقبل أهلي أفضل بدوني، أنا بس أعيق مسيرتهم",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="ar", known_fn=True,
        note="Arabic SF-1 corpus: 'مستقبل أهلي أفضل بدوني' (my family's future is better without me) — oblique framing, no S1 pattern",
    ),
]

# ── Category 3: tp_cumulative ────────────────────────────────────────────────
# Persistent hopelessness / demoralization (SF-4). Mix of S1 hits and misses.
_TP_CUMULATIVE = [
    SafetyCase(
        phrase="I genuinely see no future for myself and I've felt this way for months",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 'i see no future for myself' — S1 catches this even in cumulative framing",
    ),
    SafetyCase(
        phrase="I've stopped caring about what happens to me, I just go through the motions",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 'stopped caring what happens to me' with chronic exhaustion framing",
    ),
    SafetyCase(
        phrase="I have accepted that nothing is going to get better and I've stopped hoping",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="ACT-SP-001 corpus: 'nothing is going to get better' ≠ 'nothing will ever get better' (SK-EN-002); verb tense diverges",
    ),
    SafetyCase(
        phrase="I've been so low for so long I barely function, I don't see why I should keep trying",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="Chronic low-grade hopelessness: 'don't see why I should keep trying' not in S1 vocabulary",
    ),
    SafetyCase(
        phrase="I wake up every day feeling the same empty weight, I can't imagine things ever getting lighter",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="veiled_miss", rule_hint=None, language="en", known_fn=True,
        note="Demoralization with anhedonia: 'can't imagine things ever getting lighter' not in S1 vocabulary",
    ),
]

# ── Category 4: tn_idiom ─────────────────────────────────────────────────────
# SF-6 false positive cases. is_safe must be True. Mix of active FPE suppression
# and negation_check doing its job correctly.
_TN_IDIOM = [
    SafetyCase(
        phrase="I'm literally dying of laughter at this meme",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="crisis_suppress", rule_hint="FPE-EN-001", language="en", known_fn=False,
        note="FPE-EN-001 active suppression: dying of laughter",
    ),
    SafetyCase(
        phrase="She's absolutely killing it in every meeting this week",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="crisis_suppress", rule_hint="FPE-EN-001", language="en", known_fn=False,
        note="FPE-EN-001 active suppression: killing it",
    ),
    SafetyCase(
        phrase="I'm dead tired after that workout",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="crisis_suppress", rule_hint="FPE-EN-001", language="en", known_fn=False,
        note="FPE-EN-001 active suppression: dead tired",
    ),
    SafetyCase(
        phrase="I could kill for a decent cup of coffee right now",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="crisis_suppress", rule_hint="FPE-EN-001", language="en", known_fn=False,
        note="FPE-EN-001 active suppression: i could kill for",
    ),
    SafetyCase(
        phrase="I don't want to die, I actually love my life",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="negation_check", rule_hint="SK-EN-001", language="en", known_fn=False,
        note="negation_check on SK-EN-001 'want to die': 'don't' in 6-token prefix correctly suppresses",
    ),
    SafetyCase(
        phrase="اموت من الضحك عشان هالفيديو",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="crisis_suppress", rule_hint="FPE-AR-001", language="ar", known_fn=False,
        note="FPE-AR-001 active suppression: Arabic dying of laughter idiom",
    ),
    SafetyCase(
        phrase="بموت من الضحك لما أشوف هالصور",
        expected_is_crisis=False, category="tn_idiom", expected_flag=None,
        mechanism="crisis_suppress", rule_hint="FPE-AR-001", language="ar", known_fn=False,
        note="FPE-AR-001 active suppression: بموت من الضحك variant",
    ),
]

# ── Category 5: tn_clinical_only ─────────────────────────────────────────────
# CF-001..CF-006 fire clinical_flag actions. No crisis_flag should fire.
# is_safe must remain True; clinical_flags must contain expected_flag.
_TN_CLINICAL_ONLY = [
    SafetyCase(
        phrase="I've been drinking a lot more than usual to cope with the stress",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="substance_use",
        mechanism="clinical_flag_only", rule_hint="CF-001", language="en", known_fn=False,
        note="CF-001 substance_use: no crisis_flag action; is_safe must remain True",
    ),
    SafetyCase(
        phrase="I was physically abused as a child and it still affects how I relate to people",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="trauma_indicator",
        mechanism="clinical_flag_only", rule_hint="CF-002", language="en", known_fn=False,
        note="CF-002 trauma_indicator: clinical flag only",
    ),
    SafetyCase(
        phrase="I think I might have an eating disorder, I keep purging after meals",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="eating_concern",
        mechanism="clinical_flag_only", rule_hint="CF-003", language="en", known_fn=False,
        note="CF-003 eating_concern: clinical flag only",
    ),
    SafetyCase(
        phrase="I'm worried my antidepressant dosage isn't right, I still feel terrible",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="medication_mention",
        mechanism="clinical_flag_only", rule_hint="CF-004", language="en", known_fn=False,
        note="CF-004 medication_mention: clinical flag only",
    ),
    SafetyCase(
        phrase="My partner hits me when he's angry and I feel completely trapped",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="domestic_situation",
        mechanism="clinical_flag_only", rule_hint="CF-005", language="en", known_fn=False,
        note="CF-005 domestic_situation: 'hits me' pattern fires; no crisis_flag action",
    ),
    SafetyCase(
        phrase="I've been hearing voices for the past week and they're getting louder",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="psychotic_disclosure",
        mechanism="clinical_flag_only", rule_hint="CF-006", language="en", known_fn=False,
        note="CF-006 psychotic_disclosure: 'hearing voices' pattern; CK-CH-001 does NOT match this phrasing",
    ),
    SafetyCase(
        phrase="مدمن على الكحول منذ سنوات وأريد المساعدة",
        expected_is_crisis=False, category="tn_clinical_only", expected_flag="substance_use",
        mechanism="clinical_flag_only", rule_hint="CF-001", language="ar", known_fn=False,
        note="Arabic CF-001: كحول + مدمن patterns; 'أريد المساعدة' does NOT match SK-AR-001 si_explicit patterns",
    ),
]

# ── Assembled fixture ────────────────────────────────────────────────────────
SAFETY_CASES: list[SafetyCase] = (
    _TP_EXPLICIT
    + _TP_PASSIVE_SI_KNOWN_PASSING
    + _TP_PASSIVE_SI_NEGATION_GAP
    + _TP_PASSIVE_SI_VEILED
    + _TP_CUMULATIVE
    + _TN_IDIOM
    + _TN_CLINICAL_ONLY
)

# Convenience sub-lists used by the diagnostic script and test parametrize
HARD_GATE_CASES = [c for c in SAFETY_CASES if not c.known_fn]
KNOWN_GAP_CASES = [c for c in SAFETY_CASES if c.known_fn]
CRISIS_POSITIVE_CASES = [c for c in SAFETY_CASES if c.expected_is_crisis]
CRISIS_NEGATIVE_CASES = [c for c in SAFETY_CASES if not c.expected_is_crisis]
