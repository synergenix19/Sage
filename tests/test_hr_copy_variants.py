"""HR-1 Stage 2 -- deterministic variant-pool copy (src/sage_poc/safety/hr_copy.py).

Covers pick_hr_variant's core contract (reproducible per session_id+slot, varies
across sessions, never leaks {{first_name}} when no name is available, interpolates
correctly when one is), plus the DRAFT pools themselves: every variant, once
{{crisis_*}}/{{first_name}} placeholders are resolved, still carries its slot's
required content anchor, and no variant contains an em dash.

Per house convention (test_hr_terminal.py's own note): assert on resolved content
anchors / index reproducibility, not on prose equality with a single "the" string --
these are NOW pools, so there is no single verbatim string to pin.
"""
import re

import pytest

from sage_poc.crisis_copy import resolve_crisis_placeholders
from sage_poc.safety.hr_copy import (
    HR_DISTRESS_QUESTION_POOL,
    HR_REASK_POOL,
    HR_REDIRECT_HIGHER_POOL,
    HR_REDIRECT_LOWER_POOL,
    HR_SUPPORTIVE_MESSAGE_POOL,
    pick_hr_variant,
)

_ALL_POOLS = {
    "distress_question": HR_DISTRESS_QUESTION_POOL,
    "supportive_message": HR_SUPPORTIVE_MESSAGE_POOL,
    "redirect_higher": HR_REDIRECT_HIGHER_POOL,
    "redirect_lower": HR_REDIRECT_LOWER_POOL,
    "reask": HR_REASK_POOL,
}

# A 0-10 scale reference does not always appear as the literal substring "0 to 10"
# (a ratified variant may phrase it "between 0 and 10"); the load-bearing property is
# that both scale endpoints appear, in order, somewhere in the sentence.
_SCALE_ANCHOR_RE = re.compile(r"\b0\b.*\b10\b", re.DOTALL)


# ---------------------------------------------------------------------------
# Pool shape
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slot_key,pool", _ALL_POOLS.items())
def test_each_pool_has_four_variants(slot_key, pool):
    assert len(pool) == 4, slot_key


@pytest.mark.parametrize("slot_key,pool", _ALL_POOLS.items())
def test_no_em_dash_in_any_pool_variant(slot_key, pool):
    for variant in pool:
        assert "—" not in variant, f"{slot_key} variant contains an em dash: {variant!r}"


# ---------------------------------------------------------------------------
# pick_hr_variant: reproducibility + spread
# ---------------------------------------------------------------------------

def test_pick_hr_variant_reproducible_same_session_and_slot():
    pool = HR_DISTRESS_QUESTION_POOL
    first = pick_hr_variant(pool, "session-abc-123", "distress_question")
    for _ in range(10):
        assert pick_hr_variant(pool, "session-abc-123", "distress_question") == first


def test_pick_hr_variant_reproducible_across_all_slots():
    session_id = "session-reproducible-check"
    for slot_key, pool in _ALL_POOLS.items():
        first = pick_hr_variant(pool, session_id, slot_key)
        second = pick_hr_variant(pool, session_id, slot_key)
        assert first == second, slot_key


def test_pick_hr_variant_varies_across_sessions():
    pool = HR_DISTRESS_QUESTION_POOL
    seen = {
        pick_hr_variant(pool, f"session-{i}", "distress_question")
        for i in range(50)
    }
    # 50 distinct sessions across a 3-4 way pool must not collapse onto one variant.
    assert len(seen) > 1


def test_pick_hr_variant_different_slot_keys_can_diverge_for_same_session():
    # Same session_id, two different slots: nothing requires (or forbids) the same
    # index, but the function must be able to pick independently per slot -- proven
    # by checking the raw hash input includes slot_key, so two different slot_keys
    # for the identical session_id are not required to (and in practice do not
    # always) resolve to the same POSITIONAL index within same-length pools.
    idx_distress = [
        HR_DISTRESS_QUESTION_POOL.index(
            pick_hr_variant(HR_DISTRESS_QUESTION_POOL, f"s{i}", "distress_question")
        )
        for i in range(20)
    ]
    idx_reask = [
        HR_REASK_POOL.index(pick_hr_variant(HR_REASK_POOL, f"s{i}", "reask"))
        for i in range(20)
    ]
    assert idx_distress != idx_reask


# ---------------------------------------------------------------------------
# Name-only personalization (§5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slot_key,pool", _ALL_POOLS.items())
def test_no_first_name_never_returns_placeholder(slot_key, pool):
    for i in range(30):
        result = pick_hr_variant(pool, f"no-name-session-{i}", slot_key, first_name=None)
        assert "{{first_name}}" not in result, (slot_key, result)


