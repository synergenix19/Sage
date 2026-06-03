# tests/test_output_gate_session_summary.py
"""Tests for session summary persistence in output_gate_node (Task 3.5)."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
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
# Tests for output_gate_node integration
# ---------------------------------------------------------------------------

class TestSummaryPersistenceInOutputGateNode:
    """Tests that verify _persist_session_summary is fired (or not) correctly."""

    def _run_node(self, state):
        """Run output_gate_node inside a fresh event loop so create_task tasks execute."""
        from sage_poc.nodes.output_gate import output_gate_node

        async def _runner():
            result = await output_gate_node(state)
            # Drain any pending tasks created during the node
            await asyncio.gather(*asyncio.all_tasks(asyncio.get_event_loop()) - {asyncio.current_task()})
            return result

        return asyncio.run(_runner())

    def test_summary_persisted_on_turn_10(self):
        """When turn_count=9, next_turn=10, summary is persisted."""
        state = make_state(turn_count=9, session_id="sess-abc", user_id="user-xyz")

        with (
            patch(
                "sage_poc.nodes.output_gate.summarise_history",
                new=AsyncMock(return_value="Summary text"),
            ),
            patch(
                "sage_poc.nodes.output_gate._persist_session_summary",
                new=AsyncMock(),
            ) as mock_persist,
        ):
            self._run_node(state)

        mock_persist.assert_called_once_with(
            "sess-abc",
            "user-xyz",
            "Summary text",
            [],
            [],
            skills_used=[],
            mood_score=5.0,
        )

    def test_summary_not_persisted_when_session_id_missing(self):
        """When session_id is None, _persist_session_summary must NOT be called."""
        state = make_state(turn_count=9, session_id=None, user_id="user-xyz")

        with (
            patch(
                "sage_poc.nodes.output_gate.summarise_history",
                new=AsyncMock(return_value="Summary text"),
            ),
            patch(
                "sage_poc.nodes.output_gate._persist_session_summary",
                new=AsyncMock(),
            ) as mock_persist,
        ):
            self._run_node(state)

        mock_persist.assert_not_called()

    def test_summary_not_persisted_when_user_id_missing(self):
        """When user_id is None, _persist_session_summary must NOT be called."""
        state = make_state(turn_count=9, session_id="sess-abc", user_id=None)

        with (
            patch(
                "sage_poc.nodes.output_gate.summarise_history",
                new=AsyncMock(return_value="Summary text"),
            ),
            patch(
                "sage_poc.nodes.output_gate._persist_session_summary",
                new=AsyncMock(),
            ) as mock_persist,
        ):
            self._run_node(state)

        mock_persist.assert_not_called()

    def test_summary_not_persisted_on_non_multiple_of_10(self):
        """At turn_count=4 (next_turn=5), the summary block is skipped entirely."""
        state = make_state(turn_count=4, session_id="sess-abc", user_id="user-xyz")

        with (
            patch(
                "sage_poc.nodes.output_gate.summarise_history",
                new=AsyncMock(return_value="Summary text"),
            ) as mock_summarise,
            patch(
                "sage_poc.nodes.output_gate._persist_session_summary",
                new=AsyncMock(),
            ) as mock_persist,
        ):
            self._run_node(state)

        mock_summarise.assert_not_called()
        mock_persist.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for _persist_session_summary directly
# ---------------------------------------------------------------------------

class TestPersistSessionSummaryHelper:
    """Unit tests for the _persist_session_summary helper in isolation.

    Because PostgresMemoryRepository and get_embedding_async are deferred
    imports (inside the function body), we patch them at their *source* modules
    via sys.modules injection rather than as attributes of output_gate.
    """

    def _run_persist(self, mock_app, mock_repo, mock_embedding, **kwargs):
        """
        Run _persist_session_summary with fully-mocked deferred imports.

        We patch:
          - sys.modules["server"]           => module with .app = mock_app
          - sage_poc.memory.postgres_repository.PostgresMemoryRepository
                                            => constructor returning mock_repo
          - sage_poc.memory.embedding.get_embedding_async => AsyncMock
        """
        import sys
        from unittest.mock import MagicMock as MM

        fake_server_module = MM()
        fake_server_module.app = mock_app

        fake_repo_module = MM()
        fake_repo_module.PostgresMemoryRepository = MagicMock(return_value=mock_repo)

        fake_embedding_module = MM()
        fake_embedding_module.get_embedding_async = mock_embedding

        modules_patch = {
            "server": fake_server_module,
            "sage_poc.memory.postgres_repository": fake_repo_module,
            "sage_poc.memory.embedding": fake_embedding_module,
        }

        from sage_poc.nodes.output_gate import _persist_session_summary

        async def _runner():
            with patch.dict(sys.modules, modules_patch):
                await _persist_session_summary(**kwargs)

        asyncio.run(_runner())

    def _make_mock_app_and_repo(self):
        """Return (mock_app, mock_repo, mock_save) wired together."""
        mock_pool = MagicMock()
        mock_app = MagicMock()
        mock_app.state._db_pool = mock_pool

        mock_save = AsyncMock()
        mock_repo_instance = MagicMock()
        mock_repo_instance.save_session_summary = mock_save

        return mock_app, mock_pool, mock_repo_instance, mock_save

    def test_safety_level_crisis_when_crisis_flags(self):
        """crisis_flags non-empty => safety_level='crisis'."""
        mock_app, _, mock_repo, mock_save = self._make_mock_app_and_repo()
        mock_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-1",
            user_id="user-1",
            summary_text="Some summary",
            crisis_flags=["suicidal_ideation"],
            clinical_flags=[],
        )

        mock_save.assert_called_once()
        # Positional args: (session_id, user_id, summary_text, embedding, safety_level)
        args = mock_save.call_args.args
        assert args[4] == "crisis"

    def test_safety_level_clinical_when_no_crisis(self):
        """crisis_flags=[], clinical_flags non-empty => safety_level='clinical'."""
        mock_app, _, mock_repo, mock_save = self._make_mock_app_and_repo()
        mock_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-2",
            user_id="user-2",
            summary_text="Some summary",
            crisis_flags=[],
            clinical_flags=["substance_use"],
        )

        mock_save.assert_called_once()
        args = mock_save.call_args.args
        assert args[4] == "clinical"

    def test_safety_level_normal_when_no_flags(self):
        """Both flags empty => safety_level='normal'."""
        mock_app, _, mock_repo, mock_save = self._make_mock_app_and_repo()
        mock_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-3",
            user_id="user-3",
            summary_text="Some summary",
            crisis_flags=[],
            clinical_flags=[],
        )

        mock_save.assert_called_once()
        args = mock_save.call_args.args
        assert args[4] == "normal"

    def test_no_pool_returns_early(self):
        """When pool is None, save_session_summary must NOT be called."""
        mock_app = MagicMock()
        mock_app.state._db_pool = None

        mock_save = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.save_session_summary = mock_save
        mock_embedding = AsyncMock(return_value=[0.1])

        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-4",
            user_id="user-4",
            summary_text="Some summary",
            crisis_flags=[],
            clinical_flags=[],
        )

        mock_save.assert_not_called()

    # -----------------------------------------------------------------------
    # Decoupled flag-write behaviour — exercises the try/except added in Rec 3
    # -----------------------------------------------------------------------

    def test_flag_write_called_in_success_path(self):
        """write_persisted_clinical_flags must be awaited after a successful summary write.

        Both writes use the same mocked PostgresMemoryRepository instance because
        _run_persist patches PostgresMemoryRepository to always return mock_repo.
        """
        mock_app, _, mock_repo, mock_save = self._make_mock_app_and_repo()
        mock_write_flags = AsyncMock()
        mock_repo.write_persisted_clinical_flags = mock_write_flags
        mock_embedding = AsyncMock(return_value=[0.1])

        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-5",
            user_id="user-5",
            summary_text="Some summary",
            crisis_flags=[],
            clinical_flags=["substance_use"],
        )

        mock_save.assert_called_once()
        mock_write_flags.assert_awaited_once()

    def test_flag_write_called_even_when_summary_save_raises(self):
        """write_persisted_clinical_flags must still be awaited when save_session_summary raises.

        The flag write is placed after (and outside) the try/except that guards
        save_session_summary. A summary DB failure must not block flag persistence
        since persisted_clinical_flags feeds safety_check at the next session start.
        """
        mock_app, _, mock_repo, mock_save = self._make_mock_app_and_repo()
        mock_save.side_effect = Exception("simulated summary DB failure")
        mock_write_flags = AsyncMock()
        mock_repo.write_persisted_clinical_flags = mock_write_flags
        mock_embedding = AsyncMock(return_value=[0.1])

        # Must not raise — summary failure is swallowed by the outer try/except
        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-6",
            user_id="user-6",
            summary_text="Some summary",
            crisis_flags=[],
            clinical_flags=["substance_use"],
        )

        mock_write_flags.assert_awaited_once()

    def test_flag_write_exception_is_swallowed(self):
        """An exception from write_persisted_clinical_flags must not propagate.

        _persist_session_summary runs as an asyncio.create_task background task.
        An unhandled exception there would be silently dropped by the event loop
        rather than surfacing to the caller — a silent clinical data loss. The
        explicit try/except added around the flag write ensures it is logged.
        """
        mock_app, _, mock_repo, mock_save = self._make_mock_app_and_repo()
        mock_write_flags = AsyncMock(side_effect=Exception("flags DB failure"))
        mock_repo.write_persisted_clinical_flags = mock_write_flags
        mock_embedding = AsyncMock(return_value=[0.1])

        # Must not raise — flag write failure must be caught and logged, not propagated
        self._run_persist(
            mock_app=mock_app,
            mock_repo=mock_repo,
            mock_embedding=mock_embedding,
            session_id="sess-7",
            user_id="user-7",
            summary_text="Some summary",
            crisis_flags=[],
            clinical_flags=["substance_use"],
        )

        mock_save.assert_called_once()
