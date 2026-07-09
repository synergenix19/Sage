"""Fail-closed crisis-copy LOCALE-PARITY boot guard tests (#1 class-fix).

assert_crisis_locale_parity() extends the crisis-copy boot guard to a second invariant: every
active crisis_content level shipped for one supported locale MUST have a natively-authored twin in
every other supported locale (en_uae + ar_uae). This is the class-guarantee — a crisis string added
in English without its Arabic twin fails the boot instead of reaching an Arabic user via machine
translation (the RCA of finding #1: the monitoring fallback had no native AR twin and rode the
translate-out path, the one crisis-number surface not deterministic end-to-end in Arabic).
"""
import pytest

from sage_poc.crisis_copy import assert_crisis_locale_parity


def test_real_crisis_content_has_locale_parity():
    # The shipped tree must boot: every active crisis level has en_uae + ar_uae native twins.
    assert_crisis_locale_parity()  # must not raise


def test_missing_arabic_twin_fails_boot():
    # An English crisis level with no Arabic twin is exactly the #1 failure mode — fail the boot.
    rules = [
        {"locale": "en_uae", "crisis_level": "acute", "active": True},
        {"locale": "ar_uae", "crisis_level": "acute", "active": True},
        {"locale": "en_uae", "crisis_level": "monitoring_fallback", "active": True},  # no AR twin
    ]
    with pytest.raises(RuntimeError, match="LOCALE PARITY"):
        assert_crisis_locale_parity(rules)


def test_missing_english_twin_fails_boot():
    # Parity is symmetric: an Arabic-only level must also fail.
    rules = [
        {"locale": "en_uae", "crisis_level": "acute", "active": True},
        {"locale": "ar_uae", "crisis_level": "acute", "active": True},
        {"locale": "ar_uae", "crisis_level": "monitoring_fallback", "active": True},  # no EN twin
    ]
    with pytest.raises(RuntimeError, match="LOCALE PARITY"):
        assert_crisis_locale_parity(rules)


def test_exempt_extended_level_en_only_does_not_trip_parity():
    # "extended" (proactive resource directory, CC-EN-002) is NOT served by any node, so it is
    # explicitly exempt from parity even while active + EN-only (audit finding #8, tracked separately).
    rules = [
        {"locale": "en_uae", "crisis_level": "acute", "active": True},
        {"locale": "ar_uae", "crisis_level": "acute", "active": True},
        {"locale": "en_uae", "crisis_level": "extended", "active": True},  # exempt level
    ]
    assert_crisis_locale_parity(rules)  # must not raise


def test_inactive_en_only_level_does_not_trip_parity():
    # A dead/deactivated EN-only rule can never reach a user, so it is exempt from the parity check.
    rules = [
        {"locale": "en_uae", "crisis_level": "acute", "active": True},
        {"locale": "ar_uae", "crisis_level": "acute", "active": True},
        {"locale": "en_uae", "crisis_level": "monitoring_fallback", "active": False},  # dead -> excluded
    ]
    assert_crisis_locale_parity(rules)  # must not raise


def test_both_locales_present_passes():
    rules = [
        {"locale": "en_uae", "crisis_level": "acute", "active": True},
        {"locale": "ar_uae", "crisis_level": "acute", "active": True},
        {"locale": "en_uae", "crisis_level": "monitoring_fallback", "active": True},
        {"locale": "ar_uae", "crisis_level": "monitoring_fallback", "active": True},
    ]
    assert_crisis_locale_parity(rules)  # must not raise
