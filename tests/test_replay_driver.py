import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from scripts.register_eval.replay_driver import run_replay, select_pool


def _payload(text="شكرا لك", version="v1"):
    return {
        "text": text,
        "prompt_hash": "a" * 16,
        "exemplar_version": version,
        "generation_language": "ar_native",
        "gen_latency_ms": 5,
    }


class _FakeClient:
    """In-memory stand-in for the Supabase REST calls the driver makes.
    upsert_row enforces the same (source_message_id, exemplar_version) uniqueness
    the real partial unique index (migration 013) guarantees.
    """

    def __init__(self, historical_rows=None):
        self._historical_rows = historical_rows or []
        self.rows: dict[tuple[str, str], dict] = {}
        self.upsert_calls = 0

    async def fetch_historical_messages(self, *, limit=None):
        rows = self._historical_rows
        if limit is not None:
            rows = rows[:limit]
        return rows

    async def fetch_done_source_ids(self, exemplar_version):
        return {k[0] for k in self.rows if k[1] == exemplar_version}

    async def upsert_row(self, row):
        self.upsert_calls += 1
        key = (row["source_message_id"], row["shadow_exemplar_version"])
        self.rows[key] = row  # upsert semantics: same key overwrites, never appends

    async def select_pool(self, exemplar_version):
        return [r for k, r in self.rows.items() if k[1] == exemplar_version]


def _row(i, content="نص عربي"):
    return {"id": str(i), "session_id": f"s{i}", "turn_number": 1,
            "content": content, "clinical_flags": []}


def _run(*args, **kwargs):
    return asyncio.run(run_replay(*args, **kwargs))


@pytest.fixture(autouse=True)
def _patch_back_translate():
    # replay_gates_on_row (called by the driver per item) back-translates the
    # shadow text via sage_poc.language.async_translate_to_english — mirrors
    # tests/test_replay_gates.py's own patch target, no live network call.
    with patch("sage_poc.language.async_translate_to_english", new=AsyncMock(return_value="thank you")):
        yield


def test_replay_idempotent_upsert():
    client = _FakeClient(historical_rows=[_row(1)])
    translate = AsyncMock(return_value="thanks")
    generate = AsyncMock(return_value=_payload(version="v1"))

    _run("historical_replay", run_id="run-1", exemplar_version="v1",
         client=client, translate=translate, generate=generate)
    _run("historical_replay", run_id="run-2", exemplar_version="v1",
         client=client, translate=translate, generate=generate)

    assert len(client.rows) == 1


def test_provenance_fields_populated():
    client = _FakeClient(historical_rows=[_row(7)])
    translate = AsyncMock(return_value="thanks")
    generate = AsyncMock(return_value=_payload(version="v1"))

    _run("historical_replay", run_id="run-abc", exemplar_version="v1",
         client=client, translate=translate, generate=generate)

    row = next(iter(client.rows.values()))
    assert row["source"] == "historical_replay"
    assert row["source_message_id"] == "7"
    assert row["run_id"] == "run-abc"
    assert row["shadow_exemplar_version"] == "v1"


def test_gate_replay_result_persisted_per_row():
    # Layer 3's actionable signal (which gates fired, on which turn) must be durable
    # per-row, not only in the aggregated gate_summary the run returns.
    client = _FakeClient(historical_rows=[_row(9)])
    translate = AsyncMock(return_value="thanks")
    generate = AsyncMock(return_value=_payload(version="v1"))

    _run("historical_replay", run_id="run-g", exemplar_version="v1",
         client=client, translate=translate, generate=generate)

    gate = next(iter(client.rows.values()))["gate_replay_result"]
    assert gate is not None
    assert set(gate) >= {"cultural_fired", "banned_opener", "format_tokens", "back_en"}
    assert isinstance(gate["cultural_fired"], list)
    assert isinstance(gate["banned_opener"], bool)


