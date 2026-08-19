# tests/test_veto_input_normalization.py
#
# F2 (code_review.md 2026-08-17): Node-4 veto lexicons must see normalized
# input. Bare .lower() misses U+2019 (the default iOS/Android apostrophe) and
# invisible characters (ZWSP etc.), silently disarming deterministic safety
# vetoes depending on the user's keyboard. Spec basis: S5 mandates input
# normalization; routing the vetoes through rules.normalize.normalize_text
# restores spec. Reading of record: normalization, NOT a lexicon change; no
# clinical re-sign-off required (owner disposition 2026-08-17).
#
# Three cases per module, phrases taken verbatim from the lexicon JSONs:
#   1. non-ASCII positive: the phrase that slips through today must veto
#      (U+2019 for ocd/ipv; ZWSP for harm_intrusive, whose 40 patterns
#      contain no apostrophes, so U+2019 cannot break it today)
#   2. ASCII pin: byte-identical outcome on pure-ASCII input
#      (regression-by-improvement on the unchanged direction)
#   3. curly-quote negative: normalization must not create false vetoes
# Plus an ASCII-invariance property check over all three lexicons.

import pytest

from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion, COMPULSION_PATTERNS
from sage_poc.nodes.harm_intrusive import is_harm_intrusive, HARM_INTRUSIVE_PATTERNS
from sage_poc.nodes.ipv_preempt import _matches_expansion, EXPANSION_PHRASES
from sage_poc.rules.normalize import normalize_text

pytestmark = pytest.mark.safety_gate


# ── OCD compulsion veto (lexicon: ocd_compulsion_patterns.json) ──────────────

class TestOcdCompulsionNormalization:
    def test_u2019_apostrophe_vetoes(self):
        # Lexicon pattern: "can't stop checking" (ASCII apostrophe)
        assert is_ocd_compulsion(
            "I can’t stop checking the stove over and over"
        ) is True

    def test_ascii_pin_unchanged(self):
        assert is_ocd_compulsion("I can't stop checking the stove") is True
        assert is_ocd_compulsion("today was a completely ordinary day") is False

    def test_curly_quote_negative_stays_negative(self):
        assert is_ocd_compulsion(
            "That movie was so scary I couldn’t sleep afterwards"
        ) is False


# ── Harm-intrusive veto (lexicon: harm_intrusive_patterns.json) ──────────────

class TestHarmIntrusiveNormalization:
    def test_zwsp_inside_pattern_vetoes(self):
        # A zero-width space (U+200B, IME/paste artifact) inside "harming"
        # defeats bare .lower() for every covering pattern ("intrusive images
        # of harming", "images of harming my baby", "harming my baby");
        # strip_invisible removes it. (No apostrophe-bearing patterns exist in
        # this lexicon, so U+2019 cannot break it; ZWSP is the same
        # input-artifact defect class.)
        assert is_harm_intrusive(
            "I keep having intrusive images of har​ming my baby"
        ) is True

    def test_ascii_pin_unchanged(self):
        assert is_harm_intrusive(
            "I keep having intrusive images of harming my baby"
        ) is True
        assert is_harm_intrusive("today was a completely ordinary day") is False

    def test_curly_quote_negative_stays_negative(self):
        assert is_harm_intrusive(
            "I’ve been reading about intrusive advertising practices"
        ) is False


# ── IPV §6a expansion matcher (lexicon: ipv_preempt_expansion.json) ──────────

class TestIpvExpansionNormalization:
    def test_u2019_apostrophe_matches(self):
        # Lexicon phrase: "I don't know what they'd do if I pushed back"
        # (2 ASCII apostrophes; 14 of the 19 phrases carry apostrophes,
        # making this the highest-value target)
        assert _matches_expansion(
            "I don’t know what they’d do if I pushed back"
        ) is True

    def test_ascii_pin_unchanged(self):
        assert _matches_expansion(
            "I'm always watching what I say so I don't set them off"
        ) is True
        assert _matches_expansion("They get really angry if I say no") is True
        assert _matches_expansion("today was a completely ordinary day") is False

    def test_curly_quote_negative_stays_negative(self):
        assert _matches_expansion(
            "They said the restaurant’s closed on Mondays"
        ) is False


# ── ASCII-invariance property (all three lexicons) ───────────────────────────

class TestAsciiInvariance:
    def test_normalize_text_is_identity_modulo_lower_on_ascii(self):
        # For pure-ASCII input normalize_text(s) == s.lower(): every stage
        # (strip_invisible, NFKC, typographic map) is a no-op on ASCII, so
        # every veto outcome on ASCII input is byte-identical pre/post F2.
        for corpus in (COMPULSION_PATTERNS, HARM_INTRUSIVE_PATTERNS, EXPANSION_PHRASES):
            for phrase in corpus:
                if not phrase.isascii():
                    continue  # Arabic OCD entries: covered by the test below
                carrier = f"well {phrase} today"
                assert normalize_text(carrier) == carrier.lower()

    def test_non_ascii_lexicon_entries_stable_under_normalize_text(self):
        # The OCD lexicon carries 9 Arabic patterns (dead at the message_en
        # call site — recorded finding, not touched by F2). Pin that
        # normalize_text does not alter them (modulo lower), so the compiled
        # normalized lexicon is byte-identical for them pre/post F2.
        for corpus in (COMPULSION_PATTERNS, HARM_INTRUSIVE_PATTERNS, EXPANSION_PHRASES):
            for phrase in corpus:
                if phrase.isascii():
                    continue
                assert normalize_text(phrase) == phrase.lower()
