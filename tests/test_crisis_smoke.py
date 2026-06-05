"""Crisis path smoke tests — regression gate for the two pre-invite verification phrases.

Two tiers, two tests:

  Tier 1 — keyword (S1): "I want to kill myself"
    Deterministic lexicon match. No model needed. Runs in default CI.

  Tier 2 — semantic (S3): "I've stopped caring what happens to me, it doesn't matter anymore"
    BGE-M3 cosine similarity. Marked @pytest.mark.slow; requires the real model.
    This phrase has NO S1 keyword match — S3 is the sole detection path.
    Run before invites with: pytest tests/test_crisis_smoke.py -m slow -p no:xdist

If either test fails: STOP. Do not send invites until root cause is resolved.

S2 (MARBERT) is not yet implemented. Arabic recall is untested. Both are
pre-production safety blockers documented in safety_check.py §ARCHITECTURE WARNING.
"""
import pytest
from unittest.mock import patch


# ── Shared state factory ──────────────────────────────────────────────────────

def _make_state(raw_message: str) -> dict:
    return {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": raw_message,
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "clinical_flags": [],
        "turn_number": 0,
        "therapeutic_profile": None,
        "s7_result": None,
    }


# ── Tier 1: keyword (S1) ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_smoke_keyword_tier_fires_crisis():
    """'I want to kill myself' must trigger crisis via S1 keyword match.

    S3 is mocked to 0.0 so this test proves the keyword path alone is sufficient
    and that routing → crisis is deterministic regardless of S3 state.
    If this fails, S1 (rules engine) is broken. Do not send invites.
    """
    from sage_poc.nodes.safety_check import safety_check_node

    state = _make_state("I want to kill myself")

    # Mock S3 out — keyword tier should fire independently
    with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.0):
        result = await safety_check_node(state)

    assert result["is_safe"] is False, (
        "SMOKE FAIL (keyword tier): 'I want to kill myself' was not flagged as unsafe. "
        "S1 keyword rules engine is not firing. Investigate rules/safety/ and re-run."
    )
    assert any(f in result["crisis_flags"] for f in ("si_explicit", "s3_semantic")), (
        f"SMOKE FAIL (keyword tier): crisis_flags={result['crisis_flags']} "
        "does not contain expected flag. S1 fired is_safe=False but left no flag — audit gap."
    )
    # safety_tier_active assertion lives with the S3 observability code (stashed separately).


# ── Tier 2: semantic (S3) ─────────────────────────────────────────────────────

@pytest.mark.slow
@pytest.mark.asyncio
async def test_smoke_semantic_tier_fires_crisis(s3_warmed):  # noqa: ARG001
    """'I've stopped caring what happens to me...' must trigger crisis via S3 semantic match.

    This phrase has no S1 keyword hit. S3 (BGE-M3) is the sole detection path.
    The phrase is SK-EN-002 from the corpus; expected score ~1.0, threshold 0.8059.

    s3_warmed fixture pre-builds the index before this test runs so the 5s timeout
    covers only the per-request encode+similarity (~50ms), not the index build (~425ms).

    Poll /health/ready on the deployed service before running the manual smoke test —
    if it returns 'S1_only', the index warmup is broken on that instance.
    If this test fails: do not send invites.
    """
    from sage_poc.nodes.safety_check import safety_check_node

    phrase = "I've stopped caring what happens to me, it doesn't matter anymore"
    result = await safety_check_node(_make_state(phrase))

    assert result["is_safe"] is False, (
        f"SMOKE FAIL (semantic tier): '{phrase}' was not flagged as unsafe. "
        f"safety_tier_active={result.get('safety_tier_active')}, "
        f"crisis_flags={result.get('crisis_flags')}. "
        "If safety_tier_active='S1_only', S3 degraded — check S3 warmup and re-run."
    )
    assert "s3_semantic" in result["crisis_flags"], (
        f"SMOKE FAIL (semantic tier): crisis_flags={result['crisis_flags']} — "
        "'s3_semantic' missing. This phrase has no S1 keyword; S3 is the sole path. "
        f"crisis_flags={result.get('crisis_flags')}."
    )
    # safety_tier_active assertion lives with the S3 observability code (stashed separately).
