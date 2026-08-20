# tests/test_output_gate_phase_split_audit_matrix.py
"""Task 3 (P2 core-layer, 2026-08-20) -- output_gate three-phase split, audit-row equivalence.

Amendment 3: response-equality alone is insufficient evidence for this refactor. The audit row
IS the compliance artifact (it is what a clinician/DPO auditor actually reads), so this module
pins BOTH (a) the exact state dict passed into write_session_audit -- i.e. _build_session_audit_row's
input -- and (b) output_gate_node's returned dict, per matrix state, and asserts dict-equality
against a matrix RECORDED from the CURRENT (pre-refactor, monolithic) node before any phase
extraction happened. See tests/fixtures/output_gate_phase_split_matrix.json for the recording
and docs on how it was produced.

This is a NEW module -- it does not alter any existing output_gate test file's assertions
(collision-bar compliant). It intentionally duplicates state construction rather than importing
from another test module, so it has no dependency on other files' internals drifting under it.

Non-determinism handling (both when this matrix was RECORDED and on every later run):
  - time.monotonic() is frozen to a constant (output_gate.py's only two consumers --
    opener-rewrite latency and translate-out latency -- both then compute to a fixed 0ms delta).
  - datetime.now(timezone.utc) is frozen to a fixed instant (consumed by the return dict's
    last_turn_at and the AUDIT log-line dict's timestamp).
  - turn_started_at is left unset on every matrix state, so latency_ms is never computed (the
    None-safe branch), removing the one timing field that ISN'T frozen by the time-monotonic patch.
  - turn_count is fixed away from any multiple-of-10 boundary, so summarise_history / session-summary
    persistence never fires (kept out of scope for this matrix; that path is covered elsewhere in
    tests/test_output_gate_session_summary.py, a file this task does not touch).
  - rules_engine.evaluate("cultural_output", ...) is stubbed to fired=[] so this matrix is scoped to
    output_gate's OWN logic (its three phases), not to the content of rules/data JSON, which is
    covered elsewhere.
  - _rewrite_opener and async_translate_to_arabic are stubbed to deterministic values so the matrix
    never depends on a live LLM / translation backend.
  - _log_clinical_review, _persist_session_summary, and write_identity_substitution_audit are
    stubbed to no-ops so the matrix never depends on server.app / a live DB pool; write_session_audit
    is the ONE call captured (that is the compliance artifact under test).

Amendment 4 (fixture-corpus requirement for any task touching output_gate): the matrix spans
Arabic-script (STATE_AR) and Arabizi (STATE_ARABIZI) turns, clinical-flag states that alter
output_gate's own behaviour (crisis_flags/T1 tiering, clinical_flags, medical_flags, the HR §5
terminal's skill_match_method marker), and the eleven states named in the task-3 brief step 1
(crisis, standard, medical, HR, screen, derealization-flagged, AR-language, retry-fallback,
banned-opener-rewrite, SG-2 caveat, psychoed-serve), for 12 states total. Per-class counts and the
row+return equality claim are restated in the PR body.
"""
import asyncio
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.safety_gate

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "output_gate_phase_split_matrix.json"

_FROZEN_NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return _FROZEN_NOW if tz is not None else _FROZEN_NOW.replace(tzinfo=None)


class _FrozenTime:
    """Replaces the `time` module reference inside output_gate.py. output_gate.py calls only
    time.monotonic() (grep-verified at task-3 authorship); a constant makes every elapsed-time
    computation there deterministically 0."""

    @staticmethod
    def monotonic():
        return 1000.0


# ---------------------------------------------------------------------------
# Shared state construction
# ---------------------------------------------------------------------------

