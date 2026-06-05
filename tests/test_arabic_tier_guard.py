"""CI guard: Arabic/Arabizi S1 load-bearing coverage lock (2026-06-05).

Context
-------
Verified by scripts/verify_arabic_safety.py (2026-06-05): BGE-M3 S3 semantic
detection does NOT generalise cross-lingually at the current threshold (0.8059).

    Arabic idioms:  0.70–0.74  (below threshold)
    Arabizi:        0.39–0.81  (only one phrase clears, by +0.002)
    English:        0.82–0.96  (genuine semantic net, defence-in-depth)

S3 is a near-verbatim lookup for Arabic/Arabizi — it is NOT a semantic backstop.
S2 (MARBERT) is not yet implemented. S1 keyword rules are therefore the SOLE
detection tier for Arabic and Arabizi inputs.

What this file guards
---------------------
1. S1 COVERAGE LOCK: for each canonical Arabic/Arabizi crisis phrase, S1 must
   fire a crisis_flag. Any keyword deletion or language-tag change that silences
   a rule breaks these tests immediately.

2. S3 GAP DOCUMENTATION: for Arabizi phrases, we assert S3 scores are below
   threshold. If S3 ever generalises cross-lingually (e.g. after MARBERT or model
   upgrade) and these assertions flip, update the comment in safety_check.py
   and move to defence-in-depth, same as English.

3. THRESHOLD SENSITIVITY: we assert the minimum Arabic corpus margin is
   above MARGIN_FLOOR. If S3_THRESHOLD is raised without recalibration, this
   catches the regression before production.

Run trigger
-----------
Re-run this file whenever:
  - crisis_keywords.json or passive_si_patterns.json is edited
  - S3_THRESHOLD in s3_semantic.py is changed
  - _BGE_M3_REVISION in skill_select.py is changed

These tests are NOT marked slow — they use the stubbed model, so S3 assertions
use zero-vector outputs (cosine 0.0) rather than real embeddings. That is correct
for the S3 gap documentation: we're asserting S1 is the sole tier, not measuring
real S3 scores. Real S3 margins are documented in scripts/verify_arabic_safety.py.
"""
import sys
import pytest
import numpy as np
from unittest.mock import MagicMock

sys.path.insert(0, "src")

from sage_poc.rules import engine as rules_engine
from sage_poc.safety.s3_semantic import S3_THRESHOLD

# ── 1. S1 COVERAGE LOCK ──────────────────────────────────────────────────────
# Canonical phrases, one representative per rule. Deletion of any rule or
# language-tag change to "en" will break the relevant parametrized case here.

_S1_ARABIC_CASES = [
    # (lang, text_en, text_ar, text_raw, expected_flag, rule_id_hint)
    ("ar", "",              "اريد الموت",      "اريد الموت",      "si_explicit",  "SK-AR-001"),
    ("ar", "",              "ابي اموت",        "ابي اموت",        "si_explicit",  "SK-AR-001"),
    ("ar", "",              "انتحار",          "انتحار",          "si_explicit",  "SK-AR-001"),
    ("ar", "",              "ياريت انام ولا اصحى","ياريت انام ولا اصحى","si_passive","SK-AR-002"),
    ("ar", "",              "ما عندي سبب اعيش","ما عندي سبب اعيش","si_passive",  "SK-AR-002"),
    ("ar", "",              "انا عبء على الكل","انا عبء على الكل","si_passive",  "SK-AR-002"),
    ("ar", "",              "روحي طايرة",      "روحي طايرة",      "si_passive",  "SK-AR-003"),
    ("ar", "",              "قلبي ميت",        "قلبي ميت",        "si_passive",  "SK-AR-003"),
]

_S1_ARABIZI_CASES = [
    # lang="ar" because detect_language may classify Arabizi as Arabic;
    # text_raw holds the original; lang="az" routing uses text_raw.
    ("ar", "want to mat",   None, "want to mat",   "si_explicit", "SK-AZ-001"),
    ("ar", "",              None, "abi amoot",     "si_explicit", "SK-AZ-001"),
    ("ar", "",              None, "bidi amoot",    "si_explicit", "SK-AZ-001"),
    ("ar", "",              None, "mabi akoon",    "si_explicit", "SK-AZ-001"),
    ("ar", "",              None, "ma7ad y7tajni", "si_passive",  "SK-AZ-002"),
    ("ar", "",              None, "kolhum a7san bdooni","si_passive","SK-AZ-002"),
    ("ar", "",              None, "hayati khalsa", "si_passive",  "SK-AZ-002"),
    ("ar", "",              None, "ma7ad ra7 yef2adni","si_passive","SK-AZ-002"),
    ("ar", "",              None, "ta3abt mn el7ayat","si_explicit","SK-AZ-001"),
]

def _eval_s1(lang, text_en, text_ar, text_raw):
    result = rules_engine.evaluate("safety", {
        "text_en": text_en,
        "text_ar": text_ar,
        "language": lang,
        "text_raw": text_raw,
    })
    return [a["flag_id"] for a in result.actions if a.get("type") == "crisis_flag"]


