from sage_poc.nodes.venting_detect import detect_venting


def test_dontfix_signals_detected():
    for m in ("please just listen, I can't handle this anymore",
              "I'm so overwhelmed I just need to get this out, don't try to fix it",
              "I just need to vent", "I don't want advice, just talk"):
        assert detect_venting(m, m, "en") is True, m


def test_non_venting_distress_not_detected():
    # Acute distress WITHOUT a don't-fix signal must NOT be suppressed — the user may want help.
    for m in ("I'm panicking, help me calm down", "my heart is racing, what do I do"):
        assert detect_venting(m, m, "en") is False, m
