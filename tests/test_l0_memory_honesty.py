import json, pathlib

_L0 = pathlib.Path("src/sage_poc/prompts/templates/L0_persona.json")


def test_l0_has_memory_honesty_clause_and_version_bump():
    data = json.loads(_L0.read_text(encoding="utf-8"))
    assert data["version"] == "2.3.0", "version must be bumped for the memory-honesty clause"
    content = data["content"].lower()
    assert "memory" in content
    # must instruct honest 'I don't have access' and forbid false denial
    assert "do not have access" in content or "don't have access" in content
    assert "never claim" in content
    # word budget must still accommodate the content
    assert len(data["content"].split()) <= data["word_budget"]
