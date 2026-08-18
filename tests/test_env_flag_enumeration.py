# tests/test_env_flag_enumeration.py
#
# P2 class closure (code_review.md 2026-08-17): env flags read outside config.py
# must be enumerated with EFFECTIVE values, so parity stamps can never silently
# omit them again (the "V2-off locals false-passed" defect class, 3rd recurrence).

import subprocess
import sys
from pathlib import Path

from sage_poc.env_flags import ENUMERATED_ENV_FLAGS, effective_env_flags

REPO = Path(__file__).resolve().parents[1]


def test_gate_script_passes():
    # The static gate is the contract; it must be green on this tree.
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_env_flag_enumeration.py")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_effective_values_track_the_environment(monkeypatch):
    # Effective values must come from the LIVE readers, not import-time constants:
    # flipping the env flips the stamp within the same process.
    monkeypatch.delenv("SKILL_ROUTING_V2", raising=False)
    monkeypatch.delenv("SKILL_RERANK_ENABLED", raising=False)
    off = effective_env_flags()
    assert off["SKILL_ROUTING_V2"] is False
    assert off["SKILL_RERANK_ENABLED"] is False

    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    on = effective_env_flags()
    assert on["SKILL_ROUTING_V2"] is True
    assert on["SKILL_RERANK_ENABLED"] is True


def test_every_enumerated_flag_has_an_effective_value():
    values = effective_env_flags()
    assert set(values) == set(ENUMERATED_ENV_FLAGS)
