from sage_poc.nodes import skill_select as ss


def test_runner_up_dropped_when_below_min():
    ranked = [("worry_time", 0.62), ("financial_anxiety", 0.47)]
    assert ss._select_runner_up(ranked, "worry_time", 0.62) is None  # 0.47 < MIN 0.50


def test_runner_up_dropped_when_outside_margin():
    ranked = [("worry_time", 0.70), ("grief_loss", 0.51)]
    # 0.51 >= MIN but 0.70-0.51=0.19 > MARGIN 0.05
    assert ss._select_runner_up(ranked, "worry_time", 0.70) is None


def test_runner_up_kept_when_strong_and_close():
    ranked = [("worry_time", 0.62), ("psychoed_stress", 0.59)]
    assert ss._select_runner_up(ranked, "worry_time", 0.62) == ("psychoed_stress", 0.59)