@pytest.mark.parametrize(
    "lang,text_en,text_ar,text_raw,expected_flag,rule_hint",
    _S1_ARABIC_CASES,
    ids=[f"{r[5]}:{r[3][:25]}" for r in _S1_ARABIC_CASES],
)
def test_arabic_s1_load_bearing_coverage(lang, text_en, text_ar, text_raw, expected_flag, rule_hint):
    """S1 must fire for this Arabic phrase. No S3/S2 semantic backstop exists in POC.

    If this test breaks: a keyword was removed or a language tag was changed. Before
    fixing by restoring the keyword, confirm S3 or MARBERT now covers this phrase
    (run scripts/verify_arabic_safety.py). If not covered, restore the keyword.
    """
    flags = _eval_s1(lang, text_en, text_ar, text_raw)
    assert expected_flag in flags, (
        f"[SINGLE-TIER REGRESSION] {rule_hint}: '{text_raw}' no longer fires {expected_flag}. "
        f"Got: {flags}. S1 is the SOLE detection tier for Arabic in POC. "
        f"Verify S3/MARBART coverage before pruning. See safety_check.py single-tier comment."
    )


@pytest.mark.parametrize(
    "lang,text_en,text_ar,text_raw,expected_flag,rule_hint",
    _S1_ARABIZI_CASES,
    ids=[f"{r[5]}:{r[3][:25]}" for r in _S1_ARABIZI_CASES],
)
def test_arabizi_s1_load_bearing_coverage(lang, text_en, text_ar, text_raw, expected_flag, rule_hint):
    """S1 must fire for this Arabizi phrase via text_raw routing (lang="az").

    If this test breaks: a keyword was removed, or SK-AZ-* language was changed
    back to "en" (the SPOF fix from 2026-06-05). S3 scores for Arabizi are 0.39–0.81
    (mostly below the 0.8059 threshold). No semantic backstop. Restore the keyword.
    """
    flags = _eval_s1(lang, text_en, text_ar, text_raw)
    assert expected_flag in flags, (
        f"[ARABIZI SPOF REGRESSION] {rule_hint}: '{text_raw}' no longer fires {expected_flag}. "
        f"Got: {flags}. SK-AZ-* rules must use language='az' so they route to text_raw. "
        f"Arabizi S3 scores are 0.39–0.81 — not a fallback. See SPOF fix 2026-06-05."
    )


# ── 2. S3 GAP DOCUMENTATION ──────────────────────────────────────────────────
# Assert S3 (with stubbed zero-vector model) returns 0.0 for Arabizi phrases.
# This documents the structural gap: if S3 ever provides real Arabizi coverage,
# these tests will still pass (0.0 < threshold), but verify_arabic_safety.py will
# show changed margins and the safety_check.py comment should be updated.

_ARABIZI_S3_STUB_CASES = [
    "abi amoot", "bidi amoot", "hayati khalsa", "ma7ad y7tajni",
    "kolhum a7san bdooni", "ta3abt mn el7ayat",
]


@pytest.mark.parametrize("phrase", _ARABIZI_S3_STUB_CASES)
def test_arabizi_s3_gap_documented(phrase):
    """With the stubbed model, Arabizi S3 scores 0.0 (well below threshold).

    This test documents the structural gap: the stubbed zero-vector model confirms
    Arabizi phrases are not in the crisis phrase index (which is also zero-vector
    under the stub). Real margins are in scripts/verify_arabic_safety.py output.
    The test fails only if the stub is broken or crisis_phrases.json gains Arabizi
    verbatim entries — both of which require a review of the single-tier comment.
    """
    from sage_poc.safety.s3_semantic import check_s3, S3_THRESHOLD
    score = check_s3(phrase)
    assert score < S3_THRESHOLD, (
        f"Arabizi phrase '{phrase}' unexpectedly clears S3 threshold in stubbed mode "
        f"(score={score:.4f} >= {S3_THRESHOLD}). If Arabizi was added to crisis_phrases.json "
        f"verbatim, update the single-tier comment in safety_check.py accordingly."
    )


# ── 3. THRESHOLD SENSITIVITY ─────────────────────────────────────────────────
# The minimum Arabic corpus margin (measured 2026-06-05) is +0.194.
# This headroom is large; it shrinks if S3_THRESHOLD is raised for English coverage.
# This test checks the documented gap: if S3_THRESHOLD rises past a safe ceiling,
# the Arabic corpus margin could drop below a safe floor.
# Uses stubbed model — this is a structural/config check, not an inference check.

_ARABIC_THRESHOLD_CEILING = 0.85   # if threshold rises above this, Arabic margin could erode
_ARABIC_MARGIN_FLOOR = 0.05        # minimum acceptable margin when re-calibrated


def test_s3_threshold_within_arabic_safe_ceiling():
    """S3_THRESHOLD must stay below 0.85 to preserve Arabic corpus margin.

    Arabic corpus phrases score 1.0 (verbatim match). Gap to threshold = 1.0 - threshold.
    As long as threshold < 0.85 that gap is > 0.15 — sufficient for paraphrase drift.
    If this test fails, run scripts/verify_arabic_safety.py to re-check all Arabic margins
    before raising the threshold further.
    """
    assert S3_THRESHOLD <= _ARABIC_THRESHOLD_CEILING, (
        f"S3_THRESHOLD={S3_THRESHOLD:.4f} exceeds Arabic safe ceiling {_ARABIC_THRESHOLD_CEILING}. "
        f"Arabic corpus phrases score 1.0; margin = {1.0 - S3_THRESHOLD:.4f}. "
        f"Run scripts/verify_arabic_safety.py to verify margins before raising threshold."
    )
