"""Regression guard for the safety-file AR-parity gate (#329/#330)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_safety_language_parity as parity


def test_parity_gate_passes():
    """medical_redflag must be genuinely covered (not exempt); the gate passes overall."""
    assert parity.main() == 0, "safety-file AR parity gate failed — a new EN-only safety file?"


def test_medical_redflag_not_exempt_and_covered():
    en, ar = parity.audit_file(parity._SAFETY_DIR / "medical_redflag_phrases.json")
    assert "medical_redflag_phrases.json" not in parity.EXEMPT, "#329 must be real coverage, not exempt"
    assert ar > 0 and en > 0, f"medical_redflag lost AR coverage: en={en} ar={ar}"
