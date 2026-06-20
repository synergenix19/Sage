"""T6 — deterministic output-format strip at Node 8 (output_gate).

Spec: docs/superpowers/plans/2026-06-19-intent-dependent-formatting-knowledge-answers.md (T6).
Closes DEV-2026-06-19-C. Load-bearing since the GPT-primary decision (DEV-B, 2026-06-20):
the model prior is fixed and not retrainable in-house, so this gate is the PRIMARY style
guarantee, not a backstop. Strips ***/**/* paired emphasis + emoji unconditionally;
replaces em-dash with ", " OUTSIDE quoted spans only (false-positive guard: cited content
preserved). Preserves newlines + numbered/hyphen lists + lone-asterisk citation markers.
"""
from sage_poc.nodes.output_gate import _strip_output_format


def test_strip_removes_paired_bold_and_italic():
    assert _strip_output_format("This is **bold** and *italic* text") == "This is bold and italic text"


def test_strip_removes_triple_emphasis():
    assert _strip_output_format("***very***") == "very"


def test_strip_removes_emoji():
    out = _strip_output_format("Take a slow breath \U0001F642\U0001F31F")
    assert "\U0001F642" not in out and "\U0001F31F" not in out
    assert "Take a slow breath" in out


def test_strip_replaces_stylistic_emdash_with_comma():
    assert _strip_output_format("I felt anxious — then it passed") == "I felt anxious, then it passed"
    assert _strip_output_format("work—life balance") == "work, life balance"


def test_strip_preserves_numbered_and_bulleted_lists():
    text = "A few things that help.\n1. A steady sleep schedule\n2. A wind down routine\n- dim the lights"
    assert _strip_output_format(text) == text


def test_strip_preserves_lone_asterisk_citation_marker():
    # false-positive guard (T6.iv): a lone * (footnote/citation marker) is not mangled
    assert _strip_output_format("see the note below*") == "see the note below*"


def test_strip_preserves_emdash_inside_quoted_passage():
    # false-positive guard (T6.iv): a cited em-dash inside quotes is preserved
    text = 'The study notes "participants felt — empty" by week one'
    assert '"participants felt — empty"' in _strip_output_format(text)


def test_strip_arabic_removes_bold_preserves_rtl_list_and_text():
    text = "نصائح للنوم:\n1. **النوم** المنتظم\n2. تجنب الكافيين"
    out = _strip_output_format(text)
    assert "**" not in out
    assert "النوم" in out
    assert "1." in out and "2." in out


def test_strip_arabic_preserves_emdash_inside_quotes():
    text = 'قالت الدراسة "شعرت — بالفراغ" في الأسبوع الأول'
    assert "—" in _strip_output_format(text)


def test_strip_idempotent_and_empty_safe():
    assert _strip_output_format("") == ""
    once = _strip_output_format("**x** — y \U0001F642")
    assert _strip_output_format(once) == once
