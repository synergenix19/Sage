import pytest
from sage_poc.nodes.output_gate import _limit_to_one_question, _strip_trailing_question


def test_arabic_question_mark_collapsed():
    # two Arabic questions -> keep only the first
    t = "كيف تشعر اليوم؟ هل نمت جيدا؟"
    out = _limit_to_one_question(t)
    assert out.count("؟") == 1
    assert "كيف تشعر اليوم؟" in out


def test_strip_trailing_arabic_question():
    t = "خذ نفسا عميقا الان. هل تريد المتابعة؟"
    out = _strip_trailing_question(t)
    assert "؟" not in out
    assert "خذ نفسا عميقا الان." in out
