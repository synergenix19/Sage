# tests/test_output_gate_clinical_review.py
"""Tests for deterministic Layer 1 clinical review notification in output_gate_node (Task 4.5)."""
import asyncio
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers — reuse the same make_state pattern from session summary tests
# ---------------------------------------------------------------------------

def make_state(**kwargs):
    """Build a minimal SageState dict for output_gate_node tests."""
    defaults = {
        # routing / gate
        "gate_path": None,
        "path": [],
        # language
        "detected_language": "en",
        # content
        "message_en": "Hello",
        "response_en": "Hi there",
        # safety
        "is_safe": True,
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        # memory / turn tracking
        "conversation_history": [],
        "turn_count": 0,
        "conversation_summary": None,
        # session identity
        "session_id": "sess-123",
        "user_id": "user-456",
        # skill tracking
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        # emotional metrics
        "emotional_intensity": 5,
        "engagement": 5,
        # crisis extras
        "s7_result": None,
        "s7_method": None,
        "third_party_crisis": False,
        "escalation_triggered": None,
    }
    return {**defaults, **kwargs}


# ---------------------------------------------------------------------------
# Integration tests — patch _log_clinical_review at module level
# ---------------------------------------------------------------------------

class TestClinicalReviewInOutputGateNode:
    """Tests that verify _log_clinical_review is fired (or not) correctly
    from output_gate_node.

    We use a non-turn-10 turn_count (default 0 → next_turn=1) so the session
    summary block never interferes.
    """

    def _run_node(self, state):
        """Run output_gate_node inside a fresh event loop so create_task tasks execute."""
        from sage_poc.nodes.output_gate import output_gate_node

        async def _runner():
            result = await output_gate_node(state)
            # Drain any pending tasks created during the node
            await asyncio.gather(*asyncio.all_tasks(asyncio.get_event_loop()) - {asyncio.current_task()})
            return result

        return asyncio.run(_runner())

    def test_clinical_review_fires_when_clinical_flags(self):
        """When clinical_flags are present and crisis_flags empty, _log_clinical_review is called."""
        state = make_state(
            clinical_flags=["substance_use"],
            crisis_flags=[],
            session_id="sid",
            user_id="uid",
        )

        with patch(
            "sage_poc.nodes.output_gate._log_clinical_review",
            new=AsyncMock(),
        ) as mock_log:
            self._run_node(state)

        mock_log.assert_called_once_with(
            "sid",
            "uid",
            [],
            ["substance_use"],
        )

    def test_clinical_review_fires_when_crisis_flags(self):
        """When crisis_flags are present, _log_clinical_review is called."""
        state = make_state(
            crisis_flags=["suicidal_ideation"],
            clinical_flags=[],
            session_id="sid",
            user_id="uid",
        )

        with patch(
            "sage_poc.nodes.output_gate._log_clinical_review",
            new=AsyncMock(),
        ) as mock_log:
            self._run_node(state)

        mock_log.assert_called_once_with(
            "sid",
            "uid",
            ["suicidal_ideation"],
            [],
        )

    def test_clinical_review_not_fired_when_no_flags(self):
        """When both flags are empty, _log_clinical_review must NOT be called."""
        state = make_state(
            clinical_flags=[],
            crisis_flags=[],
            session_id="sid",
            user_id="uid",
        )

        with patch(
            "sage_poc.nodes.output_gate._log_clinical_review",
            new=AsyncMock(),
        ) as mock_log:
            self._run_node(state)

        mock_log.assert_not_called()

    def test_clinical_review_not_fired_when_no_session_id(self):
        """When session_id is None (flags present), _log_clinical_review must NOT be called."""
        state = make_state(
            clinical_flags=["substance_use"],
            crisis_flags=["suicidal_ideation"],
            session_id=None,
            user_id="uid",
        )

        with patch(
            "sage_poc.nodes.output_gate._log_clinical_review",
            new=AsyncMock(),
        ) as mock_log:
            self._run_node(state)

        mock_log.assert_not_called()


# ---------------------------------------------------------------------------
# Unit tests for _log_clinical_review helper directly
# ---------------------------------------------------------------------------

