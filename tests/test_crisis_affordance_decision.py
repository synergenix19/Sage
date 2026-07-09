"""#205 — crisis affordance follows the routing PATH, not the initial tier, + a path-consistency
backstop that flags the mismatch.

`_crisis_affordance_decision` is the pure decision extracted from the /chat emit boundary (server.py
lives at the repo root, so `from server import ...`). Returns (emit_card, path_consistency_mismatch).

The failure #205 caught: a monitoring-continuation turn ran crisis_response at crisis_tier="none"
(a continuation-context recall miss the monitoring state rescued into crisis_response); the old
tier-only emit dropped the card, shipping crisis content with no tap-to-call. Affordance must follow
the path; the mismatch must be surfaced for clinical review.
"""
from server import _crisis_affordance_decision


def _d(**kw):
    base = dict(gate_path=None, crisis_tier=None, path=[], is_safe=True, tiering_enabled=True)
    base.update(kw)
    return _crisis_affordance_decision(**base)


class TestAffordanceFollowsPath:
    def test_205_scenario_gate_path_crisis_but_tier_none_forces_card_and_flags_mismatch(self):
        # The exact #205 turn: crisis_response ran (gate_path='crisis') at crisis_tier='none'.
        emit, mismatch = _d(gate_path="crisis", crisis_tier="none")
        assert emit is True         # card forced by the path (was False under tier-only)
        assert mismatch is True     # backstop flags the recall miss for clinical review

    def test_crisis_response_in_node_path_also_forces_card(self):
        emit, mismatch = _d(path=["safety_check", "crisis_response"], crisis_tier="none")
        assert emit is True
        assert mismatch is True

    def test_t2_emits_card_with_no_mismatch(self):
        emit, mismatch = _d(gate_path="crisis", crisis_tier="T2")
        assert emit is True
        assert mismatch is False    # tier agreed — not a mismatch

    def test_t1_warm_turn_no_card_no_mismatch(self):
        # T1 is warm (no card) and did NOT run crisis_response.
        emit, mismatch = _d(gate_path="standard", crisis_tier="T1", path=["safety_check", "freeflow_respond"])
        assert emit is False
        assert mismatch is False

    def test_ordinary_turn_no_card(self):
        emit, mismatch = _d(gate_path="standard", crisis_tier="none", path=["safety_check", "freeflow_respond"])
        assert emit is False
        assert mismatch is False


class TestTieringDisabledLegacyPath:
    def test_flag_off_uses_is_safe_but_path_still_forces_and_flags(self):
        # Tiering OFF: card = not is_safe. A crisis path with is_safe True (the miss) still forces + flags.
        emit, mismatch = _d(tiering_enabled=False, gate_path="crisis", is_safe=True)
        assert emit is True
        assert mismatch is True

    def test_flag_off_not_safe_emits_card_no_mismatch(self):
        emit, mismatch = _d(tiering_enabled=False, is_safe=False, path=["safety_check", "crisis_response"])
        assert emit is True
        assert mismatch is False     # is_safe already said crisis
