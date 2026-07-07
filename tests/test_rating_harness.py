from scripts.register_eval.rating_harness import build_blinded_sheet, compute_irr, register_delta


def test_blinding_hides_arm_identity():
    sheet = build_blinded_sheet([{"turn_id": "t1", "shipped": "خ1", "shadow": "خ2"}], seed=7)
    row = sheet[0]
    assert set(row["arms"].keys()) == {"A", "B"}
    assert "shipped" not in row and "shadow" not in row
    assert build_blinded_sheet([{"turn_id": "t1", "shipped": "خ1", "shadow": "خ2"}], seed=7)[0]["arms"] == row["arms"]


def test_irr_perfect_is_one():
    assert compute_irr({"r1": [4, 5, 3], "r2": [4, 5, 3]}) == 1.0


def test_register_delta():
    d = register_delta([{"turn_id": "t1", "shipped_score": 3.0, "shadow_score": 4.0},
                        {"turn_id": "t2", "shipped_score": 3.5, "shadow_score": 4.5}])
    assert d["shadow_mean"] == 4.25 and d["shipped_mean"] == 3.25 and d["delta"] == 1.0
    assert d["shadow_meets_kpi"] is True


def test_pairs_joined_by_session_and_turn():
    # Verification #2: table split — shadow (shadow_register_eval) must pair with the
    # served Arabic (messages/session_audit) on (session_id, turn_number), NOT assume one row.
    from scripts.register_eval.rating_harness import pair_by_turn
    shadow_rows = [{"session_id": "s1", "turn_number": 2, "shadow_arabic_text": "خ_shadow"}]
    shipped_rows = [{"session_id": "s1", "turn_number": 2, "arabic_text": "خ_shipped"},
                    {"session_id": "s1", "turn_number": 9, "arabic_text": "خ_other"}]
    pairs = pair_by_turn(shadow_rows, shipped_rows)
    assert len(pairs) == 1
    assert pairs[0]["turn_id"] == "s1:2"
    assert pairs[0]["shadow"] == "خ_shadow" and pairs[0]["shipped"] == "خ_shipped"
