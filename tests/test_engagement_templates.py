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

    def test_template_version_is_1_5_0(self):
        tmpl = get_intent_template("general_chat")
        # v1.5.0 (2026-06-14): opener changed from "reflect the feeling back before anything
        # else" to a substance-first opener (name the specific thing, then validate) to resolve
        # the L0/L2 conflict; validate-before-inform preserved; R3 engage-then-bridge + Option-A
        # Exception clause preserved. See docs/superpowers/audits/2026-06-14-stock-opener-rca.md
        assert tmpl.version == "1.5.0"

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
            # Blurbs must give enough for an informed choice (clinician-approved 2026-06-17,
            # intensity gating deferred): a bare clause is not enough to decide on a skill
            # without starting it. Lower bound enforces substance; upper bound keeps the
            # offer scannable and within the skill_offer word budget.
            en_desc = entry["description"]["en"]
            assert len(en_desc) >= 110, (
                f"{sid}: blurb too thin for an informed choice ({len(en_desc)} chars). "
                "Say what it is, what you actually do, and what it helps with, plus duration."
            )
            assert len(en_desc) <= 320, f"{sid}: blurb too long for an offer line ({len(en_desc)} chars)"


def _composer_state(**overrides) -> dict:
    base = {
        "raw_message": "I keep worrying about everything",
        "message_en": "I keep worrying about everything",
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "new_clinical_flags_turn": [],
        "third_party_crisis": False,
        "crisis_state": "none",
        "code_switching": False,
        "primary_intent": "new_skill",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 6,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "path": [],
        "turn_count": 1,
    }
    return {**base, **overrides}


class TestSkillOfferComposition:
    def test_offer_template_selected_when_offer_pending(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(offered_skill_ids=["worry_time", "cognitive_restructuring"])
        system_str, user_str, layers = compose_prompt(state)
        assert "Worry time" in user_str, "en display_name from offer_descriptions must be injected"
        assert "Reframing practice" in user_str
        assert "Do not begin any exercise this turn" in user_str
        assert "continuing to talk" in user_str

    def test_unmatched_template_still_used_without_offer(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state()
        system_str, user_str, layers = compose_prompt(state)
        assert "Do not begin any exercise this turn" not in user_str

    def test_offer_template_is_draft_and_clean(self):
        tmpl = get_intent_template("skill_offer")
        assert tmpl is not None
        assert "—" not in tmpl.content
        assert set(tmpl.variables) == {"intensity", "intensity_guidance", "offer_options_block"}

    def test_all_unknown_offer_ids_fall_back_to_intent_l2(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(offered_skill_ids=["ghost_skill_a", "ghost_skill_b"])
        system_str, user_str, layers = compose_prompt(state)
        assert "Do not begin any exercise this turn" not in user_str, (
            "an offer template with a blank options block must never render"
        )

    def test_bilingual_missing_en_degrades_not_crashes(self):
        from sage_poc.prompts.composer import _bilingual
        assert _bilingual({"ar": None}, "en") == ""
        assert _bilingual({}, "ar") == ""

    def test_offer_turn_deducts_from_l1_budget(self):
        from sage_poc.prompts.composer import _compute_l1_budget
        state = _composer_state()
        base = _compute_l1_budget(state)
        reduced = _compute_l1_budget(state, offer_words=120)
        assert reduced == base - 120
