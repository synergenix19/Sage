from sage_poc.language import detect_language, translate_to_english, translate_to_arabic


def test_detect_english():
    assert detect_language("I feel really sad today") == "en"


def test_detect_arabic():
    lang = detect_language("أشعر بالحزن الشديد اليوم")
    assert lang in ("ar", "fa")  # langdetect sometimes confuses ar/fa


def test_detect_mixed():
    # Arabic Unicode chars override langdetect — code-switched message classified as Arabic
    lang = detect_language("I feel بخير today, maybe things will get better")
    assert lang == "ar"


# NOTE: These two tests make real Ollama calls — skip with: pytest -m "not slow"
import pytest


@pytest.mark.slow
def test_translate_arabic_to_english():
    result = translate_to_english("أنا أشعر بالخوف الشديد")
    assert isinstance(result, str)
    assert len(result) > 5
    result_lower = result.lower()
    assert any(word in result_lower for word in ["fear", "scared", "afraid", "anxious", "intense"])


@pytest.mark.slow
def test_translate_english_to_arabic():
    result = translate_to_arabic("I am here to support you.")
    assert isinstance(result, str)
    # Arabic text contains Arabic Unicode chars
    assert any('؀' <= c <= 'ۿ' for c in result)
