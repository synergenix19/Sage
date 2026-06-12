"""Content guards for the 2026-06-12 engagement-layer changes (R1 + R3).

Pins template content, blurb coverage, and composer offer selection so future
edits that silently regress engagement behavior fail CI instead of shipping.
"""
# NOTE: TestOfferDescriptionsCoverage reads offer_descriptions.json directly from
# disk (no loader cache involved), so the autouse _fresh_templates fixture is
# irrelevant to it by design.
import json
from pathlib import Path

import pytest

from sage_poc.prompts.loader import get_intent_template, reload_all

_PROMPTS_DIR = Path(__import__("sage_poc.prompts", fromlist=["__file__"]).__file__).parent


@pytest.fixture(autouse=True)
def _fresh_templates():
    reload_all()
    yield
    reload_all()


class TestR3GeneralChatEngageThenBridge:
    def test_deflection_clause_removed(self):
        tmpl = get_intent_template("general_chat")
        assert "rather than engaging with the topic itself" not in tmpl.content, (
            "R3 regression: the scope-wall deflection clause is back in L2_general_chat"
        )

    def test_engage_then_bridge_wording_present(self):
        tmpl = get_intent_template("general_chat")
        assert "engage with the topic itself briefly" in tmpl.content
        assert "Never deflect" in tmpl.content

    def test_template_version_is_1_3_0(self):
        tmpl = get_intent_template("general_chat")
        assert tmpl.version == "1.3.0"

    def test_no_em_dash_in_content(self):
        tmpl = get_intent_template("general_chat")
        assert "—" not in tmpl.content, "em dashes mirror into LLM output; use commas"


class TestOfferDescriptionsCoverage:
    _PATH = _PROMPTS_DIR / "offer_descriptions.json"

    def _load(self) -> dict:
        return json.loads(self._PATH.read_text(encoding="utf-8"))["descriptions"]

    def test_every_offerable_skill_has_a_description(self):
        from sage_poc.skill_ids import SKILL_REGISTRY
        from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
        descs = self._load()
        offerable = [s for s in SKILL_REGISTRY if s not in KEYWORD_SEMANTIC_SKIP]
        offerable_set = set(offerable)
        missing = [s for s in offerable if s not in descs]
        assert not missing, (
            f"offer_descriptions.json missing blurbs for: {missing}. Every offerable "
            "skill needs one or its offers fall back to the bare skill_name."
        )
        phantom = [s for s in descs if s not in offerable_set]
        assert not phantom, (
            f"offer_descriptions.json has blurbs for non-offerable/unknown skills: {phantom}. "
            "Remove or migrate these entries when a skill is renamed or removed."
        )

    def test_bilingual_envelope_and_clean_content(self):
        from sage_poc.corpus_constants import PLACEHOLDER_MARKERS
        descs = self._load()
        for sid, entry in descs.items():
            assert len(entry["display_name"]["en"]) <= 50, f"{sid}: display_name too long for a UI label"
            for field in ("display_name", "description"):
                assert set(entry[field].keys()) == {"en", "ar"}, (
                    f"{sid}.{field}: bilingual envelope {{en, ar}} required"
                )
                en = entry[field]["en"]
                assert en and en.strip(), f"{sid}.{field}.en empty"
                assert "—" not in en, f"{sid}.{field}: em dash in content"
                ar = entry[field]["ar"]
                if ar is not None:
                    assert ar and ar.strip(), f"{sid}.{field}.ar present but empty"
                    assert "—" not in ar, f"{sid}.{field}: em dash in ar content"
                    for marker in PLACEHOLDER_MARKERS:
                        assert marker not in ar, (
                            f"{sid}.{field}.ar contains placeholder marker {marker!r}"
                        )
            assert len(entry["description"]["en"]) <= 160, f"{sid}: blurb too long for an offer line"
