"""§3a low-mood validate-first + woven-safety flow.

Task 1: flag + cross-turn state fields (SAGE_LOW_MOOD_SCREEN, screen_stage,
safety_probe_asked). The two state fields are CROSS-TURN — they must NOT be
reset per-turn in server_helpers._build_state, or the SI probe would clear
before the answer turn reads it.
"""
import inspect

from sage_poc import config
from sage_poc.state import SageState


def test_flag_defaults_off():
    # Default OFF => byte-identical to today's §3a offer path.
    assert config.LOW_MOOD_SCREEN_ENABLED is False


def test_state_declares_screen_fields():
    assert "screen_stage" in SageState.__annotations__
    assert "safety_probe_asked" in SageState.__annotations__


def test_screen_fields_not_in_per_turn_reset():
    # CROSS-TURN invariant: neither field may appear in _build_state's per-turn
    # reset block, or the probe clears before safety_check reads the answer.
    import sage_poc.server_helpers as sh

    src = inspect.getsource(sh._build_state)
    assert "screen_stage" not in src
    assert "safety_probe_asked" not in src
