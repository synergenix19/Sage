import re

from sage_poc.language import _build_khaleeji_translation_prompt, _khaleeji_exemplars


def test_exemplar_file_is_well_formed():
    data = _khaleeji_exemplars()
    assert data["dialect_name"]
    exemplars = data["exemplars"]
    assert len(exemplars) >= 3, "few-shot needs at least 3 pairs"
    for ex in exemplars:
        assert ex["en"].strip(), "English side must be non-empty"
        assert ex["ar"].strip(), "Arabic side must be non-empty"
        assert re.search(r"[؀-ۿ]", ex["ar"]), "Arabic side must contain Arabic script"


def test_prompt_is_few_shot_and_names_the_dialect():
    prompt = _build_khaleeji_translation_prompt("I am here for you.")
    data = _khaleeji_exemplars()
    # Dialect named explicitly (research: naming beats codes)
    assert data["dialect_name"] in prompt
    # Every exemplar appears (the few-shot block)
    for ex in data["exemplars"]:
        assert ex["en"] in prompt
        assert ex["ar"] in prompt
    # The text to translate is included
    assert "I am here for you." in prompt
    # Consistency instruction present
    assert "consistent" in prompt.lower()
