import json, pathlib

_L0 = pathlib.Path("src/sage_poc/prompts/templates/L0_persona.json")


def test_l0_memory_clause_splits_present_and_absent_v2_4_0():
    """v2.4.0 fixes the v2.3.0 false-denial regression: the clause must answer from history
    that IS present and admit ONLY when genuinely absent (preserving A4), never deny visible
    history. Behavioural proof is tests/test_l0_memory_clause.py (live_llm); this is the fast
    structural gate on the clause text."""
    data = json.loads(_L0.read_text(encoding="utf-8"))
    assert data["version"] == "2.4.0", "version must be bumped for the v2.4.0 clause fix"
    content = data["content"].lower()
    assert "memory" in content
    # present side: answer from history that is visible
    assert "answer from it" in content
    # absent side: admit only when genuinely not present
    assert "genuinely not present" in content and "cannot see it" in content
    # anti-false-denial guard (the v2.3.0 regression this fixes)
    assert "never deny or contradict something that is visible" in content
    # A4 still preserved: never claim they did not say something they did
    assert "never claim they did not say" in content
    # word budget must still accommodate the content
    assert len(data["content"].split()) <= data["word_budget"]
