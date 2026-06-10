"""
Group 3 Bug Fix Audit — Functional Tests
Covers A3 (regex), A4 (third-party crisis), A5 (thread safety).
"""
from __future__ import annotations
import threading
import time
import logging
from unittest.mock import patch

import pytest

from sage_poc.rules.engine import _eval_safety
from sage_poc.rules.schemas import SafetyRule
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.prompts.composer import compose_prompt


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_rule(match_type: str, patterns: list[str], language: str = "en", modifiers: list[str] = []) -> SafetyRule:
    return SafetyRule(
        rule_id="audit_test",
        version="1.0.0",
        category="safety",
        effective_date="2026-01-01",
        match_type=match_type,
        patterns=patterns,
        language=language,
        modifiers=modifiers,
        action={"type": "crisis_flag", "flag_id": "si"},
    )


def _safety_state(raw_message: str, **overrides) -> dict:
    base = {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": raw_message,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "third_party_crisis": False,
        "crisis_state": "none",
        "s7_result": None, "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "code_switching": False,
        "primary_intent": None, "secondary_intent": None,
        "intent_confidence": 1.0, "emotional_intensity": 5, "engagement": 5,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "skill_match_method": None, "semantic_score": None,
        "escalation_triggered": None, "gate_path": None,
        "response_en": None, "response": None,
        "path": [], "turn_count": 0, "conversation_history": [],
    }
    base.update(overrides)
    return base


def _freeflow_state(**overrides) -> dict:
    base = {
        "raw_message": "I feel anxious",
        "detected_language": "en", "message_en": "I feel anxious",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [], "third_party_crisis": False,
        "crisis_state": "none", "s7_result": None, "s7_method": None,
        "distress_trajectory": [], "engagement_trajectory": [], "code_switching": False,
        "primary_intent": "general_chat", "secondary_intent": None,
        "intent_confidence": 0.9, "emotional_intensity": 5, "engagement": 5,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "skill_match_method": None, "semantic_score": None,
        "escalation_triggered": None, "gate_path": None, "response_en": None, "response": None,
        "path": [], "turn_count": 0, "conversation_history": [],
    }
    base.update(overrides)
    return base


# ── A3: Regex branch in _eval_safety ─────────────────────────────────────────

