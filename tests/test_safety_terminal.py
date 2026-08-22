"""Fix round 3, item 3: safety/terminal.py's spawn_safety_audit now DELEGATES to
observability.spawn_logged (one idiom, one implementation -- controller ruling M2). These
tests pin that the delegation is behavior-preserving: the three SAFETY-EXIT terminals'
distinct log text and the strong-ref task-set protection both survive the refactor.
"""
import asyncio
import logging

import pytest

from sage_poc import observability
from sage_poc.safety.terminal import spawn_safety_audit


@pytest.mark.asyncio
async def test_spawn_safety_audit_preserves_its_own_distinct_log_text(caplog):
    """The three SAFETY-EXIT terminals' pinned log shape ("[%s] session audit error: %s")
    must survive delegation unchanged -- NOT spawn_logged's own default wording
    ("[%s] background task error: %s"). External review/alerting may key on this exact
    string."""
    async def _boom():
        raise RuntimeError("simulated audit write failure")

    log = logging.getLogger("test.safety.terminal")
    with caplog.at_level("WARNING", logger="test.safety.terminal"):
        task = observability.spawn_logged(_boom(), "medical_response", log=log,
                                           message="[%s] session audit error: %s")
        with pytest.raises(RuntimeError):
            await task

    messages = [r.getMessage() for r in caplog.records]
    assert any(m == "[medical_response] session audit error: simulated audit write failure"
               for m in messages), f"expected the terminal's exact log text; got: {messages}"


@pytest.mark.asyncio
async def test_spawn_safety_audit_itself_produces_the_terminal_log_text(monkeypatch, caplog):
    """End-to-end through spawn_safety_audit's real call shape (not spawn_logged directly),
    proving the delegation's `message=` wiring in safety/terminal.py is correct, not just
    that spawn_logged supports a custom message in isolation."""
    from sage_poc.audit import write_session_audit as real_write_session_audit  # noqa: F401

    async def _failing_write_session_audit(row):
        raise RuntimeError("boom")

    monkeypatch.setattr("sage_poc.safety.terminal.write_session_audit", _failing_write_session_audit)

    log = logging.getLogger("test.safety.terminal.e2e")
    with caplog.at_level("WARNING", logger="test.safety.terminal.e2e"):
        task = spawn_safety_audit({"path": []}, {"gate_path": "medical"}, log, "medical_response")
        with pytest.raises(RuntimeError):
            await task

    messages = [r.getMessage() for r in caplog.records]
    assert any(m == "[medical_response] session audit error: boom" for m in messages), (
        f"spawn_safety_audit must preserve its own log text through delegation; got: {messages}"
    )


@pytest.mark.asyncio
async def test_spawn_safety_audit_task_is_strong_ref_protected(monkeypatch):
    """spawn_logged's module-level strong-ref task-set (fix round 3) now protects the
    SAFETY-EXIT terminals' audit tasks too, via delegation -- prevents the asyncio hazard
    where a task with no other live reference can be garbage-collected mid-flight."""
    release = asyncio.Event()

    async def _slow_write_session_audit(row):
        await release.wait()

    monkeypatch.setattr("sage_poc.safety.terminal.write_session_audit", _slow_write_session_audit)

    log = logging.getLogger("test.safety.terminal.strongref")
    task = spawn_safety_audit({"path": []}, {"gate_path": "medical"}, log, "medical_response")

    # The task must be held in observability's strong-ref set while pending -- this is the
    # actual mechanism that prevents premature GC, not just "the task object exists".
    assert task in observability._background_tasks, (
        "spawn_safety_audit's task must be strong-ref held via spawn_logged's delegation"
    )

    release.set()
    await task
    # Once done, the done-callback discards it from the set (bounded growth).
    assert task not in observability._background_tasks
