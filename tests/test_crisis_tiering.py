"""W1-core: crisis tiering (v7.1 amendment to §5.1 OR-fusion).

This file has two layers:
  1. RESOLVER unit tests (this commit) — pure, fast, no model: the signal-set + language →
     tier mapping, sourced entirely from rules/data/safety/tier_routing.json (no hardcoded
     boundary in code). Covers audit checklist C and the tier semantics of E.
  2. BEHAVIORAL + S7 invariant tests (next commit, gate plumbing) — assert real routing through
     safety_check/graph with the flag ON: the two prod FP strings resolve T1, the Arabic
     command-hallucination resolves T2, and the three S7 Cardinal-Rule-4 invariants. Those are
     marked below with an explicit skip so this file never claims coverage it does not yet have.
"""
import pytest

from sage_poc.safety.crisis_tier import resolve_crisis_tier


# ── Layer 1: resolver unit tests (the 3 signed rules) ────────────────────────

def test_s1_keyword_any_language_is_T2():
    # Any S1 keyword flag → acute, regardless of language or an accompanying S3 hit.
    assert resolve_crisis_tier({"si_explicit"}, "en") == "T2"
    assert resolve_crisis_tier({"si_passive"}, "ar") == "T2"
    assert resolve_crisis_tier({"si_explicit", "s3_semantic"}, "en") == "T2"


def test_s3_solo_english_is_T1():
    # Semantic-only (no keyword corroboration) in English → warm concern, NOT the RED card.
    # This is the exact production incident: "i am feeling hopeless" fired s3_semantic alone.
    assert resolve_crisis_tier({"s3_semantic"}, "en") == "T1"


def test_s3_solo_arabic_and_arabizi_is_T2():
    # AR/AZ keyword coverage is weak, so a semantic-only hit there stays acute (preserves the
    # Arabic command-hallucination catch found in prod).
    assert resolve_crisis_tier({"s3_semantic"}, "ar") == "T2"
    assert resolve_crisis_tier({"s3_semantic"}, "az") == "T2"


def test_no_signal_is_none():
    assert resolve_crisis_tier(set(), "en") == "none"
    assert resolve_crisis_tier(set(), "ar") == "none"


def test_resolver_reads_json_not_hardcoded_constants():
    # Audit C: the boundary lives in tier_routing.json, exactly 3 rules, no phrase lists.
    from sage_poc.safety.crisis_tier import _load_tier_rules
    rules = _load_tier_rules()
    assert [r["id"] for r in rules] == ["s1_any", "s3_solo_en", "s3_ar_az"]
    for r in rules:
        assert "phrases" not in r and "keywords" not in r, "tier rules must carry no phrase lists (§K)"


# ── Layer 2: behavioral + S7 invariants (pending gate plumbing — next commit) ──

@pytest.mark.skip(reason="GREEN after W1 gate plumbing (safety_check tier + graph routing, flag ON)")
def test_prod_fp_strings_resolve_T1_behaviorally():
    """The two verified prod FP strings must route T1 (not the RED card) with the flag ON:
    'i am feeling hopeless' and 'it feels like a burden and it is making me feel so low'."""


@pytest.mark.skip(reason="GREEN after W1 gate plumbing")
def test_arabic_command_hallucination_resolves_T2_behaviorally():
    """The Arabic command-hallucination case must stay T2 (crisis) with the flag ON."""


@pytest.mark.skip(reason="GREEN after W1 gate plumbing — S7 Cardinal-Rule-4 invariants")
def test_s7_timeout_cannot_suppress_same_turn_s1_fire():
    """Inject an S7 timeout AND a same-turn S1 keyword fire → must still route T2."""