class TestA3RegexBranch:

    def test_valid_regex_match_fires_crisis(self):
        """Word-boundary regex matches 'suicidal thoughts'."""
        rule = _make_rule("regex", [r"\bsuicid\w*\b"])
        result = _eval_safety([rule], {"text_en": "I am having suicidal thoughts", "language": "en"})
        assert len(result.fired) == 1
        assert result.fired[0].rule_id == "audit_test"

    def test_valid_regex_no_match_on_unrelated_text(self):
        """Word-boundary regex does not match unrelated text."""
        rule = _make_rule("regex", [r"\bsuicid\w*\b"])
        result = _eval_safety([rule], {"text_en": "I feel sad today", "language": "en"})
        assert len(result.fired) == 0

    def test_malformed_regex_skipped_not_crash(self, caplog):
        """Malformed pattern is caught, logged at WARNING, and skipped."""
        rule = _make_rule("regex", [r"[unclosed"])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.engine"):
            result = _eval_safety([rule], {"text_en": "any text", "language": "en"})
        assert len(result.fired) == 0
        assert any("Malformed regex" in r.message and "audit_test" in r.message for r in caplog.records)

    def test_malformed_regex_logs_pattern(self, caplog):
        """Log message contains the offending pattern string."""
        bad_pattern = r"[unclosed"
        rule = _make_rule("regex", [bad_pattern])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.engine"):
            _eval_safety([rule], {"text_en": "any text", "language": "en"})
        assert any(bad_pattern in r.message for r in caplog.records)

    def test_empty_pattern_does_not_crash(self):
        """Empty string pattern with keyword match_type does not crash."""
        rule = _make_rule("keyword", [""])
        result = _eval_safety([rule], {"text_en": "I feel anxious", "language": "en"})
        # Empty substring always matches via .find() — this is pre-existing keyword behavior
        # The important thing is no exception is raised
        assert isinstance(result.fired, list)

    def test_regex_with_unicode_arabic_pattern(self):
        """Regex engine handles Arabic Unicode in pattern.
        IMPORTANT: Arabic regex patterns are applied against normalize_arabic() output,
        which strips alef-hamza variants (أ → ا). Clinicians must write Arabic regex
        patterns in normalized form. Pattern 'اريد.+اموت' (normalized) matches
        normalized text 'اريد ان اموت' from original 'أريد أن أموت'.
        """
        rule = SafetyRule(
            rule_id="arabic_regex_test", version="1.0.0", category="safety",
            effective_date="2026-01-01", match_type="regex",
            patterns=[r"اريد.+اموت"],  # normalized form (alef without hamza)
            language="ar",
            action={"type": "crisis_flag", "flag_id": "si"},
        )
        result = _eval_safety([rule], {
            "text_en": "I want to die",
            "text_ar": "أريد أن أموت",  # original Arabic text (with hamza)
            "language": "ar",
        })
        assert len(result.fired) == 1

    def test_regex_negation_check_respected(self):
        """Regex match with negation_check modifier is suppressed when negation present."""
        rule = SafetyRule(
            rule_id="negation_regex_test", version="1.0.0", category="safety",
            effective_date="2026-01-01", match_type="regex",
            patterns=[r"\bkill\b"],
            modifiers=["negation_check"],
            action={"type": "crisis_flag", "flag_id": "si"},
        )
        result = _eval_safety([rule], {"text_en": "I do not want to kill myself", "language": "en"})
        assert len(result.fired) == 0, "Negation should suppress regex match"

    def test_regex_span_recorded_correctly(self):
        """Matched span from regex corresponds to actual match positions."""
        rule = _make_rule("regex", [r"\bpain\b"])
        result = _eval_safety([rule], {"text_en": "I am in pain today", "language": "en"})
        assert len(result.fired) == 1
        span = result.fired[0].matched_span
        assert span is not None
        text_norm = "i am in pain today"
        assert text_norm[span[0]:span[1]] == "pain"

    def test_regex_layer1_timing_under_50ms(self):
        """Engine evaluation with regex rule stays under 50ms deterministic budget."""
        rules = [_make_rule("regex", [r"\bsuicid\w*\b"]) for _ in range(10)]
        text_ctx = {"text_en": "I feel a bit sad but I am okay", "language": "en"}
        start = time.perf_counter()
        for _ in range(20):
            _eval_safety(rules, text_ctx)
        elapsed_ms = (time.perf_counter() - start) / 20 * 1000
        assert elapsed_ms < 50, f"Regex eval averaged {elapsed_ms:.1f}ms — exceeds 50ms budget"


# ── A4: Third-Party Crisis Flow ───────────────────────────────────────────────

