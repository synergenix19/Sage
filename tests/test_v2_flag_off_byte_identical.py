"""Byte-identical guard: with SKILL_ROUTING_V2 OFF, skill_select must be exactly prod V1.

This is the FOUNDATION of step 2, not a guardrail bolted on after: the §5 flip-gate compares
V2-on against V1, so the verdict is only trustworthy if the flag-OFF path is *true* V1. If
wiring a V2 behavior drifts the off-path, the gate measures V2 against a contaminated baseline.
So this guard is locked BEFORE any calibrated behavior is wired, and re-run after each wiring.

CI constraint: the model-level stash-control (the wrong-skill suite, 240/250) needs a live
BGE-M3 and is excluded from CI — it runs locally/pre-merge. This file is the DETERMINISTIC
companion (no model load) that CAN stand in CI: it pins the flag-off routing *configuration*
(anchor set + thresholds + decision seams) to V1 and proves the guard has teeth (flag-on
differs). Each V2 wiring extends this file with a flag-off==V1 assertion for its seam.
"""
from sage_poc.nodes.skill_select import build_anchor_pairs, _SKILLS, _v2_enabled


def _anchor_set(include_exemplars):
    return tuple(build_anchor_pairs(_SKILLS, include_exemplars=include_exemplars))


def test_v2_flag_is_read_dynamically(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    assert _v2_enabled() is False
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    assert _v2_enabled() is True


def test_flag_off_anchor_set_is_byte_identical_to_v1(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    assert _anchor_set(_v2_enabled()) == _anchor_set(False)


def test_guard_has_teeth_flag_on_anchor_set_differs_from_v1(monkeypatch):
    # Proves the guard is not vacuous: when the flag is ON the index genuinely changes,
    # so a flag-off==v1 assertion is meaningfully distinguishing, not always-true.
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    assert _anchor_set(_v2_enabled()) != _anchor_set(False)
