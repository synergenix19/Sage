# tests/test_rules_normalize.py
import re
import pytest
from sage_poc.rules.normalize import (
    strip_invisible, strip_arabic_diacritics,
    normalize_alef, normalize_text, normalize_arabic,
    has_arabic, ARABIC_CHAR_RE,
)


def test_strip_invisible_removes_zwsp():
    assert strip_invisible("want​to die") == "wantto die"


def test_strip_invisible_removes_bom():
    assert strip_invisible("﻿hello") == "hello"


def test_strip_invisible_removes_zwnj():
    assert strip_invisible("don‌t") == "dont"


def test_strip_invisible_removes_rtl_mark():
    assert strip_invisible("want‏to die") == "wantto die"


def test_strip_invisible_removes_ltr_mark():
    assert strip_invisible("want‎to die") == "wantto die"


def test_strip_arabic_diacritics_removes_fatha():
    # fatha U+064E on alef
    assert strip_arabic_diacritics("أَ") == "أ"


def test_strip_arabic_diacritics_removes_sukun():
    assert strip_arabic_diacritics("مْ") == "م"


def test_normalize_alef_hamza_above():
    # أ (U+0623) → ا (U+0627)
    assert normalize_alef("أبي") == "ابي"


def test_normalize_alef_madda():
    # آ (U+0622) → ا
    assert normalize_alef("آخر") == "اخر"


def test_normalize_alef_hamza_below():
    # إ (U+0625) → ا
    assert normalize_alef("إبراهيم") == "ابراهيم"


def test_normalize_alef_wasla():
    # ٱ (U+0671) → ا
    assert normalize_alef("ٱلله") == "الله"


def test_normalize_text_lowercases():
    assert normalize_text("KILL MYSELF") == "kill myself"


def test_normalize_text_strips_invisible_before_lowercase():
    assert normalize_text("want​to DIE") == "wantto die"


def test_normalize_arabic_full_pipeline():
    # أبي أموت (with hamza above alef) → normalized to bare alef
    result = normalize_arabic("أبي أموت")
    assert result == "ابي اموت"


def test_normalize_arabic_strips_diacritics_and_alef():
    # أَبِي أَمُوتُ (with full harakat) → ابي اموت
    result = normalize_arabic("أَبِي أَمُوتُ")
    assert result == "ابي اموت"


def test_normalize_arabic_bare_alef_unchanged():
    assert normalize_arabic("ابي اموت") == "ابي اموت"


def test_normalize_text_folds_curly_apostrophe():
    # U+2019 RIGHT SINGLE QUOTATION MARK (iOS/Android apostrophe) -> U+0027
    assert normalize_text("can’t") == "can't"


def test_normalize_text_folds_left_single_quote():
    # U+2018 LEFT SINGLE QUOTATION MARK -> U+0027
    assert normalize_text("it‘s fine") == "it's fine"


def test_normalize_text_folds_smart_double_quotes():
    # U+201C LEFT / U+201D RIGHT DOUBLE QUOTATION MARK -> U+0022
    assert normalize_text("“hello”") == '"hello"'


def test_normalize_text_folds_em_dash():
    # U+2014 EM DASH -> ASCII hyphen-minus; U+2019 apostrophe also folds
    result = normalize_text("i—can’t")
    assert result == "i-can't"


def test_normalize_text_folds_en_dash():
    # U+2013 EN DASH -> ASCII hyphen-minus
    assert normalize_text("day–by–day") == "day-by-day"


def test_normalize_text_folds_fullwidth_chars():
    # Fullwidth i (U+FF49) -> ASCII i via NFKC; U+2019 apostrophe also folds
    assert normalize_text("ｉ’m") == "i'm"


def test_normalize_text_backward_compat_plain_ascii():
    assert normalize_text("can't go on") == "can't go on"


# -- has_arabic / ARABIC_CHAR_RE -----------------------------------------------------

def test_has_arabic_pure_ascii_false():
    assert has_arabic("kill myself") is False


def test_has_arabic_pure_arabic_true():
    assert has_arabic("أبي أموت") is True


def test_has_arabic_mixed_script_true():
    assert has_arabic("I feel اموت today") is True


def test_has_arabic_diacritics_only_true():
    # Bare fatha U+064B, no base letter -- still inside the U+0600-U+06FF block.
    assert has_arabic("ً") is True


