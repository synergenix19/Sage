from sage_poc.shadow_eval import build_shadow_eval_row


def _state():
    return {"session_id": "s1", "turn_number": 4, "message_en": "I'm tired",
            "clinical_flags": ["substance"]}


def test_row_from_payload():
    p = {"text": "هلا والله", "prompt_hash": "d" * 16, "exemplar_version": "0.1.0-draft",
         "generation_language": "ar_native", "gen_latency_ms": 812}
    row = build_shadow_eval_row(_state(), p, tool_loop_iterations=0, timed_out=False)
    assert row["session_id"] == "s1" and row["turn_number"] == 4
    assert row["message_en"] == "I'm tired" and row["clinical_flags"] == ["substance"]
    assert row["shadow_arabic_text"] == "هلا والله"
    assert row["tool_loop_iterations"] == 0 and row["shadow_timed_out"] is False


def test_censored_row_on_timeout():
    row = build_shadow_eval_row(_state(), None, tool_loop_iterations=2, timed_out=True)
    assert row["shadow_timed_out"] is True
    assert row["shadow_arabic_text"] is None and row["shadow_gen_latency_ms"] is None
    assert row["tool_loop_iterations"] == 2  # censored obs still records the English-arm tool count
