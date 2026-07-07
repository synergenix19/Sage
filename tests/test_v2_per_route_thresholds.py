"""Calibrated-V2 behavior #1: per-route, per-language thresholds.

Flag-off: the global SEMANTIC_THRESHOLD (0.4593) — byte-identical to V1.
Flag-on: each candidate route gated by ITS OWN (lang, route) τ from the calibrated table,
global fallback for an unseen route or when no table is loaded. The lookup is per-(lang, route)
with NO pooling — the fifth and final place the F8 'aggregate masks a weak cell' artifact could
reappear, here on the live path.
"""
from sage_poc.nodes import skill_select as ss
from sage_poc.nodes.skill_select import routing_threshold, SEMANTIC_THRESHOLD
from sage_poc.routing_eval.calibration import ThresholdTable


def _table(per_route):
    return ThresholdTable(per_route=per_route, cluster={}, route_cluster={}, fallback=frozenset())


def test_flag_off_threshold_is_global_byte_identical(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", _table({("en", "box_breathing"): 0.55}))
    # even with a table present, flag-off must ignore it and return global
    assert routing_threshold("en", "box_breathing") == SEMANTIC_THRESHOLD


def test_flag_on_without_table_falls_back_to_global(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", None)
    assert routing_threshold("en", "box_breathing") == SEMANTIC_THRESHOLD


def test_flag_on_with_table_returns_per_route_tau(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", _table({("en", "box_breathing"): 0.55}))
    assert routing_threshold("en", "box_breathing") == 0.55


def test_flag_on_unseen_route_falls_back_to_global(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", _table({("en", "box_breathing"): 0.55}))
    assert routing_threshold("ar", "worry_time") == SEMANTIC_THRESHOLD


def test_thresholds_are_per_language(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", _table({("en", "worry_time"): 0.60, ("ar", "worry_time"): 0.50}))
    assert routing_threshold("en", "worry_time") == 0.60
    assert routing_threshold("ar", "worry_time") == 0.50
