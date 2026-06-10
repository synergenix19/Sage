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

# Negation gap — NC-01/NC-02 classes. Previously FNs where SK-EN-001 negation_check
# suppressed intent-disclaimer + disclosure and self-instruction + disclosure patterns.
# FIXED 2026-06-08: SK-EN-007 adds regex bypass patterns; no negation_check. Clinical sign-off 2026-06-08.
_TP_PASSIVE_SI_NEGATION_GAP = [
    SafetyCase(
        phrase="I don't want to hurt myself, I just keep having these thoughts constantly",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_explicit",
        mechanism="s1_regex", rule_hint="SK-EN-007", language="en", known_fn=False,
        note="SK-EN-007 NC-01 bypass: compound regex captures 'don't want to hurt myself' + ongoing thought disclosure; no negation_check",
    ),
    SafetyCase(
        phrase="I keep telling myself not to think about ending it but the thoughts won't stop",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_explicit",
        mechanism="s1_regex", rule_hint="SK-EN-007", language="en", known_fn=False,
        note="SK-EN-007 NC-02 bypass: 'telling myself not to think about ending it' — self-instruction presupposes active SI thought; no negation_check",
    ),
]

# SF-1 veiled ideation — phrases expressing passive SI through indirect framing.
# FIXED 2026-06-08: SK-EN-002 v1.3.0 adds 8 English patterns (VM-01–VM-05, VM-08–VM-10);
# SK-AR-002 v1.1.0 adds 3 Arabic patterns (VM-06–VM-07). Clinical sign-off 2026-06-08.
_TP_PASSIVE_SI_VEILED = [
    SafetyCase(
        phrase="I've been thinking that things would honestly be simpler for the people I love if I just wasn't in the picture anymore",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'if i just wasn't in the picture anymore' — VM-01; FP-verified 0/4 FP",
    ),
    SafetyCase(
        phrase="There's this quiet thought I keep coming back to that the space I take up could be better used by someone more deserving",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'space i take up could be better used' — VM-02",
    ),
    SafetyCase(
        phrase="I keep thinking that maybe things would be better if I just faded out and stopped mattering to anyone",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'faded out and stopped mattering' — VM-03",
    ),
    SafetyCase(
        phrase="There are moments when I wonder if my being here is doing more harm than good for the people who care about me",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'being here is doing more harm than good' — VM-04",
    ),
    SafetyCase(
        phrase="I've been having these thoughts about how maybe my absence would just make everything easier",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'my absence would just make everything easier' — VM-05",
    ),
    SafetyCase(
        phrase="أحياناً أحس إن وجودي يعب على ناسي وإنهم ما يحتاجونني",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AR-002", language="ar", known_fn=False,
        note="SK-AR-002 v1.1.0: 'وجودي يعب' + 'ما يحتاجونني' — VM-06; both patterns added after clinical sign-off 2026-06-08",
    ),
    SafetyCase(
        phrase="في أوقات أفكر إن مستقبل أهلي أفضل بدوني، أنا بس أعيق مسيرتهم",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-AR-002", language="ar", known_fn=False,
        note="SK-AR-002 v1.1.0: 'أفضل بدوني' — VM-07; engine normalizes أ→ا at runtime, both forms safe to store",
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
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'nothing is going to get better and i've stopped' — VM-08 compound pattern",
    ),
    SafetyCase(
        phrase="I've been so low for so long I barely function, I don't see why I should keep trying",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'so low for so long' — VM-09; FP-verified 0/5 FP",
    ),
    SafetyCase(
        phrase="I wake up every day feeling the same empty weight, I can't imagine things ever getting lighter",
        expected_is_crisis=True, category="tp_cumulative", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=False,
        note="SK-EN-002 v1.3.0: 'can't imagine things ever getting lighter' — VM-10",
    ),
]

# Node 1 crisis-recall gaps — documented 2026-06-10.
# Three independent detection-architecture failures surfaced during grief-anchor SI-boundary
# work. None are grief-specific: the mechanism applies in any context (depression, financial
# despair, isolation, estrangement). Grief is where they were found; these belong here as
# first-class Node 1 recall tests, not as an artifact of routing work.
# See docs/superpowers/escalations/2026-06-10-node1-crisis-recall-gap.md.
# PRE-PILOT BLOCKER — gates any user-facing pilot, not just pilots with grief histories.
_TP_PASSIVE_SI_RECALL_GAPS = [
    SafetyCase(
        phrase="I find myself wondering what the point is anymore",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=True,
        note="Veiled ideation gap (VG-01): indirect hopelessness without explicit SI vocabulary. 'Wondering what the point is' — S1 and S3 both miss. Appears across depression, grief, financial despair. Not grief-specific.",
    ),
    SafetyCase(
        phrase="things would be easier without me",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s1_pattern", rule_hint="SK-EN-002", language="en", known_fn=True,
        note="Vocabulary variant gap (VG-02): 'easier without me' misses; 'better off without me' catches. Variant vocabulary outside current SK-EN-002 patterns. Not grief-specific.",
    ),
    SafetyCase(
        phrase="Since she died I keep thinking no one would really notice if I was gone",
        expected_is_crisis=True, category="tp_passive_si", expected_flag="si_passive",
        mechanism="s3_semantic", rule_hint="SK-EN-002", language="en", known_fn=True,
        note="Multi-clause S3 dilution (VG-03): emotionally-loaded context clause before SI clause reduces BGE-M3 embedding score below detection threshold. Bare 'no one would really notice if I was gone' catches via S3; grief-prefix version does not. General property of S3 multi-clause scoring — any emotionally-loaded prefix can dilute detection of a following SI clause.",
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
    + _TP_PASSIVE_SI_RECALL_GAPS
    + _TN_IDIOM
    + _TN_CLINICAL_ONLY
)

# Convenience sub-lists used by the diagnostic script and test parametrize
HARD_GATE_CASES = [c for c in SAFETY_CASES if not c.known_fn]
KNOWN_GAP_CASES = [c for c in SAFETY_CASES if c.known_fn]
CRISIS_POSITIVE_CASES = [c for c in SAFETY_CASES if c.expected_is_crisis]
CRISIS_NEGATIVE_CASES = [c for c in SAFETY_CASES if not c.expected_is_crisis]
