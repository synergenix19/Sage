"""Regression test for POST /extract-profile observations preservation.

Silent clinical-data-loss bug: the post-session profile merge in /extract-profile
omitted the `observations` key, so upsert_therapeutic_profile wrote an empty list
(`observations = EXCLUDED.observations`), wiping everything the in-conversation
`record_observation` tool had accumulated during the session. Because observations
are never surfaced in a prompt, the loss was invisible at runtime.

This pins the invariant on the actual upserted profile (behavior, not a log/comment
string): a /extract-profile run must carry the user's existing observations forward.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def reset_app_state():
    """Restore app.state after each test to prevent leakage across the suite."""
    from server import app
    orig_pool = getattr(app.state, "_db_pool", None)
    orig_graph = getattr(app.state, "_graph", None)
    yield
    app.state._db_pool = orig_pool
    app.state._graph = orig_graph


def _checkpoint(turn_count: int, history_len: int):
    return {
        "channel_values": {
            "conversation_history": [
                {"role": "user", "content": f"m{i}"} for i in range(history_len)
            ],
            "turn_count": turn_count,
            "clinical_flags": [],
        }
    }


def _run_extract_profile(existing_profile, extracted):
    """Drive POST /extract-profile with a mocked repo + checkpoint and return the
    profile dict handed to upsert_therapeutic_profile (i.e. the merge result)."""
    from server import app

    mock_repo = AsyncMock()
    mock_repo.get_therapeutic_profile = AsyncMock(return_value=existing_profile)
    mock_repo.upsert_therapeutic_profile = AsyncMock()

    app.state._db_pool = object()
    app.state._graph = MagicMock()
    app.state._graph.checkpointer.aget = AsyncMock(
        return_value=_checkpoint(turn_count=6, history_len=12)
    )
    return app, mock_repo


@pytest.mark.asyncio
async def test_extract_profile_preserves_observations_without_clobbering_other_fields():
    """A post-session extraction must not erase observations written mid-session,
    and must still merge the other profile fields correctly (no collateral clobber).

    This is the test that would have caught the original silent wipe: it asserts on
    the actual dict passed to upsert_therapeutic_profile (behavior, not a log string).
    """
    existing_observations = [
        {"text": "User identified own catastrophising unprompted",
         "type": "insight", "confidence": "high", "recorded_at": "2026-07-10"},
    ]
    existing_profile = {
        "observations": existing_observations,
        "last_extraction_turn": 0,
        "session_count": 2,
        "effective_techniques": ["box_breathing"],
        "mood_trajectory": [{"session": 1, "mood_score": 3}],
        "total_skills_completed": 4,
    }

    # The extractor returns the extracted keys — it never emits `observations`
    # (only the record_observation tool writes those), so a correct merge must
    # preserve `existing["observations"]` unchanged.
    extracted = {
        "effective_techniques": ["grounding"],
        "ineffective_techniques": [],
        "distortion_patterns": [],
        "disclosed_concerns": ["work stress"],
        "communication_style": "direct",
        "cultural_preferences": {},
        "mood_score": 5,
        "skills_completed": 1,
    }

    app, mock_repo = _run_extract_profile(existing_profile, extracted)

    with patch(
        "sage_poc.memory.postgres_repository.PostgresMemoryRepository",
        return_value=mock_repo,
    ), patch(
        "sage_poc.memory.profile_extractor.extract_session_profile",
        AsyncMock(return_value=extracted),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/extract-profile", json={
                "session_id": "sess-obs-1",
                "user_id": "user-obs-1",
            })

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    mock_repo.upsert_therapeutic_profile.assert_awaited_once()
    upserted = (
        mock_repo.upsert_therapeutic_profile.call_args.kwargs.get("profile")
        or mock_repo.upsert_therapeutic_profile.call_args.args[1]
    )

    # The fix under test: observations carried forward, not wiped to [].
    assert upserted.get("observations") == existing_observations, (
        "extract-profile must carry existing observations forward, not wipe them to []"
    )

    # And the fix must not disturb the rest of the merge:
    assert set(upserted["effective_techniques"]) == {"box_breathing", "grounding"}, (
        "effective_techniques must remain the set-union of existing + extracted"
    )
    assert upserted["session_count"] == 3, "session_count must increment existing (2 -> 3)"
    assert upserted["mood_trajectory"] == [
        {"session": 1, "mood_score": 3},
        {"session": 3, "mood_score": 5},
    ], "mood_trajectory must append the new session's mood, not drop the prior entry"
    assert upserted["total_skills_completed"] == 5, (
        "total_skills_completed must be existing (4) + extracted skills_completed (1)"
    )
