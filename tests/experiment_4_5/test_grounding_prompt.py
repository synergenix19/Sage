"""Experiment 4.5 — Grounding prompt layer tests (L4 knowledge block + compose_prompt).

Tests cover:
  1. _build_l4_knowledge_block() unit contract
  2. compose_prompt() with knowledge passages (L4 fires, citation included)
  3. compose_prompt() with abstain=True (abstain instruction fires)
  4. compose_prompt() without passages (L4 absent)
  5. Knowledge layer ordering (always appears before user message)
  6. Multi-passage citation numbering
  7. Arabic state — L4 still fires (grounding is language-agnostic)
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from tests.experiment_4_5.conftest import make_compose_state, _no_rules


# ---------------------------------------------------------------------------
# 1. _build_l4_knowledge_block() unit contract
# ---------------------------------------------------------------------------

class TestBuildL4KnowledgeBlock:

    def test_formats_single_passage_with_citation_marker(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        passages = [
            {"text": "CBT is evidence-based.", "source_id": "cbt-001", "citation": "Beck (1979)"}
        ]
        block = _build_l4_knowledge_block(passages, abstain=False)
        assert "[1]" in block
        assert "CBT is evidence-based" in block

    def test_formats_multiple_passages_with_sequential_markers(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        passages = [
            {"text": "CBT text.", "source_id": "cbt-001", "citation": "Beck (1979)"},
            {"text": "DBT text.", "source_id": "dbt-002", "citation": "Linehan (1993)"},
            {"text": "MBCT text.", "source_id": "mbct-003", "citation": "Segal (2002)"},
        ]
        block = _build_l4_knowledge_block(passages, abstain=False)
        assert "[1]" in block
        assert "[2]" in block
        assert "[3]" in block

    def test_returns_none_for_empty_passages_and_no_abstain(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        assert _build_l4_knowledge_block([], abstain=False) is None

    def test_abstain_returns_block_with_fabricate_warning(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        block = _build_l4_knowledge_block([], abstain=True)
        assert block is not None
        assert "fabricate" in block.lower()

    def test_includes_not_certain_instruction_when_passages_present(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        passages = [{"text": "Some text.", "source_id": "src-001", "citation": "Author (2020)"}]
        block = _build_l4_knowledge_block(passages, abstain=False)
        assert "not certain" in block

    def test_citation_text_included_in_block(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        passages = [{"text": "EMDR reduces PTSD symptoms.", "source_id": "emdr-001", "citation": "Shapiro (1989)"}]
        block = _build_l4_knowledge_block(passages, abstain=False)
        assert "Shapiro (1989)" in block or "emdr-001" in block

    def test_passage_text_included_verbatim(self):
        from sage_poc.prompts.composer import _build_l4_knowledge_block
        text = "Mindfulness reduces rumination in depressive episodes."
        passages = [{"text": text, "source_id": "mbct-001", "citation": "Segal (2002)"}]
        block = _build_l4_knowledge_block(passages, abstain=False)
        assert "Mindfulness reduces rumination" in block


# ---------------------------------------------------------------------------
# 2. compose_prompt() integration — knowledge passages present
# ---------------------------------------------------------------------------

class TestComposePromptWithKnowledge:

    def test_knowledge_layer_in_layers_list(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            knowledge_passages=[
                {"text": "CBT is evidence-based.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, _, layers = compose_prompt(state)
        assert "knowledge" in layers

    def test_citation_marker_in_user_string(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            knowledge_passages=[
                {"text": "CBT is evidence-based.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, _ = compose_prompt(state)
        assert "[1]" in user_str

    def test_passage_text_in_user_string(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            knowledge_passages=[
                {"text": "CBT is an evidence-based therapy for depression.",
                 "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, _ = compose_prompt(state)
        assert "CBT" in user_str or "evidence-based" in user_str

    def test_knowledge_layer_absent_for_general_chat(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="general_chat",
            knowledge_passages=[],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, _, layers = compose_prompt(state)
        assert "knowledge" not in layers

    def test_knowledge_layer_present_for_info_request_with_empty_passages_and_abstain(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            knowledge_passages=[],
            knowledge_abstain=True,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, layers = compose_prompt(state)
        # L4 must fire for abstain=True to inject the "do not fabricate" instruction
        assert "knowledge" in layers
        text_lower = user_str.lower()
        assert (
            "fabricate" in text_lower
            or "do not invent" in text_lower
            or "no relevant" in text_lower
            or "no evidence" in text_lower
        )

    def test_user_message_appears_last_in_user_str(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            message_en="what is CBT exactly",
            knowledge_passages=[
                {"text": "CBT is evidence-based.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, _ = compose_prompt(state)
        assert user_str.endswith("USER: what is CBT exactly")

    def test_multiple_passages_produce_multiple_citation_markers(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            knowledge_passages=[
                {"text": "CBT text.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.91},
                {"text": "DBT text.", "source_id": "dbt-002", "citation": "Linehan (1993)", "relevance_score": 0.78},
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, _ = compose_prompt(state)
        assert "[1]" in user_str
        assert "[2]" in user_str

    def test_knowledge_block_appears_before_user_message(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            message_en="what is CBT",
            knowledge_passages=[
                {"text": "CBT evidence text.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, _ = compose_prompt(state)
        # [1] citation marker must appear before USER: line
        assert user_str.index("[1]") < user_str.index("USER: what is CBT")


# ---------------------------------------------------------------------------
# 3. compose_prompt() Arabic state — L4 language-agnostic
# ---------------------------------------------------------------------------

class TestComposePromptArabicGrounding:

    def test_knowledge_layer_fires_for_arabic_state(self):
        """L4 grounding fires regardless of detected_language.

        The message content in the prompt uses message_en (translated), so the
        knowledge passages are in English even for Arabic sessions.
        """
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            detected_language="ar",
            message_en="what is cognitive behavioral therapy",
            raw_message="ما هو العلاج المعرفي السلوكي",
            knowledge_passages=[
                {"text": "CBT is evidence-based.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, _, layers = compose_prompt(state)
        assert "knowledge" in layers

    def test_citation_in_user_str_for_arabic_state(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            detected_language="ar",
            message_en="what is CBT",
            raw_message="ما هو CBT",
            knowledge_passages=[
                {"text": "CBT is evidence-based.", "source_id": "cbt-001", "citation": "Beck (1979)", "relevance_score": 0.88}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, user_str, _ = compose_prompt(state)
        assert "[1]" in user_str


# ---------------------------------------------------------------------------
# 4. compose_prompt() — no skill active + knowledge (info_request path)
# ---------------------------------------------------------------------------

class TestComposePromptInfoRequestPath:

    def test_no_l3_skill_wrapper_on_info_request(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state(
            primary_intent="info_request",
            active_skill_id=None,
            step_instruction=None,
            knowledge_passages=[
                {"text": "Anxiety treatment text.", "source_id": "anx-001", "citation": "Barlow (2002)", "relevance_score": 0.82}
            ],
            knowledge_abstain=False,
        )
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, _, layers = compose_prompt(state)
        assert "L3_skill_wrapper" not in layers
        assert "skill_instruction" not in layers

    def test_result_is_three_tuple(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state()
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            result = compose_prompt(state)
        assert len(result) == 3
        system_str, user_str, layers = result
        assert isinstance(system_str, str)
        assert isinstance(user_str, str)
        assert isinstance(layers, list)

    def test_persona_and_intent_always_in_layers(self):
        from sage_poc.prompts.composer import compose_prompt
        state = make_compose_state()
        with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
            _, _, layers = compose_prompt(state)
        assert "persona" in layers
        assert "intent" in layers