def _base_state(**overrides):
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "The exhaustion you're describing sounds real. What's been hardest?",
        "gate_path": None,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "completed_skill_id": None,
        "executed_step_id": None,
        "active_step_id": None,
        "step_instruction": None,
        "step_mandatory_caveat": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_flags": [],
        "crisis_state": "none",
        "crisis_tier": None,
        "t1_count": None,
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "s7_method": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "knowledge_query_raw": "",
        "knowledge_query_searched": "",
        "knowledge_top_similarity": None,
        "stale_skill_id": None,
        "cultural_output_violations": [],
        "path": ["safety_check", "intent_route", "freeflow_respond"],
        "turn_count": 3,
        "turn_number": 3,
        "session_id": "sess-matrix",
        "user_id": "user-matrix",
        "identity_substitution_rule_id": None,
        "original_response_hash": None,
        "original_response_text": None,
        "prompt_layers": ["persona", "intent"],
        "token_usage": {},
        "resistance_score": None,
        "resistance_history": [],
        "semantic_score": None,
        "skill_match_method": None,
        "new_clinical_flags_turn": [],
        "prev_step_id": None,
        "re_escalation_within_monitoring": None,
        "engagement_trajectory": [],
        "distress_trajectory": [],
        "last_turn_at": None,
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
        "is_safe": True,
        "medical_flags": [],
        "offered_skill_ids": None,
        "abstain_referral": None,
        "psychoed_serve": None,
        "psychoed_matched_row_id": None,
        "psychoed_collision_path": None,
        "psychoed_framing": None,
        "psychoed_weave_pending": None,
        "psychoed_weave_fired": None,
        "psychoed_active_category": None,
        "derealization_referral_delivered": None,
        "directive_posture": False,
        "turn_started_at": None,
    }
    return {**base, **overrides}


def _psychoed_serve_payload():
    from sage_poc.psychoed import serve, store
    block_id = "6d-b1"
    category = "6d"
    payload = {
        "category": category, "block_id": block_id, "route": "standard", "framing": "abstract",
        "weave_due": False, "matched_row_id": "row-42", "collision_path": "clean",
    }
    composed = serve.compose_turn1(payload)
    return payload, composed


def _build_matrix() -> "dict[str, dict]":
    """Returns {name: state} for the 12 matrix states. `psychoed-serve` is built lazily (needs
    sage_poc.psychoed imports) inside the caller so import-time flag state doesn't matter here."""
    states = {
        "crisis": _base_state(
            crisis_flags=["s3_semantic"],
            crisis_tier="T1",
            t1_count=2,
            response_en="Thanks for telling me. What's one small thing that might help right now?",
        ),
        "standard": _base_state(),
        "medical": _base_state(
            clinical_flags=["physical_symptom_disclosure"],
            medical_flags=["MED-003"],
            response_en="Thanks for sharing that. How long has this been going on?",
        ),
        "hr": _base_state(
            skill_match_method="psychotic_disclosure_auto_select",
            clinical_flags=["psychotic_disclosure"],
            response_en=(
                "It sounds like you're experiencing something very distressing with people "
                "following and watching you. This is important to talk through with a mental "
                "health professional. 800-HOPE (800-4673) or emergency services 999."
            ),
        ),
        "screen": _base_state(
            step_instruction={"prompt": "score_mood check-in"},
            executed_step_id="score_mood",
            response_en=(
                "How are you feeling on a scale of one to ten? "
                "Have you had any thoughts of harming yourself?"
            ),
        ),
        "derealization_flagged": _base_state(
            clinical_flags=["derealization"],
            derealization_referral_delivered=True,
            response_en="Thanks for telling me that. What's been going on today?",
        ),
        "ar_language": _base_state(
            detected_language="ar",
            raw_message="أشعر أن كل شيء غريب وغير حقيقي",
            message_en="I feel like everything is strange and unreal",
            response_en="I'm here with you. What's been happening?",
        ),
        "arabizi": _base_state(
            detected_language="az",
            raw_message="ana ta3ban w7ase kolshi s3b",
            message_en="I'm tired and I feel like everything is hard",
            response_en="Thanks for telling me. What's been hardest today?",
        ),
        "retry_fallback": _base_state(
            response_en="",
            banned_opener_retry_count=1,
            offered_skill_ids=["box_breathing"],
            path=["safety_check", "intent_route", "skill_select", "skill_offer_made", "freeflow_respond"],
        ),
        "banned_opener_rewrite": _base_state(
            response_en="It sounds like you're really overwhelmed right now.",
        ),
        "sg2_caveat": _base_state(
            step_mandatory_caveat="This technique isn't recommended if you're currently experiencing a panic attack.",
            active_skill_id="progressive_muscle_relaxation",
            executed_step_id="pmr_intro",
            response_en="Let's begin the muscle relaxation exercise.",
        ),
    }
    payload, composed = _psychoed_serve_payload()
    states["psychoed_serve"] = _base_state(
        path=["safety_check", "intent_route", "skill_select", "knowledge_retrieve", "freeflow_respond"],
        message_en="why do people get anxious",
        raw_message="why do people get anxious",
        response_en=composed["text"],
        skill_match_method="psychoed_resolver",
        psychoed_serve=payload,
        psychoed_matched_row_id="row-42",
        psychoed_collision_path="clean",
        psychoed_framing="abstract",
        psychoed_weave_pending=False,
        psychoed_weave_fired=False,
    )
    return states


