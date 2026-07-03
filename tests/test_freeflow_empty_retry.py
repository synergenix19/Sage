"""W3: the empty-result regeneration is latency-bounded.

When the primary generation returns empty, freeflow does ONE regeneration attempt. That
attempt must be bounded by a short hard timeout — a fast vetted line (emitted by output_gate)
beats a slow second LLM round-trip that would blow the <3s p95 budget (resilient_invoke's own
timeout is 30s). On breach the helper returns "" so output_gate substitutes the vetted line.
"""
import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock

import sage_poc.nodes.freeflow_respond as ff


@pytest.mark.asyncio
async def test_bounded_empty_retry_returns_text_when_fast():
    with patch.object(ff, "resilient_invoke", new=AsyncMock(return_value="a warm reply")):
        out = await ff._bounded_empty_retry(
            None, [], node="freeflow_respond", language="en", fallback_llm=None
        )
    assert out == "a warm reply"


@pytest.mark.asyncio
async def test_bounded_empty_retry_defers_to_vetted_line_on_timeout():
    async def _slow(*a, **k):
        await asyncio.sleep(1.0)
        return "too late"

    with patch.object(ff, "resilient_invoke", new=_slow), \
         patch.object(ff, "EMPTY_RETRY_TIMEOUT_SECONDS", 0.05):
        t0 = time.monotonic()
        out = await ff._bounded_empty_retry(
            None, [], node="freeflow_respond", language="en", fallback_llm=None
        )
        elapsed = time.monotonic() - t0

    assert out == "", "on breach, return empty so output_gate emits the vetted line"
    assert elapsed < 0.5, "must not block on the slow retry (latency guard)"


def test_empty_retry_timeout_is_bounded_well_under_p95():
    # The retry budget must be far below the 3s p95 target and the 30s resilient default.
    assert 0 < ff.EMPTY_RETRY_TIMEOUT_SECONDS <= 3.0
