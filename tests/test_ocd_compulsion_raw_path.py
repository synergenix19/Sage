"""#330 code half — the veto reads RAW input (pass-raw plumbing), independent of AR patterns.

Proves the language-contract fix WITHOUT shipping clinician-gated Arabic content: an EN compulsion
supplied in the raw position must fire even when the translated position is empty/benign. The
native Arabic patterns that actually close the AR bypass are dual-clinician-gated and land in a
separate PR — this file is the infrastructure proof, not the bypass closure.
"""
from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion
from sage_poc.state import safety_text


def test_detector_reads_raw_position_not_only_first():
    # EN compulsion in the raw (second) position fires even when the translated (first) is benign.
    assert is_ocd_compulsion("how are you today", "i keep checking the lock and can't stop")


def test_single_arg_backward_compatible():
    assert is_ocd_compulsion("i keep checking the lock") is True
    assert is_ocd_compulsion("") is False
    assert is_ocd_compulsion() is False


def test_safety_text_returns_raw():
    assert safety_text({"raw_message": "الأصل", "message_en": "translated"}) == "الأصل"
    assert safety_text({"raw_message": "", "message_en": "x"}) == ""  # raw is authoritative; no fallback
