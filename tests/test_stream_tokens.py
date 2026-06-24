"""The streaming emitter must preserve newlines so L4 line structure (numbered
lists) survives to the client. Regression guard for the wall-of-text bug:
server.py used response_text.split(), which collapsed all newlines."""


def test_stream_tokens_reconstructs_text_exactly():
    from server import _stream_tokens
    text = "Anxiety is natural.\n1. Cognitive.\n2. Physical.\n3. Emotional."
    assert "".join(_stream_tokens(text)) == text


def test_stream_tokens_preserves_newlines():
    from server import _stream_tokens
    text = "intro line\n1. one\n2. two"
    joined = "".join(_stream_tokens(text))
    assert joined.count("\n") == 2
    assert joined == text


def test_stream_tokens_emits_multiple_chunks_for_streaming():
    from server import _stream_tokens
    toks = _stream_tokens("a b c")
    assert len(toks) > 1  # still chunked for the typing effect


def test_stream_tokens_does_not_add_artificial_trailing_space():
    from server import _stream_tokens
    # Old code yielded word+" ", turning "x\ny" into "x y ". Must not happen.
    assert "".join(_stream_tokens("x\ny")) == "x\ny"


def test_stream_tokens_preserves_arabic_and_newlines():
    from server import _stream_tokens
    text = "الاكتئاب يؤثر على النوم.\n1. تعب مستمر.\n2. فقدان الاهتمام."
    assert "".join(_stream_tokens(text)) == text


def test_stream_tokens_empty():
    from server import _stream_tokens
    assert _stream_tokens("") == []