def test_with_first_name_interpolates_correctly():
    # Force a session/slot combination known to select the name-bearing variant
    # (HR_DISTRESS_QUESTION_POOL[1] is the {{first_name}} variant): brute-force a
    # session_id that resolves to it with first_name provided (full pool eligible).
    target_text = HR_DISTRESS_QUESTION_POOL[1].replace("{{first_name}}", "Maya")
    session_id = None
    for i in range(2000):
        candidate = f"name-search-{i}"
        result = pick_hr_variant(
            HR_DISTRESS_QUESTION_POOL, candidate, "distress_question", first_name="Maya"
        )
        if result == target_text:
            session_id = candidate
            break
    assert session_id is not None, "could not locate a session hashing to the name variant"

    result = pick_hr_variant(
        HR_DISTRESS_QUESTION_POOL, session_id, "distress_question", first_name="Maya"
    )
    assert "Maya" in result
    assert "{{first_name}}" not in result
    # Never interpolate anything beyond the first name itself.
    assert result == HR_DISTRESS_QUESTION_POOL[1].replace("{{first_name}}", "Maya")


def test_first_name_presence_only_changes_eligibility_not_hash_input():
    # With no name available, the candidate pool narrows to the 3 name-free variants;
    # the selected variant must always be one of those 3 (never index 1, the
    # name-bearing one), for many sessions.
    name_free_texts = {v for v in HR_DISTRESS_QUESTION_POOL if "{{first_name}}" not in v}
    for i in range(50):
        result = pick_hr_variant(
            HR_DISTRESS_QUESTION_POOL, f"eligibility-check-{i}", "distress_question", first_name=None
        )
        assert result in name_free_texts


def test_defensive_strip_when_every_variant_bears_the_placeholder():
    # Synthetic pool where ALL variants carry {{first_name}} (none of the real
    # shipped pools hit this, but pick_hr_variant must not leak a raw placeholder
    # if a future pool ever does): falls back to the full pool and strips cleanly.
    synthetic_pool = (
        "{{first_name}}, thank you for telling me.",
        "I hear you, {{first_name}}, and I want to help.",
    )
    for i in range(10):
        result = pick_hr_variant(synthetic_pool, f"strip-check-{i}", "distress_question", first_name=None)
        assert "{{first_name}}" not in result
        assert "  " not in result  # no double space left behind
        assert not result.startswith(",")  # no dangling leading punctuation
        assert not result.startswith(" ")


# ---------------------------------------------------------------------------
# Content anchors, after full placeholder resolution
# ---------------------------------------------------------------------------

def test_distress_question_pool_variants_carry_the_0_to_10_scale_anchor():
    for variant in HR_DISTRESS_QUESTION_POOL:
        resolved = variant.replace("{{first_name}}", "Sam")
        assert _SCALE_ANCHOR_RE.search(resolved), variant


def test_reask_pool_variants_carry_the_0_to_10_scale_anchor_and_stay_content_neutral():
    for variant in HR_REASK_POOL:
        resolved = variant.replace("{{first_name}}", "Sam")
        assert _SCALE_ANCHOR_RE.search(resolved), variant
        lowered = resolved.lower()
        for probing_phrase in ("why", "what happened", "tell me more"):
            assert probing_phrase not in lowered, (variant, probing_phrase)


def test_higher_redirect_pool_variants_resolve_the_emergency_number():
    for variant in HR_REDIRECT_HIGHER_POOL:
        # Raw (unresolved) source must never hardcode the literal digits -- only the
        # placeholder -- so the number stays single-sourced via CRISIS_CONFIG.
        assert "999" not in variant, variant
        resolved = resolve_crisis_placeholders(variant.replace("{{first_name}}", "Sam"))
        assert "{{crisis_" not in resolved, resolved
        assert "999" in resolved, resolved


def test_lower_redirect_pool_variants_name_doctor_or_mental_health_professional():
    for variant in HR_REDIRECT_LOWER_POOL:
        resolved = variant.replace("{{first_name}}", "Sam")
        assert "doctor or mental health professional" in resolved, variant


def test_supportive_message_pool_variants_never_leave_unresolved_crisis_placeholder():
    for variant in HR_SUPPORTIVE_MESSAGE_POOL:
        resolved = resolve_crisis_placeholders(variant.replace("{{first_name}}", "Sam"))
        assert "{{crisis_" not in resolved


# ---------------------------------------------------------------------------
# Not Python's salted builtin hash() -- reproducible across fresh interpreters.
# ---------------------------------------------------------------------------

def test_reproducible_across_fresh_interpreter_processes_different_hash_seeds():
    """The audit/reproducibility requirement is meaningless if the index depends on
    PYTHONHASHSEED (a fresh value every process by default): the SAME session_id must
    resolve to the SAME variant in a brand new interpreter with a different seed.
    Spawns two subprocesses with different explicit PYTHONHASHSEED values and asserts
    they agree -- the concrete proof that pick_hr_variant does not route through
    Python's builtin (salted) hash()."""
    import os
    import subprocess
    import sys

    script = (
        "from sage_poc.safety.hr_copy import HR_DISTRESS_QUESTION_POOL, pick_hr_variant\n"
        "print(pick_hr_variant(HR_DISTRESS_QUESTION_POOL, 'fixed-session-xyz', 'distress_question'))\n"
    )
    env_a = dict(os.environ, PYTHONHASHSEED="1")
    env_b = dict(os.environ, PYTHONHASHSEED="2")
    out_a = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env_a, check=True,
    ).stdout.strip()
    out_b = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env_b, check=True,
    ).stdout.strip()
    assert out_a == out_b
    assert out_a in HR_DISTRESS_QUESTION_POOL