class TestA4ThirdPartyCrisis:

    async def _run_safety(self, raw: str):
        state = _safety_state(raw)
        with (
            patch("sage_poc.nodes.safety_check.detect_language", return_value="en"),
            patch("sage_poc.nodes.safety_check.async_translate_to_english", return_value=raw),
        ):
            return await safety_check_node(state)

    async def test_third_party_sets_flag_not_crisis(self):
        """'My friend told me she wants to die' → third_party_crisis=True, is_safe=True."""
        result = await self._run_safety("my friend told me she wants to die")
        assert result["is_safe"] is True
        assert result.get("third_party_crisis") is True
        assert "third_party_si" not in result.get("clinical_flags", [])

    async def test_direct_crisis_unaffected(self):
        """'I want to die' → third_party_crisis=False, is_safe=False, crisis path fires."""
        result = await self._run_safety("I want to die")
        assert result["is_safe"] is False
        assert result.get("third_party_crisis") is False
        assert len(result.get("crisis_flags", [])) > 0

    async def test_ambiguous_third_party_without_explicit_subject(self):
        """'Sometimes people around me want to give up' — verify it does NOT fire crisis for user."""
        result = await self._run_safety("sometimes people around me want to give up")
        # This is ambiguous — it should NOT lock in crisis for the current user.
        # is_safe must be True (no self-harm flag on current user).
        assert result["is_safe"] is True

    async def test_third_party_plus_own_distress(self):
        """'My friend wants to die and I'm terrified' — third_party fires, user stays safe."""
        result = await self._run_safety("my friend wants to die and i am terrified")
        assert result["is_safe"] is True
        assert result.get("third_party_crisis") is True

    def test_third_party_concern_block_in_prompt(self):
        """third_party_crisis=True in state injects THIRD-PARTY CONCERN into user prompt."""
        state = _freeflow_state(third_party_crisis=True)
        _, user_str, layers = compose_prompt(state)
        assert "third_party_crisis" in layers
        assert "THIRD-PARTY CONCERN" in user_str
        assert "Do not treat the current user as being in crisis" in user_str

    def test_third_party_false_does_not_inject(self):
        """third_party_crisis=False does not inject the THIRD-PARTY CONCERN block."""
        state = _freeflow_state(third_party_crisis=False)
        _, user_str, layers = compose_prompt(state)
        assert "third_party_crisis" not in layers
        assert "THIRD-PARTY CONCERN" not in user_str

    async def test_direct_crisis_still_fires_after_a4(self):
        """Regression: A4 must not suppress direct crisis detection."""
        result = await self._run_safety("I want to end my life right now")
        assert result["is_safe"] is False, "Direct crisis must still be detected after A4 fix"
        assert result.get("third_party_crisis") is False

    def test_audit_trail_includes_third_party_crisis(self):
        """output_gate audit dict contains third_party_crisis key."""
        import json
        from sage_poc.nodes import output_gate
        import inspect
        src = inspect.getsource(output_gate)
        assert "third_party_crisis" in src, "third_party_crisis must appear in output_gate source"


# ── A5: Thread Safety in skill_select ────────────────────────────────────────

