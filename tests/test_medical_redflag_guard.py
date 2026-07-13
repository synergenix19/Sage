from sage_poc.safety.medical_redflag import detect_medical_redflag
import typing

def test_state_declares_medical_channel():
    from sage_poc.state import SageState
    hints = typing.get_type_hints(SageState)
    assert "medical_flags" in hints, "medical_flags must be a declared channel (LangGraph drops undeclared keys)"

def test_gate_path_allows_medical():
    from sage_poc.state import SageState
    hints = typing.get_type_hints(SageState)
    assert "medical" in str(hints["gate_path"])

# The VERBATIM escalation trace. Do not adjust this string to fit the phrase list.
LIVE_TRACE = "crushing pain in my chest spreading to my jaw, my left arm's gone numb"
# The same presentation with the one clause that trivially matched removed. A textbook
# cardiac presentation phrased the way people actually phrase it — MUST still fire.
JAWLESS_VARIANT = "crushing pain in my chest, my left arm's gone numb"

def test_live_trace_fires():
    assert detect_medical_redflag(LIVE_TRACE) != []

def test_jawless_variant_fires():
    # If this fails, the phrase list is wrong — extend it (word-order/proximity
    # variants), never narrow this test.
    assert detect_medical_redflag(JAWLESS_VARIANT) != []

def test_crushing_variant_isolated_forces_word_order_entry():
    # No numbness/jaw clause — only the word-order variant can match. If crushing_variant
    # is deleted or broken, this fails (the other entries cannot cover it).
    ids = detect_medical_redflag("I have crushing pain in my chest")
    assert "crushing_variant" in ids, ids
    # And the verbatim §1 literal (different word order) still matches its own entry:
    assert "crushing" in detect_medical_redflag("this is crushing chest pain")

def test_must_not_fire_controls_stay_clear():
    # Panic negatives AND benign-numbness negatives. Benign limb-numbness (no
    # laterality) must NOT route to a medical emergency — §1's criterion is one-sided.
    for benign in ("racing heart", "tight chest", "shallow breath",
                   "my chest feels a little tight", "my heart is racing from the panic",
                   "my foot's gone numb from sitting",
                   "my hand went numb from sleeping on it",
                   "my leg's gone numb from sitting cross-legged"):
        assert detect_medical_redflag(benign) == [], benign
