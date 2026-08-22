"""P2 Task 7a: unit tests for observability.spawn_logged, the dedup of the
create_task + add_done_callback fire-and-forget idiom used across the audit/notify
call sites (graph.py, output_gate.py, screen/medical/high_risk_response.py)."""
import asyncio
import logging

import pytest

from sage_poc.observability import spawn_logged


async def test_successful_coro_completes_silently(caplog):
    async def _ok():
        return "done"

    with caplog.at_level(logging.WARNING):
        task = spawn_logged(_ok(), "test-success")
        result = await task

    assert result == "done"
    assert not any("test-success" in r.message for r in caplog.records)


async def test_raising_coro_logs_a_warning_via_callback(caplog):
    async def _boom():
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.WARNING):
        task = spawn_logged(_boom(), "test-failure")
        # Let the task run and its done-callback fire before asserting.
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError):
            await task
        await asyncio.sleep(0)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("test-failure" in r.message and "kaboom" in r.message for r in warnings)


async def test_cancelled_task_does_not_log(caplog):
    async def _hang():
        await asyncio.sleep(10)

    with caplog.at_level(logging.WARNING):
        task = spawn_logged(_hang(), "test-cancelled")
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)

    assert not any("test-cancelled" in r.message for r in caplog.records)


async def test_uses_supplied_logger_when_given():
    async def _boom():
        raise ValueError("nope")

    calls = []

    class _FakeLogger:
        def warning(self, fmt, *args):
            calls.append(fmt % args)

    task = spawn_logged(_boom(), "custom-logger", log=_FakeLogger())
    await asyncio.sleep(0)
    with pytest.raises(ValueError):
        await task
    await asyncio.sleep(0)

    assert any("custom-logger" in c and "nope" in c for c in calls)


async def test_returns_a_real_task_that_can_be_awaited():
    async def _val():
        return 42

    task = spawn_logged(_val(), "test-return-type")
    assert isinstance(task, asyncio.Task)
    assert await task == 42