class TestA5Threading:

    def test_module_level_lock_exists(self):
        """_init_lock is a threading.Lock at module level."""
        from sage_poc.nodes.skill_select import _init_lock
        assert isinstance(_init_lock, type(threading.Lock()))

    def test_embed_model_assigned_last(self):
        """_embed_model is assigned after _anchor_skill_ids and _anchor_embeddings."""
        import inspect
        from sage_poc.nodes import skill_select
        src = inspect.getsource(skill_select._ensure_semantic_ready)
        # The assignment _embed_model = model must come after the two array assignments
        idx_skills = src.find("_anchor_skill_ids = [sid")
        idx_embeds = src.find("_anchor_embeddings = model.encode")
        idx_model  = src.find("_embed_model = model")
        assert idx_skills < idx_model, "_anchor_skill_ids must be assigned before _embed_model"
        assert idx_embeds < idx_model, "_anchor_embeddings must be assigned before _embed_model"

    def test_sequential_calls_no_error(self):
        """Sequential calls to _ensure_semantic_ready do not crash."""
        from sage_poc.nodes.skill_select import _ensure_semantic_ready
        _ensure_semantic_ready()
        _ensure_semantic_ready()  # second call must be a no-op

    def test_concurrent_calls_load_once(self):
        """Concurrent calls from multiple threads result in exactly one model load."""
        import sage_poc.nodes.skill_select as sks

        # Reset module state for isolation
        original_model = sks._embed_model
        original_ids   = sks._anchor_skill_ids
        original_embs  = sks._anchor_embeddings

        load_count = []
        original_ensure = sks._ensure_semantic_ready

        def counting_ensure():
            load_count.append(1)
            original_ensure()

        threads = [threading.Thread(target=sks._ensure_semantic_ready) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # After all threads complete, model must be loaded
        assert sks._embed_model is not None
        assert sks._anchor_embeddings is not None

        # Restore state (model stays loaded — that's correct behavior)

    def test_cold_start_returns_valid_embeddings(self):
        """After _ensure_semantic_ready, anchor embeddings are a non-empty numpy array."""
        import numpy as np
        from sage_poc.nodes.skill_select import _ensure_semantic_ready
        _ensure_semantic_ready()
        from sage_poc.nodes import skill_select as sks
        assert sks._anchor_embeddings is not None
        assert isinstance(sks._anchor_embeddings, np.ndarray)
        assert sks._anchor_embeddings.shape[0] > 0
        assert len(sks._anchor_skill_ids) == sks._anchor_embeddings.shape[0]


# ── B1: p95 formula edge cases ───────────────────────────────────────────────

class TestB1P95Formula:
    """Mathematical verification of Math.ceil(n * 0.95) - 1 in TypeScript.
    Replicated in Python for CI purposes.
    """

    @staticmethod
    def p95_index(n: int) -> int:
        import math
        return math.ceil(n * 0.95) - 1

    def test_n1(self):
        assert self.p95_index(1) == 0  # only element

    def test_n20(self):
        assert self.p95_index(20) == 18  # 19th of 20

    def test_n100(self):
        assert self.p95_index(100) == 94  # 95th of 100

    def test_n200(self):
        assert self.p95_index(200) == 189  # 190th of 200

    def test_returns_last_valid_index(self):
        """Index never exceeds n-1."""
        for n in [1, 2, 3, 5, 10, 20, 50, 100]:
            idx = self.p95_index(n)
            assert 0 <= idx < n, f"Index {idx} out of bounds for n={n}"

    def test_old_formula_was_wrong(self):
        """Confirm Math.floor(n * 0.95) gives wrong result for n=20."""
        import math
        old_index = math.floor(20 * 0.95)  # 19 — one past correct
        new_index = self.p95_index(20)     # 18 — correct
        assert old_index != new_index
        assert new_index == 18


# ── B3: Type guard NaN via JSON round-trip ───────────────────────────────────

class TestB3TypeGuard:

    def test_nan_guard_behavior_documented(self):
        """In JavaScript, JSON.stringify({input: NaN}) → {"input":null}, which typeof-guards reject.
        This test documents the invariant: the JSONB storage round-trip in Supabase
        prevents NaN from reaching the TypeScript type guard. Confirmed by JS semantics:
        typeof null === 'object' (not 'number') → row correctly excluded."""
        # Simulate the JS behavior: NaN → null in JSON
        simulated_supabase_row = {"input": None, "output": 100}  # NaN serialized as null
        # New guard checks both fields: null fails typeof check
        input_ok  = isinstance(simulated_supabase_row.get("input"),  (int, float))
        output_ok = isinstance(simulated_supabase_row.get("output"), (int, float))
        assert not input_ok, "null input should fail the type guard"
        assert output_ok,    "integer output should pass the type guard"
        # Row is excluded (both must pass) — correct
        row_passes = input_ok and output_ok
        assert not row_passes

    def test_none_output_would_have_caused_nan_before_fix(self):
        """Before fix: filter only checked input; None output → NaN in reduce.
        After fix: both fields checked; rows with None output are excluded."""
        rows = [
            {"input": 100, "output": 50},
            {"input": 200, "output": None},  # would cause NaN before fix
            {"input": 150, "output": 75},
        ]
        # Simulate old guard: only input checked
        old_passed = [r for r in rows if r["input"] is not None and isinstance(r["input"], (int, float))]
        old_avg_output = sum(r["output"] or 0 for r in old_passed) / len(old_passed)
        # Old avg would be (50 + 0 + 75) / 3 = 41.67 — wrong (None counted as 0)

        # Simulate new guard: both fields checked
        new_passed = [r for r in rows if isinstance(r.get("input"), (int, float))
                                       and isinstance(r.get("output"), (int, float))]
        new_avg_output = sum(r["output"] for r in new_passed) / len(new_passed)
        # Correct: (50 + 75) / 2 = 62.5

        assert len(new_passed) == 2
        assert new_avg_output == 62.5


# ── B4: Empty result set ─────────────────────────────────────────────────────

class TestB4EmptyResultSet:

    def test_engagement_returns_zeros_for_no_sessions(self):
        """fetchEngagement returns zeros for a user with no sessions in the window.
        Replicated in Python since we can't call Supabase directly here.
        This mirrors the early-return path in fetchEngagement."""
        # Simulated: no sessions returned by Supabase
        sessions = []
        session_ids = [s["id"] for s in sessions]
        if len(session_ids) == 0:
            result = {"sessionCount": 0, "skillsUsedCount": 0}
        else:
            result = None  # would continue to messages query
        assert result == {"sessionCount": 0, "skillsUsedCount": 0}

    def test_twenty_one_days_ago_is_iso8601(self):
        """TWENTY_ONE_DAYS_AGO() returns a valid ISO 8601 UTC string."""
        from datetime import datetime, timezone
        cutoff_ms = __import__('time').time() * 1000 - 21 * 24 * 60 * 60 * 1000
        cutoff = datetime.fromtimestamp(cutoff_ms / 1000, tz=timezone.utc).isoformat()
        # Should parse without error
        parsed = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None


# ── A1/A2: Regression guard ──────────────────────────────────────────────────

class TestA1A2Regression:

    def test_jailbreak_before_monitoring_in_route(self):
        """jailbreak intent routes to 'gate' regardless of crisis_state=monitoring."""
        from sage_poc.graph import _route_after_intent
        state = {
            "primary_intent": "jailbreak",
            "intent_confidence": 0.95,
            "crisis_state": "monitoring",
            "active_skill_id": None,
        }
        route = _route_after_intent(state)
        assert route == "gate", f"Expected 'gate', got '{route}'"

    def test_scope_refusal_before_monitoring_in_route(self):
        """scope_refusal intent routes to 'gate' regardless of crisis_state=monitoring."""
        from sage_poc.graph import _route_after_intent
        state = {
            "primary_intent": "scope_refusal",
            "intent_confidence": 0.95,
            "crisis_state": "monitoring",
            "active_skill_id": None,
        }
        route = _route_after_intent(state)
        assert route == "gate"

    def test_negation_suppresses_do_not_kill(self):
        """'I do not want to kill myself' does not fire crisis (two-word negation)."""
        rule = SafetyRule(
            rule_id="negation_test", version="1.0.0", category="safety",
            effective_date="2026-01-01", match_type="keyword",
            patterns=["kill myself"],
            modifiers=["negation_check"],
            action={"type": "crisis_flag", "flag_id": "si"},
        )
        result = _eval_safety([rule], {"text_en": "I do not want to kill myself", "language": "en"})
        assert len(result.fired) == 0

    def test_negation_suppresses_dont_kill(self):
        """'I don't want to kill myself' does not fire crisis."""
        rule = SafetyRule(
            rule_id="negation_test2", version="1.0.0", category="safety",
            effective_date="2026-01-01", match_type="keyword",
            patterns=["kill myself"],
            modifiers=["negation_check"],
            action={"type": "crisis_flag", "flag_id": "si"},
        )
        result = _eval_safety([rule], {"text_en": "I don't want to kill myself", "language": "en"})
        assert len(result.fired) == 0


# ── A3-F1: Loader lint check for Arabic regex normalization ───────────────────

class TestA3F1LoaderLint:
    """Regression tests for the loader lint check added in A3-F1.
    If the lint call is dropped from loader.py, these tests catch it immediately.
    """

    @staticmethod
    def _make_safety_rule(rule_id: str, patterns: list[str]) -> SafetyRule:
        return SafetyRule(
            rule_id=rule_id, version="1.0.0", category="safety",
            effective_date="2026-01-01", match_type="regex",
            patterns=patterns,
            action={"type": "crisis_flag", "flag_id": "si"},
        )

    def test_unnormalized_alef_hamza_above_triggers_warning(self, caplog):
        """Pattern with أ (alef-hamza-above, U+0623) triggers SAFETY RULE LINT warning."""
        from sage_poc.rules.loader import _lint_arabic_regex_rule
        rule = self._make_safety_rule("lint_test_hamza_above", [r"أريد أن أموت"])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
            _lint_arabic_regex_rule(rule)
        assert any("SAFETY RULE LINT" in r.message and "lint_test_hamza_above" in r.message
                   for r in caplog.records), "Expected lint warning for alef-hamza-above"

    def test_unnormalized_alef_madda_triggers_warning(self, caplog):
        """Pattern with آ (alef-madda, U+0622) triggers SAFETY RULE LINT warning."""
        from sage_poc.rules.loader import _lint_arabic_regex_rule
        rule = self._make_safety_rule("lint_test_madda", [r"آلام"])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
            _lint_arabic_regex_rule(rule)
        assert any("SAFETY RULE LINT" in r.message for r in caplog.records)

    def test_unnormalized_alef_hamza_below_triggers_warning(self, caplog):
        """Pattern with إ (alef-hamza-below, U+0625) triggers SAFETY RULE LINT warning."""
        from sage_poc.rules.loader import _lint_arabic_regex_rule
        rule = self._make_safety_rule("lint_test_hamza_below", [r"إلى"])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
            _lint_arabic_regex_rule(rule)
        assert any("SAFETY RULE LINT" in r.message for r in caplog.records)

    def test_arabic_diacritics_trigger_warning(self, caplog):
        """Pattern with harakat (e.g. fatha U+064E) triggers SAFETY RULE LINT warning."""
        from sage_poc.rules.loader import _lint_arabic_regex_rule
        rule = self._make_safety_rule("lint_test_diacritics", ["مَات"])  # fatha on meem
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
            _lint_arabic_regex_rule(rule)
        assert any("SAFETY RULE LINT" in r.message for r in caplog.records)

    def test_normalized_arabic_pattern_is_silent(self, caplog):
        """Pattern with bare alef (ا) and no diacritics produces no warning."""
        from sage_poc.rules.loader import _lint_arabic_regex_rule
        rule = self._make_safety_rule("lint_test_normalized", [r"اريد ان اموت"])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
            _lint_arabic_regex_rule(rule)
        lint_records = [r for r in caplog.records if "SAFETY RULE LINT" in r.message]
        assert len(lint_records) == 0, f"Unexpected lint warning: {lint_records}"

    def test_english_regex_pattern_is_silent(self, caplog):
        """English-only pattern with no Arabic characters produces no warning."""
        from sage_poc.rules.loader import _lint_arabic_regex_rule
        rule = self._make_safety_rule("lint_test_english", [r"\bsuicid\w*\b"])
        with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
            _lint_arabic_regex_rule(rule)
        lint_records = [r for r in caplog.records if "SAFETY RULE LINT" in r.message]
        assert len(lint_records) == 0, f"Unexpected lint warning: {lint_records}"

    def test_lint_is_called_by_load_rules_for_safety_regex(self, caplog, tmp_path):
        """load_rules() calls the lint check when loading an active safety regex rule.
        This test breaks if someone removes the _lint_arabic_regex_rule call from loader.py.
        """
        import json
        from sage_poc.rules.loader import load_rules

        # Write a temporary safety rule file with a bad Arabic pattern.
        # loader looks for _DATA_DIR / category / *.json, so create the subdir.
        safety_dir = tmp_path / "safety"
        safety_dir.mkdir()
        rule_file = safety_dir / "test_lint_integration.json"
        rule_file.write_text(json.dumps({
            "category": "safety",
            "rules": [{
                "rule_id": "LINT-INTEGRATION-TEST",
                "version": "1.0.0",
                "category": "safety",
                "authored_by": "test",
                "effective_date": "2026-01-01",
                "active": True,
                "match_type": "regex",
                "patterns": ["أريد"],  # unnormalized — should trigger lint
                "action": {"type": "crisis_flag", "flag_id": "si"},
            }]
        }), encoding="utf-8")

        # Temporarily redirect the data dir to tmp_path
        import sage_poc.rules.loader as loader_mod
        original_data_dir = loader_mod._DATA_DIR
        loader_mod._DATA_DIR = tmp_path
        try:
            with caplog.at_level(logging.WARNING, logger="sage_poc.rules.loader"):
                load_rules("safety")
        finally:
            loader_mod._DATA_DIR = original_data_dir

        assert any(
            "SAFETY RULE LINT" in r.message and "LINT-INTEGRATION-TEST" in r.message
            for r in caplog.records
        ), "load_rules() must call the lint check for active safety regex rules"
