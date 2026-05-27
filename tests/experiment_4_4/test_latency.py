# tests/experiment_4_4/test_latency.py
#
# Experiment 4.4 — Phase 2 resistance scoring latency benchmark
# KPI: p95 < 3.0 seconds over a 5-sample run.
#
# Requires a live API key (OPENROUTER_API_KEY or equivalent).
# Marked @pytest.mark.slow — excluded from fast CI runs:
#   pytest tests/experiment_4_4/ -m "not slow"
#
# Run explicitly:
#   pytest tests/experiment_4_4/test_latency.py -v -s

import time
import statistics
import pytest

from sage_poc.nodes.skill_executor import _score_resistance_via_rules_service


@pytest.mark.slow
class TestPhase2ResistanceLatency:
    """Phase 2 resistance scoring must respond within 3 seconds at p95."""

    async def test_resistance_scoring_p95_under_3_seconds(self):
        """p95 latency for _score_resistance_via_rules_service must be < 3.0s.

        Uses 5 samples — sufficient for a development gate; production p95
        requires 100+ samples. The 3s budget reflects the <3s p95 KPI in V7 §16.2.
        """
        messages = [
            "This feels pointless to me honestly.",
            "I don't see how this is going to help with anything.",
            "I've tried this before and it never works.",
            "I guess I can give it a try even though I'm skeptical.",
            "I really don't want to do this right now.",
        ]
        times: list[float] = []
        for msg in messages:
            start = time.perf_counter()
            score = await _score_resistance_via_rules_service(msg)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            # Score may be None if service is unavailable — latency still measured
            assert score is None or (isinstance(score, int) and 0 <= score <= 10), (
                f"Resistance score must be int 0-10 or None, got {score!r}"
            )

        times.sort()
        p95_idx = max(0, int(len(times) * 0.95) - 1)
        p95 = times[p95_idx]
        mean = statistics.mean(times)
        p50 = times[len(times) // 2]

        print(f"\nPhase 2 latency — n={len(times)}")
        print(f"  p50:  {p50:.3f}s")
        print(f"  p95:  {p95:.3f}s")
        print(f"  mean: {mean:.3f}s")
        print(f"  all:  {[f'{t:.3f}' for t in times]}")

        assert p95 < 3.0, (
            f"Phase 2 p95 latency {p95:.3f}s exceeds the 3s KPI budget "
            f"(V7 §16.2). All samples: {[f'{t:.3f}s' for t in times]}"
        )

    @pytest.mark.slow
    async def test_resistance_scoring_returns_valid_integer_or_none(self):
        """Smoke test: resistance scorer must return int 0-10 or None, never raise."""
        test_cases = [
            "I really don't want to engage with this.",
            "Okay I'll try.",
            "",  # empty message edge case
        ]
        for msg in test_cases:
            score = await _score_resistance_via_rules_service(msg)
            assert score is None or (isinstance(score, int) and 0 <= score <= 10), (
                f"For message {msg[:20]!r}, expected int 0-10 or None, got {score!r}"
            )