def test_single_exemplar_version_selectable():
    client = _FakeClient(historical_rows=[_row(1), _row(2)])
    translate = AsyncMock(return_value="thanks")
    generate_v1 = AsyncMock(return_value=_payload(version="v1"))
    _run("historical_replay", run_id="run-1", exemplar_version="v1",
         client=client, translate=translate, generate=generate_v1)

    generate_v2 = AsyncMock(return_value=_payload(version="v2"))
    client._historical_rows = [_row(3)]  # a "new" item under v2
    _run("historical_replay", run_id="run-2", exemplar_version="v2",
         client=client, translate=translate, generate=generate_v2)

    pool_v1 = asyncio.run(select_pool("v1", client=client))
    pool_v2 = asyncio.run(select_pool("v2", client=client))
    assert len(pool_v1) == 2 and all(r["shadow_exemplar_version"] == "v1" for r in pool_v1)
    assert len(pool_v2) == 1 and all(r["shadow_exemplar_version"] == "v2" for r in pool_v2)


def test_replay_resumable_skips_done():
    client = _FakeClient(historical_rows=[_row(1), _row(2), _row(3)])
    # pre-seed item 2 as already done under v1
    client.rows[("2", "v1")] = {"source_message_id": "2", "shadow_exemplar_version": "v1"}

    translate = AsyncMock(return_value="thanks")
    generate = AsyncMock(return_value=_payload(version="v1"))

    summary = _run("historical_replay", run_id="run-1", exemplar_version="v1",
                    client=client, translate=translate, generate=generate)

    # generator must NOT have been called for the already-done item — only 2 calls
    assert generate.await_count == 2
    assert summary["skipped_already_done"] == 1
    assert summary["processed"] == 2


def test_rate_limited_concurrency_bounded():
    concurrency = 3
    n_items = 9
    client = _FakeClient(historical_rows=[_row(i) for i in range(n_items)])
    translate = AsyncMock(return_value="thanks")

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def generate(state):
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        async with lock:
            in_flight -= 1
        return _payload(version="v1")

    _run("historical_replay", run_id="run-1", exemplar_version="v1",
         client=client, translate=translate, generate=generate, concurrency=concurrency)

    assert max_in_flight <= concurrency
    assert len(client.rows) == n_items


def test_generation_none_writes_no_row():
    client = _FakeClient(historical_rows=[_row(1)])
    translate = AsyncMock(return_value="thanks")
    generate = AsyncMock(return_value=None)

    summary = _run("historical_replay", run_id="run-1", exemplar_version="v1",
                    client=client, translate=translate, generate=generate)

    assert client.rows == {}
    assert summary["written"] == 0
    assert client.upsert_calls == 0


def test_row_carries_gender_marked_from_raw_user_text():
    # gender_marked must be computed from the RAW Arabic user text (row["content"]),
    # not the reconstructed message_en — translate() below returns unrelated English
    # text, so if gender_marked came from message_en instead this would fail to
    # detect the feminine self-marking present only in the Arabic original.
    client = _FakeClient(historical_rows=[_row(1, content="أنا تعبانة ومحتاجة أتكلم")])
    translate = AsyncMock(return_value="I need to talk, not gendered in English")
    generate = AsyncMock(return_value=_payload(version="v1"))

    _run("historical_replay", run_id="run-1", exemplar_version="v1",
         client=client, translate=translate, generate=generate)

    row = next(iter(client.rows.values()))
    assert row["gender_marked"] == "f"


def test_row_carries_gender_marked_none_when_unmarked():
    client = _FakeClient(historical_rows=[_row(1, content="عندي اجتماع بكرة الصبح")])
    translate = AsyncMock(return_value="I have a meeting tomorrow morning")
    generate = AsyncMock(return_value=_payload(version="v1"))

    _run("historical_replay", run_id="run-1", exemplar_version="v1",
         client=client, translate=translate, generate=generate)

    row = next(iter(client.rows.values()))
    assert row["gender_marked"] == "none"
