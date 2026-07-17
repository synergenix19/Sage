"""Regression guard for the safety-reads-raw language-contract gate (#330, ADR 2026-07-16)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_safety_reads_raw as gate


def test_gate_passes():
    assert gate.main() == 0, "a safety detector reads translated message_en without raw"


def test_ocd_is_conformed_not_allowlisted():
    """#330 must be a real fix (call via safety_text), never parked in the allowlist."""
    assert not any("is_ocd_compulsion" in k for k in gate.ALLOWLIST), \
        "ocd_compulsion must read raw via safety_text(), not be allowlisted"
