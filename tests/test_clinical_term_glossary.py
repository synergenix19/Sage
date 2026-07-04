"""W5 (G6) — therapy-term glossary in the Khaleeji translation prompt.

The glossary anchors CBT/ACT/DBT technique names so the translator renders them as clinically
sensible Arabic, never literal ("للتواصل مع الأرض" grounding-class errors). Glossary is DATA
(clinician-extendable term-map); the prompt-injection is the mechanism this tests deterministically.
"""
from sage_poc.language import _clinical_glossary, _build_khaleeji_translation_prompt


def test_glossary_loads_as_data():
    g = _clinical_glossary()
    terms = {t["en"]: t["ar"] for t in g["terms"]}
    assert "grounding" in terms
    assert terms["grounding"] == "تمرين التأريض الحسي"
    assert "للتواصل مع الأرض" not in terms["grounding"]  # the literal-error class is excluded


def test_prompt_injects_glossary_terms():
    # A message mentioning clinical terms carries their pinned AR renderings into the translator prompt.
    prompt = _build_khaleeji_translation_prompt("Let's try a grounding technique and box breathing.")
    assert "تمرين التأريض الحسي" in prompt or "تقنية التأريض الحسي" in prompt
    assert "تنفّس الصندوق" in prompt
    assert "grounding" in prompt.lower()


def test_prompt_only_injects_terms_present_in_text():
    # A message with no clinical term should not bloat the prompt with the whole glossary.
    prompt = _build_khaleeji_translation_prompt("How are you feeling today?")
    assert "التنشيط السلوكي" not in prompt  # behavioral activation not mentioned -> not injected


def test_glossary_preserves_exemplars_and_structure():
    # The glossary addition must not drop the few-shot exemplars or the translate instruction.
    prompt = _build_khaleeji_translation_prompt("Let's try box breathing.")
    assert "Examples:" in prompt
    assert prompt.rstrip().endswith("Arabic:")
