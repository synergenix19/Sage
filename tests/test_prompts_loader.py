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
