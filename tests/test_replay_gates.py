from scripts.register_eval.replay_gates import gate_fire_summary


def test_summary_counts_and_rate():
    rows = [{"cultural_fired": ["general_cultural"], "banned_opener": False, "format_tokens": []},
            {"cultural_fired": [], "banned_opener": True, "format_tokens": ["*"]},
            {"cultural_fired": [], "banned_opener": False, "format_tokens": []}]
    s = gate_fire_summary(rows)
    assert s["n"] == 3 and s["cultural_fires"] == 1 and s["banned_opener_fires"] == 1
    assert s["any_gate_fire_rate"] == round(2/3, 4)
