"""Calibrated-V2 behavior #3: anchor-count debias (the §6.1 ranking-bleed counter).

The bias: max-over-anchors scoring gives an anchor-rich skill more shots at a spuriously high
max -> FP bias toward anchor-rich skills (the probe's anchor-count ranking bleed). The mechanism
(an unspecified normalization-vs-cap fork; chosen here = reweight): subtract a small penalty
monotonic in anchor count, normalized to the MINIMUM count, so the least-anchored skill is
unpenalized and only the RELATIVE advantage is removed.

PRECAUTIONARY: shipped per the §3.4 pre-commit (anchor_count/FP correlation is insufficient_power
at N=27 — can't distinguish 'removed' from 'small residual'), NOT validated to remove the bias at
this scale. Likely a modest mover until the library grows divergent anchor counts.

Called only under flag-on; flag-off byte-identical is proven end-to-end by the stash-control diff.
"""
from sage_poc.nodes import skill_select as ss


def test_min_anchor_count_skill_is_unpenalized():
    out = ss._apply_anchor_debias({"a": 0.60, "b": 0.60}, {"a": 1, "b": 5})
    assert out["a"] == 0.60                       # a has the min count -> exactly unchanged


def test_anchor_rich_skill_is_penalized():
    out = ss._apply_anchor_debias({"a": 0.60, "b": 0.60}, {"a": 1, "b": 5})
    assert out["b"] < 0.60                         # more anchors -> reduced score


def test_penalty_is_monotonic_in_anchor_count():
    out = ss._apply_anchor_debias({"a": 0.6, "b": 0.6, "c": 0.6}, {"a": 1, "b": 3, "c": 9})
    assert out["a"] > out["b"] > out["c"]


def test_equal_anchor_counts_is_identity_no_relative_bias():
    inp = {"a": 0.6, "b": 0.55}
    out = ss._apply_anchor_debias(inp, {"a": 4, "b": 4})
    assert out == inp                              # no relative advantage -> no perturbation at all


def test_empty_counts_is_identity():
    inp = {"a": 0.6}
    assert ss._apply_anchor_debias(inp, {}) == inp