def test_has_arabic_empty_string_false():
    assert has_arabic("") is False


def test_has_arabic_none_like_empty_false():
    # Sites converted from `_ARABIC_RE.search(text or "")` pass falsy text through as "".
    assert has_arabic("") is False


def test_has_arabic_arabic_indic_digits_true():
    # Arabic-Indic digits U+0660-U+0669 are inside U+0600-U+06FF -- all six prior
    # implementations shared this range and therefore all matched these digits too.
    assert has_arabic("١٢٣") is True


def test_has_arabic_rtl_ltr_marks_false():
    # RTL mark U+200F / LTR mark U+200E sit OUTSIDE the Arabic script block
    # (they're in General Punctuation, stripped separately by strip_invisible).
    assert has_arabic("‏‎") is False


def test_arabic_char_re_findall_counts_characters():
    # output_gate.py needs a COUNT (for a ratio), not a bool -- ARABIC_CHAR_RE is the
    # shared pattern it calls .findall() against directly.
    assert len(ARABIC_CHAR_RE.findall("اموت today")) == 4


def test_arabic_char_re_is_compiled_and_matches_same_block_as_has_arabic():
    assert ARABIC_CHAR_RE.pattern == r'[؀-ۿ]'
    assert bool(ARABIC_CHAR_RE.search("مرحبا")) == has_arabic("مرحبا")


# -- parity with the 6 prior independent reimplementations ----------------------------
# Each lambda below reproduces one of the pre-consolidation call sites verbatim (by
# code shape, not by import) so this test proves has_arabic() is behavior-identical
# across a representative input set, not just "looks equivalent by inspection".

def _old_repository_contains_arabic(text: str) -> bool:
    # src/sage_poc/knowledge/repository.py: _ARABIC_RE.search
    return bool(re.compile(r"[؀-ۿ]").search(text or ""))


def _old_composer_is_arabic(text: str) -> bool:
    # src/sage_poc/prompts/composer.py: _is_arabic
    return bool(re.search(r"[؀-ۿ]", text))


def _old_output_gate_has_arabic(text: str) -> bool:
    # src/sage_poc/nodes/output_gate.py: _HAS_ARABIC_RE.findall(...) as a ratio numerator;
    # boolean presence form for parity purposes.
    return bool(re.compile(r"[؀-ۿ]").search(text))


def _old_skill_executor_is_arabic(text: str) -> bool:
    # src/sage_poc/nodes/skill_executor.py: per-character ordinal loop
    return any(0x0600 <= ord(c) <= 0x06FF for c in text)


def _old_engine_is_arabic_kw(text: str) -> bool:
    # src/sage_poc/rules/engine.py: per-character string-comparison loop
    return any('؀' <= ch <= 'ۿ' for ch in text)


def _old_tier_b_is_arabic(text: str) -> bool:
    # scripts/prod_smoke/tier_b_features.py: `ord(c) in range(...)` membership loop
    arabic_range = range(0x0600, 0x06FF + 1)
    return any(ord(c) in arabic_range for c in text)


_OLD_IMPLEMENTATIONS = [
    _old_repository_contains_arabic,
    _old_composer_is_arabic,
    _old_output_gate_has_arabic,
    _old_skill_executor_is_arabic,
    _old_engine_is_arabic_kw,
    _old_tier_b_is_arabic,
]

_PARITY_CASES = [
    "",                          # empty string
    "kill myself",               # pure ASCII
    "أبي أموت",                  # pure Arabic
    "I feel اموت today",         # mixed
    "ً",                    # Arabic diacritic only (fatha)
    "أَبِي أَمُوتُ",                # Arabic with full harakat
    "١٢٣",        # Arabic-Indic digits
    "‏‎",              # RTL/LTR marks only (outside the block)
    "مرحبا 123 hello",           # Arabic + digits + Latin
]


@pytest.mark.parametrize("text", _PARITY_CASES)
def test_has_arabic_matches_all_six_prior_implementations(text):
    expected = has_arabic(text)
    for old_impl in _OLD_IMPLEMENTATIONS:
        assert old_impl(text) == expected, (
            f"{old_impl.__name__} disagreed with has_arabic() on {text!r}"
        )