# States that need a config flag flipped on for their branch to be reachable (flag name -> value).
_STATE_CONFIG_OVERRIDES = {
    "hr": {"HR_NEUTRALITY_GATE_ENABLED": True},
    "psychoed_serve": {"PSYCHOED_PATHWAYS_ENABLED": True},
}

MATRIX_STATE_NAMES = [
    "crisis", "standard", "medical", "hr", "screen", "derealization_flagged",
    "ar_language", "arabizi", "retry_fallback", "banned_opener_rewrite", "sg2_caveat",
    "psychoed_serve",
]


async def _run_state(monkeypatch, name, state):
    import sage_poc.config as config
    import sage_poc.nodes.output_gate as og

    # Deterministic config flags: explicit for every state (never ambient-env-dependent).
    monkeypatch.setattr(config, "HR_NEUTRALITY_GATE_ENABLED", False)
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", False)
    for flag, value in _STATE_CONFIG_OVERRIDES.get(name, {}).items():
        monkeypatch.setattr(config, flag, value)

    monkeypatch.setattr(og, "datetime", _FrozenDatetime)
    monkeypatch.setattr(og, "time", _FrozenTime)

    write_calls = []

    async def _capture_audit(s):
        write_calls.append(copy.deepcopy(s))

    async def _fake_rewrite(response_en, opener, user_message_en):
        return "You're carrying a great deal right now, and that makes sense."

    async def _fake_translate(text, *, strict=False, gender="none"):
        return "رد تجريبي محايد للاختبار"

    _real_evaluate = og.rules_engine.evaluate

    def _stub_evaluate(schema, ctx):
        if schema == "cultural_output":
            return MagicMock(fired=[])
        return _real_evaluate(schema, ctx)

    with (
        patch.object(og, "write_session_audit", new=_capture_audit),
        patch.object(og, "_log_clinical_review", new=AsyncMock()),
        patch.object(og, "_persist_session_summary", new=AsyncMock()),
        patch.object(og, "write_identity_substitution_audit", new=AsyncMock()),
        patch.object(og, "_rewrite_opener", new=_fake_rewrite),
        patch.object(og, "async_translate_to_arabic", new=_fake_translate),
        patch.object(og.rules_engine, "evaluate", side_effect=_stub_evaluate),
    ):
        result = await og.output_gate_node(copy.deepcopy(state))
        await asyncio.sleep(0)  # let the fire-and-forget write_session_audit task run

    assert write_calls, f"{name}: output_gate_node must call write_session_audit"
    return write_calls[-1], result


def _to_jsonable(value):
    """Deep-convert a captured dict to a JSON-round-trippable structure for storage/comparison.
    Tuples become lists (matching JSON's own list-only sequence type) so a recorded-and-reloaded
    fixture compares equal to a freshly captured dict without a tuple/list false mismatch."""
    return json.loads(json.dumps(value, default=str))


# ---------------------------------------------------------------------------
# The equivalence test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name", MATRIX_STATE_NAMES)
async def test_audit_row_and_return_dict_match_recorded_matrix(name, monkeypatch):
    """Per Amendment 3: response-equality alone is insufficient. This asserts dict-equality on
    BOTH the exact state dict passed to write_session_audit (i.e. _build_session_audit_row's
    input) AND output_gate_node's returned dict, against the matrix recorded from the current
    (pre-refactor) node."""
    recorded = json.loads(_FIXTURE_PATH.read_text())
    assert name in recorded, f"{name}: no recorded matrix entry -- fixture is stale"

    states = _build_matrix()
    audit_input, returned = await _run_state(monkeypatch, name, states[name])

    audit_input_j = _to_jsonable(audit_input)
    returned_j = _to_jsonable(returned)

    assert audit_input_j == recorded[name]["audit_input"], (
        f"{name}: audit-row INPUT diverged from the recorded pre-refactor matrix "
        f"(Amendment 3 -- this is the compliance artifact)"
    )
    assert returned_j == recorded[name]["returned"], (
        f"{name}: output_gate_node's returned dict diverged from the recorded pre-refactor matrix"
    )


def test_matrix_covers_all_named_states():
    """Guards the matrix itself from silently shrinking."""
    states = _build_matrix()
    assert set(states) == set(MATRIX_STATE_NAMES)
    assert len(MATRIX_STATE_NAMES) == 12