class TestLogClinicalReviewHelper:
    """Unit tests for the _log_clinical_review helper in isolation.

    Because server, PostgresNotifier are deferred imports (inside the function
    body), we patch them via sys.modules injection.
    """

    def _run_helper(self, mock_app, mock_notifier_cls, **kwargs):
        """
        Run _log_clinical_review with fully-mocked deferred imports.

        Patches:
          - sys.modules["server"]                     => module with .app = mock_app
          - sage_poc.memory.notification.PostgresNotifier => mock_notifier_cls
        """
        from sage_poc.nodes.output_gate import _log_clinical_review

        fake_server_module = MagicMock()
        fake_server_module.app = mock_app

        fake_notif_module = MagicMock()
        fake_notif_module.PostgresNotifier = mock_notifier_cls

        modules_patch = {
            "server": fake_server_module,
            "sage_poc.memory.notification": fake_notif_module,
        }

        async def _runner():
            with patch.dict(sys.modules, modules_patch):
                await _log_clinical_review(**kwargs)

        asyncio.run(_runner())

    def _make_mock_app_and_notifier(self):
        """Return (mock_app, mock_notifier_cls, mock_notifier_instance, mock_notify)."""
        mock_pool = MagicMock()
        mock_app = MagicMock()
        mock_app.state._db_pool = mock_pool

        mock_notify = AsyncMock()
        mock_notifier_instance = MagicMock()
        mock_notifier_instance.notify_review_required = mock_notify

        mock_notifier_cls = MagicMock(return_value=mock_notifier_instance)

        return mock_app, mock_notifier_cls, mock_notifier_instance, mock_notify

    def test_severity_high_when_crisis_flags(self):
        """crisis_flags non-empty => severity='high' (DB constraint: low/medium/high)."""
        mock_app, mock_notifier_cls, _, mock_notify = self._make_mock_app_and_notifier()

        self._run_helper(
            mock_app=mock_app,
            mock_notifier_cls=mock_notifier_cls,
            session_id="sid",
            user_id="uid",
            crisis_flags=["si"],
            clinical_flags=[],
        )

        mock_notify.assert_called_once()
        kwargs = mock_notify.call_args.kwargs
        assert kwargs["severity"] == "high"

    def test_severity_medium_when_clinical_only(self):
        """crisis_flags=[], clinical_flags non-empty => severity='medium'."""
        mock_app, mock_notifier_cls, _, mock_notify = self._make_mock_app_and_notifier()

        self._run_helper(
            mock_app=mock_app,
            mock_notifier_cls=mock_notifier_cls,
            session_id="sid",
            user_id="uid",
            crisis_flags=[],
            clinical_flags=["substance_use"],
        )

        mock_notify.assert_called_once()
        kwargs = mock_notify.call_args.kwargs
        assert kwargs["severity"] == "medium"

    def test_source_is_layer1_safety(self):
        """source must always be 'layer1_safety'."""
        mock_app, mock_notifier_cls, _, mock_notify = self._make_mock_app_and_notifier()

        self._run_helper(
            mock_app=mock_app,
            mock_notifier_cls=mock_notifier_cls,
            session_id="sid",
            user_id="uid",
            crisis_flags=["si"],
            clinical_flags=[],
        )

        mock_notify.assert_called_once()
        kwargs = mock_notify.call_args.kwargs
        assert kwargs["source"] == "layer1_safety"

    def test_reason_includes_flag_names(self):
        """reason string must contain both crisis and clinical flag names."""
        mock_app, mock_notifier_cls, _, mock_notify = self._make_mock_app_and_notifier()

        self._run_helper(
            mock_app=mock_app,
            mock_notifier_cls=mock_notifier_cls,
            session_id="sid",
            user_id="uid",
            crisis_flags=["si"],
            clinical_flags=["substance_use"],
        )

        mock_notify.assert_called_once()
        kwargs = mock_notify.call_args.kwargs
        reason = kwargs["reason"]
        assert "si" in reason
        assert "substance_use" in reason

    def test_no_pool_returns_early(self):
        """When pool is None, notifier.notify must NOT be called."""
        mock_app = MagicMock()
        mock_app.state._db_pool = None

        mock_notify = AsyncMock()
        mock_notifier_instance = MagicMock()
        mock_notifier_instance.notify_review_required = mock_notify
        mock_notifier_cls = MagicMock(return_value=mock_notifier_instance)

        self._run_helper(
            mock_app=mock_app,
            mock_notifier_cls=mock_notifier_cls,
            session_id="sid",
            user_id="uid",
            crisis_flags=["si"],
            clinical_flags=[],
        )

        mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# Task 7 — _crisis_response_node writes clinician_review_queue (output_gate bypass)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crisis_response_node_writes_clinician_review_queue():
    """_crisis_response_node must write clinician_review_queue; output_gate is bypassed."""
    import asyncio
    from unittest.mock import patch, AsyncMock, MagicMock
    from sage_poc import graph as sage_graph

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    state = {
        "raw_message": "the voices told me to hurt someone",
        "message_en": "the voices told me to hurt someone",
        "detected_language": "en",
        "crisis_flags": ["command_hallucination"],
        "clinical_flags": [],
        "crisis_state": "none",
        "turn_count": 1,
        "turn_number": 1,
        "user_id": "test-user-uuid",
        "session_id": "test-session-uuid",
        "path": ["safety_check"],
        "conversation_history": [],
        "active_skill_id": None,
        "therapeutic_profile": None,
        "re_escalation_within_monitoring": False,
    }

    with patch.object(sage_graph, "_get_crisis_review_pool", return_value=mock_pool):
        with patch.object(sage_graph, "write_session_audit", new_callable=AsyncMock):
            with patch.object(sage_graph, "AUDIT_LOG_ENABLED", False):
                await sage_graph._crisis_response_node(state)
                await asyncio.sleep(0.05)

    inserts = [c for c in mock_conn.execute.call_args_list if "clinician_review_queue" in str(c)]
    assert len(inserts) >= 1, "Expected INSERT into clinician_review_queue from _crisis_response_node"
