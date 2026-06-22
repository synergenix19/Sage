import pytest
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


# NOTE: These two tests make real API calls — skip with: pytest -m "not slow"


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


# ---- Prompt content tests (mocked — no API calls) --------------------------------
# These verify the prompt string sent to the LLM, not translation quality.
# Quality is validated separately by a native Khaleeji speaker (see plan Task 4).

from unittest.mock import AsyncMock, MagicMock, patch


# ---- translate_to_arabic (sync) --------------------------------------------------

def test_translate_to_arabic_prompt_specifies_khaleeji():
    """translate_to_arabic must request Khaleeji dialect, not Modern Standard Arabic."""
    captured = {}

    def mock_invoke(messages):
        captured["messages"] = messages
        resp = MagicMock()
        resp.content = "مرحبا"
        return resp

    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke

    with patch("sage_poc.llm.get_translator", return_value=mock_llm):
        from sage_poc.language import translate_to_arabic
        translate_to_arabic("Hello, how are you feeling today?")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" in prompt, (
        f"'Khaleeji' not found in translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "not formal or clinical Modern Standard Arabic" in prompt, (
        f"Prompt must explicitly steer away from MSA, not request it.\nGot: {prompt}"
    )


def test_translate_to_arabic_prompt_contains_wellness_context():
    """translate_to_arabic must include Sage identity and warmth instruction."""
    captured = {}

    def mock_invoke(messages):
        captured["messages"] = messages
        resp = MagicMock()
        resp.content = "مرحبا"
        return resp

    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke

    with patch("sage_poc.llm.get_translator", return_value=mock_llm):
        from sage_poc.language import translate_to_arabic
        translate_to_arabic("That sounds really hard. What's been most difficult for you?")

    prompt = captured["messages"][0]["content"]
    assert "Sage" in prompt, (
        f"'Sage' not found in translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "warm" in prompt.lower(), (
        f"No warmth instruction in translate_to_arabic prompt.\nGot: {prompt}"
    )


def test_translate_to_arabic_returns_original_on_failure():
    """translate_to_arabic must return the original English text when the LLM call fails."""
    with patch("sage_poc.llm.get_translator", side_effect=RuntimeError("API down")):
        from sage_poc.language import translate_to_arabic
        result = translate_to_arabic("Fallback text that must survive")
    assert result == "Fallback text that must survive"


# ---- async_translate_to_arabic ---------------------------------------------------

@pytest.mark.asyncio
async def test_async_translate_to_arabic_prompt_specifies_khaleeji():
    """async_translate_to_arabic must request Khaleeji dialect."""
    captured = {}

    async def mock_resilient_invoke(llm, messages, node, language):
        captured["messages"] = messages
        return "مرحبا"

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_arabic
            await async_translate_to_arabic("Hello, how are you feeling today?")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" in prompt, (
        f"'Khaleeji' not found in async_translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "not formal or clinical Modern Standard Arabic" in prompt, (
        f"Prompt must explicitly steer away from MSA, not request it.\nGot: {prompt}"
    )


@pytest.mark.asyncio
async def test_async_translate_to_arabic_prompt_contains_wellness_context():
    """async_translate_to_arabic must include Sage identity and warmth instruction."""
    captured = {}

    async def mock_resilient_invoke(llm, messages, node, language):
        captured["messages"] = messages
        return "مرحبا"

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_arabic
            await async_translate_to_arabic("That makes complete sense.")

    prompt = captured["messages"][0]["content"]
    assert "Sage" in prompt, (
        f"'Sage' not found in async_translate_to_arabic prompt.\nGot: {prompt}"
    )
    assert "warm" in prompt.lower(), (
        f"No warmth instruction in async_translate_to_arabic prompt.\nGot: {prompt}"
    )


@pytest.mark.asyncio
async def test_async_translate_to_arabic_returns_original_on_empty_result():
    """async_translate_to_arabic must return the original text when resilient_invoke returns empty."""
    async def mock_resilient_invoke(llm, messages, node, language):
        return ""

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_arabic
            result = await async_translate_to_arabic("English fallback text")

    assert result == "English fallback text"


# ---- English translation functions — must NOT be affected -------------------------

def test_translate_to_english_prompt_unchanged():
    """translate_to_english must NOT include Khaleeji or therapeutic context.

    This function feeds safety classification (S1/S3) and intent routing.
    Therapeutic framing would bias those classifiers away from literal meaning.
    """
    captured = {}

    def mock_invoke(messages):
        captured["messages"] = messages
        resp = MagicMock()
        resp.content = "I am scared"
        return resp

    mock_llm = MagicMock()
    mock_llm.invoke = mock_invoke

    with patch("sage_poc.llm.get_translator", return_value=mock_llm):
        from sage_poc.language import translate_to_english
        translate_to_english("أنا خائف")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" not in prompt, (
        f"Khaleeji instruction leaked into translate_to_english prompt.\nGot: {prompt}"
    )
    assert "English" in prompt, (
        f"'English' target language missing from translate_to_english prompt.\nGot: {prompt}"
    )


@pytest.mark.asyncio
async def test_async_translate_to_english_prompt_unchanged():
    """async_translate_to_english must NOT include Khaleeji or therapeutic context."""
    captured = {}

    async def mock_resilient_invoke(llm, messages, node, language):
        captured["messages"] = messages
        return "I am scared"

    mock_llm = MagicMock()

    with patch("sage_poc.resilience.resilient_invoke", mock_resilient_invoke):
        with patch("sage_poc.language.get_translator", return_value=mock_llm):
            from sage_poc.language import async_translate_to_english
            await async_translate_to_english("أنا خائف")

    prompt = captured["messages"][0]["content"]
    assert "Khaleeji" not in prompt, (
        f"Khaleeji instruction leaked into async_translate_to_english.\nGot: {prompt}"
    )
    assert "English" in prompt


# text_direction: authoritative source for the X-Sage-Direction response header.
def test_text_direction_arabic_is_rtl():
    from sage_poc.language import text_direction
    assert text_direction("ar") == "rtl"


def test_text_direction_english_is_ltr():
    from sage_poc.language import text_direction
    assert text_direction("en") == "ltr"


def test_text_direction_unknown_or_missing_defaults_ltr():
    from sage_poc.language import text_direction
    assert text_direction(None) == "ltr"
    assert text_direction("fr") == "ltr"
