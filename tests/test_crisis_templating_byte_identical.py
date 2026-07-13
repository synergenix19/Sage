"""Byte-identical snapshot proof for crisis-copy templating.

The crisis-copy source files carry ``{{crisis_*}}`` placeholders instead of re-embedded phone
numbers. This test proves the templating mechanism is provably BYTE-IDENTICAL to an authorized
snapshot: for each of the 8 files, resolving the (now templated) live file must reconstruct the
snapshot bytes in tests/fixtures/crisis_originals/ character-for-character. Any accidental drift in
the served crisis text (a stray edit, a lost placeholder, a value that fell out of sync) fails CI.

SNAPSHOT REGENERATED 2026-07-10 for the H4 value adoption (all gates cleared): the snapshots now
carry the doc's verified composition (National Mental Support Line 800-HOPE (800-4673) 8am-8pm,
999, SAKINA/DHA/Sharjah/ER) — SUPERSEDING the pre-adoption origin/master originals ("800 46342" /
"24/7" / "MoHAP Counselling Line"). If a value in CRISIS_RESOURCES ever changes again, this test is
expected to fail — that is correct: it is the anchor proving the mechanism reproduces the AUTHORIZED
output, and the snapshot must be regenerated deliberately alongside the change, never silently.
"""
from pathlib import Path

import pytest

from sage_poc.crisis_copy import resolve_crisis_placeholders

# The 8 crisis-copy sites (verified 2026-07-08). Same inventory as the conformance test.
_CRISIS_COPY_FILES = [
    "rules/data/crisis_content/en_uae.json",
    "rules/data/crisis_content/ar_uae.json",
    "rules/data/prompt_injection/clinical_flag_adaptations.json",
    "rules/data/prompt_injection/third_party_guidance.json",
    "prompts/templates/L0_persona.json",
    "skills/psychotic_referral.json",
    "skills/psychoed_depression.json",
    "skills/post_crisis_check_in.json",
]

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "sage_poc"
_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "crisis_originals"


@pytest.mark.parametrize("rel", _CRISIS_COPY_FILES)
def test_resolved_templated_file_is_byte_identical_to_original(rel: str):
    original = (_FIXTURE_ROOT / rel).read_text(encoding="utf-8")
    templated = (_SRC_ROOT / rel).read_text(encoding="utf-8")
    resolved = resolve_crisis_placeholders(templated)
    assert resolved == original, (
        f"{rel}: resolve(templated) is NOT byte-identical to the origin/master original. "
        "The templating changed the served text — this must never happen while the config values "
        "equal today's literals."
    )


@pytest.mark.parametrize("rel", _CRISIS_COPY_FILES)
def test_templated_file_actually_carries_a_placeholder(rel: str):
    # Guards against the mechanism silently degrading to raw literals (which would make the
    # byte-identical test above pass trivially without the single-config property). Every one of
    # the 8 files contains at least one crisis number, so every one must carry a placeholder.
    templated = (_SRC_ROOT / rel).read_text(encoding="utf-8")
    assert "{{crisis_" in templated, (
        f"{rel}: expected at least one {{{{crisis_*}}}} placeholder, found none — the file was not "
        "templatized (or the number literal was re-embedded)."
    )
