import pytest
from sage_poc.prompts.loader import get_template, get_intent_template, reload_all
from sage_poc.prompts.schemas import PromptTemplate


@pytest.fixture(autouse=True)
def reset_cache():
    reload_all()
    yield
    reload_all()


def test_loader_raises_key_error_for_unknown_template():
    with pytest.raises(KeyError):
        get_template("nonexistent_id")


def test_get_intent_template_returns_none_for_unknown_intent():
    assert get_intent_template("completely_unknown_intent") is None


def test_prompt_template_pydantic_validates():
    data = {
        "template_id": "test_tmpl",
        "version": "1.0.0",
        "effective_date": "2026-05-22",
        "layer": "L0",
        "role": "system",
        "always_include": True,
        "word_budget": 100,
        "content": "Hello world",
    }
    tmpl = PromptTemplate.model_validate(data)
    assert tmpl.template_id == "test_tmpl"
    assert tmpl.variables == []
    assert tmpl.intent is None


def test_get_template_loads_from_disk(tmp_path, monkeypatch):
    """Verify the loader actually reads JSON files from disk and parses them."""
    import sage_poc.prompts.loader as loader_module

    tmpl_json = {
        "template_id": "fixture_tmpl",
        "version": "1.0.0",
        "effective_date": "2026-05-22",
        "layer": "L0",
        "role": "system",
        "always_include": True,
        "word_budget": 50,
        "content": "Hello from fixture",
    }
    (tmp_path / "fixture_tmpl.json").write_text(
        __import__("json").dumps(tmpl_json), encoding="utf-8"
    )

    monkeypatch.setattr(loader_module, "_DATA_DIR", tmp_path)
    reload_all()

    tmpl = get_template("fixture_tmpl")
    assert tmpl.template_id == "fixture_tmpl"
    assert tmpl.content == "Hello from fixture"
    assert tmpl.layer == "L0"
