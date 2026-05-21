# tests/test_rules_normalize.py
import pytest
from sage_poc.rules.normalize import (
    strip_invisible, strip_arabic_diacritics,
    normalize_alef, normalize_text, normalize_arabic,
)


def test_strip_invisible_removes_zwsp():
    assert strip_invisible("want​to die") == "wantto die"


def test_strip_invisible_removes_bom():
    assert strip_invisible("﻿hello") == "hello"


def test_strip_invisible_removes_zwnj():
    assert strip_invisible("don‌t") == "dont"


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
