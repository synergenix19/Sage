"""Offline historical-replay driver for the native-Arabic shadow-measure.

Replays real Arabic user messages (source='historical_replay', from the `messages`
table) and the curated calibration set (source='seed', seed_inputs.json) through the
SAME instruments the live shadow-measure uses — sage_poc.language.async_translate_to_english
to reconstruct message_en, sage_poc.shadow_arabic.generate_shadow_arabic for the native
generation, scripts/register_eval/replay_gates.py::replay_gates_on_row for the offline
gate-fire estimate — and lands provenance-tagged rows in shadow_register_eval (migration
013). This is a MEASUREMENT job: it never touches the live serving path, SageState, or
session_audit.

Idempotent + resumable: rows are upserted on (source_message_id, shadow_exemplar_version)
— the partial unique index migration 013 adds — so re-running the same input under the
same exemplar version can never produce more than one row. Before spending any
translate/generate calls, the driver queries which (source_message_id, exemplar_version)
pairs already exist and skips them, so a killed run resumes without re-spending external
calls. select_pool(exemplar_version) is the read-side counterpart: it pulls only rows for
one exemplar_version, since a blinded rater comparison must never mix generations from two
different exemplar versions of the same input.

Rate-limited: an asyncio.Semaphore bounds in-flight translate/generate/gate calls to
`concurrency`, with an optional `rate_delay_s` pause per item — ~3 external calls/item
(translate, generate, the gate replay's own back-translation) times ~431 historical rows
must not contend with prod serving quota.

CLI:
    python -m scripts.register_eval.replay_driver seed --run-id calib-1
    python -m scripts.register_eval.replay_driver historical_replay --limit 50 --concurrency 4
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

from scripts.register_eval.replay_gates import replay_gates_on_row, gate_fire_summary

_log = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).parent / "seed_inputs.json"

# Arabic-script filter, matches the codebase's existing `content ~ '[؀-ۿ]'` convention
# (messages table, role='user') — PostgREST's `match` operator applies the same regex.
_ARABIC_SCRIPT_RANGE = "[؀-ۿ]"


# --------------------------------------------------------------------------------------
# Default (real) external dependencies — overridable by callers/tests.
# --------------------------------------------------------------------------------------

async def _default_translate(text: str) -> str:
    from sage_poc.language import async_translate_to_english  # noqa: PLC0415
    return await async_translate_to_english(text)


async def _default_generate(state: dict) -> dict | None:
    from sage_poc.shadow_arabic import generate_shadow_arabic  # noqa: PLC0415
    return await generate_shadow_arabic(state)


class ReplayClient:
    """Thin Supabase REST wrapper for the replay driver's DB operations. Real HTTP by
    default; tests inject a fake implementing the same async interface (see
    tests/test_replay_driver.py::_FakeClient).
    """

    def __init__(self, url: str | None = None, key: str | None = None, http=None):
        self._url = url or os.environ.get("SUPABASE_URL")
        self._key = key or os.environ.get("SUPABASE_SERVICE_KEY")
        self._http = http

    def _headers(self, *, upsert: bool = False) -> dict:
        k = self._key or ""
        h = {
            "apikey": k,
            "Authorization": f"Bearer {k}",
            "Content-Type": "application/json",
        }
        if upsert:
            # merge-duplicates + the on_conflict target below turns the POST into the
            # UPSERT that backs the (source_message_id, shadow_exemplar_version) key.
            h["Prefer"] = "resolution=merge-duplicates,return=minimal"
        return h

    async def _client(self):
        if self._http is None:
            import httpx  # noqa: PLC0415
            self._http = httpx.AsyncClient()
        return self._http

    async def fetch_historical_messages(self, *, limit: int | None = None) -> list[dict]:
        http = await self._client()
        params = {
            "select": "id,session_id,turn_number,content,clinical_flags",
            "role": "eq.user",
            "content": f"match.{_ARABIC_SCRIPT_RANGE}",
            "order": "id.asc",
        }
        if limit is not None:
            params["limit"] = str(limit)
        r = await http.get(f"{self._url}/rest/v1/messages", headers=self._headers(), params=params, timeout=30.0)
        r.raise_for_status()
        return r.json()

    async def fetch_done_source_ids(self, exemplar_version: str) -> set[str]:
        http = await self._client()
        params = {
            "select": "source_message_id",
            "shadow_exemplar_version": f"eq.{exemplar_version}",
            "source_message_id": "not.is.null",
        }
        r = await http.get(f"{self._url}/rest/v1/shadow_register_eval", headers=self._headers(), params=params, timeout=30.0)
        r.raise_for_status()
        return {row["source_message_id"] for row in r.json() if row.get("source_message_id")}

    async def upsert_row(self, row: dict) -> None:
        http = await self._client()
        r = await http.post(
            f"{self._url}/rest/v1/shadow_register_eval",
            headers=self._headers(upsert=True),
            params={"on_conflict": "source_message_id,shadow_exemplar_version"},
            json=row,
            timeout=10.0,
        )
        r.raise_for_status()

    async def select_pool(self, exemplar_version: str) -> list[dict]:
        http = await self._client()
        params = {
            "select": "*",
            "shadow_exemplar_version": f"eq.{exemplar_version}",
            "source_message_id": "not.is.null",
        }
        r = await http.get(f"{self._url}/rest/v1/shadow_register_eval", headers=self._headers(), params=params, timeout=30.0)
        r.raise_for_status()
        return r.json()


# --------------------------------------------------------------------------------------
# Item loading
# --------------------------------------------------------------------------------------

def _load_seed_items(*, limit: int | None = None) -> list[dict]:
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    items = []
    for entry in data.get("inputs", []):
        text = (entry.get("text") or "").strip()
        if not text:
            # PLACEHOLDER_NATIVE_AUTHOR entries have no authored text yet — nothing to
            # translate/generate from; skip rather than fabricate.
            continue
        items.append({
            "source_message_id": entry["id"],
            "session_id": None,
            "turn_number": None,
            "clinical_flags": [],
            "raw_message": text,
        })
    if limit is not None:
        items = items[:limit]
    return items


async def _load_historical_items(client: ReplayClient, *, limit: int | None = None) -> list[dict]:
    rows = await client.fetch_historical_messages(limit=limit)
    items = []
    for row in rows:
        items.append({
            "source_message_id": str(row["id"]),
            "session_id": row.get("session_id"),
            "turn_number": row.get("turn_number"),
            "clinical_flags": row.get("clinical_flags") or [],
            "raw_message": row["content"],
        })
    return items


async def _load_items(source: str, client: ReplayClient, *, limit: int | None = None) -> list[dict]:
    if source == "seed":
        return _load_seed_items(limit=limit)
    if source == "historical_replay":
        return await _load_historical_items(client, limit=limit)
    raise ValueError(f"unknown source: {source!r} (expected 'seed' or 'historical_replay')")


def _build_replay_row(item: dict, message_en: str, out: dict, *, source: str, run_id: str) -> dict:
    """Row shape mirrors shadow_eval.build_shadow_eval_row's live-payload columns, plus
    migration 013's provenance columns. Built directly (not via build_shadow_eval_row)
    because that helper defaults session_id/turn_number to ""/0 — wrong for seed rows,
    which legitimately have neither (migration 013 makes both columns nullable for
    exactly this reason). tool_loop_iterations/shadow_timed_out don't apply to an
    offline generate() call (no live tool loop instrumentation here); shadow_timed_out
    is always False because generate() already fails open to None on any error/timeout
    (see test_generation_none_writes_no_row) rather than a live "censored" observation.
    """
    return {
        "session_id": item.get("session_id"),
        "turn_number": item.get("turn_number"),
        "message_en": message_en,
        "clinical_flags": item.get("clinical_flags") or [],
        "shadow_arabic_text": out["text"],
        "shadow_prompt_hash": out["prompt_hash"],
        "shadow_exemplar_version": out["exemplar_version"],
        "generation_language": out["generation_language"],
        "shadow_gen_latency_ms": out["gen_latency_ms"],
        "tool_loop_iterations": None,
        "shadow_timed_out": False,
        "source": source,
        "source_message_id": item["source_message_id"],
        "run_id": run_id,
    }


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------

async def run_replay(
    source: str,
    *,
    limit: int | None = None,
    exemplar_version: str | None = None,
    run_id: str,
    concurrency: int = 4,
    rate_delay_s: float = 0.0,
    client: ReplayClient | None = None,
    translate=None,
    generate=None,
) -> dict:
    """Replay `source` ('seed' | 'historical_replay') through the shadow generator and
    gate replay, writing provenance-tagged rows to shadow_register_eval.

    Returns a summary dict (total_items, skipped_already_done, processed, written,
    gate_summary) — never raises on a per-item failure; generate() is already fail-open
    (returns None), and a None generation is logged + skipped (no row), matching the
    live shadow-measure's fail-open contract.
    """
    client = client or ReplayClient()
    translate = translate or _default_translate
    generate = generate or _default_generate

    if exemplar_version is None:
        from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars  # noqa: PLC0415
        exemplar_version, _ = load_khaleeji_shadow_exemplars()

    items = await _load_items(source, client, limit=limit)

    done_ids = await client.fetch_done_source_ids(exemplar_version)
    todo = [it for it in items if it["source_message_id"] not in done_ids]
    skipped = len(items) - len(todo)
    if skipped:
        _log.info("[replay] skipping %d already-done item(s) for exemplar_version=%s (resumed run)",
                   skipped, exemplar_version)

    sem = asyncio.Semaphore(max(1, concurrency))
    counters_lock = asyncio.Lock()
    processed = 0
    written = 0
    gate_rows: list[dict] = []

    async def _process(item: dict) -> None:
        nonlocal processed, written
        async with sem:
            try:
                message_en = await translate(item["raw_message"])
                state = {
                    "detected_language": "ar",
                    "message_en": message_en,
                    "clinical_flags": item.get("clinical_flags") or [],
                    "raw_message": item["raw_message"],
                }
                out = await generate(state)
                if rate_delay_s:
                    await asyncio.sleep(rate_delay_s)

                if out is None:
                    _log.info("[replay] generation returned None (fail-open skip) for source_message_id=%s",
                              item["source_message_id"])
                    return

                gate = await replay_gates_on_row({
                    "message_en": message_en,
                    "clinical_flags": item.get("clinical_flags") or [],
                    "shadow_arabic_text": out["text"],
                })
                row = _build_replay_row(item, message_en, out, source=source, run_id=run_id)
                await client.upsert_row(row)

                async with counters_lock:
                    gate_rows.append(gate)
                    written += 1
            finally:
                async with counters_lock:
                    processed += 1

    await asyncio.gather(*[_process(item) for item in todo])

    summary = {
        "source": source,
        "run_id": run_id,
        "exemplar_version": exemplar_version,
        "total_items": len(items),
        "skipped_already_done": skipped,
        "processed": processed,
        "written": written,
        "gate_summary": gate_fire_summary(gate_rows),
    }
    _log.info("[replay] %s", summary)
    return summary


async def select_pool(exemplar_version: str, *, client: ReplayClient | None = None) -> list[dict]:
    """Return only shadow_register_eval rows for exemplar_version — the clean, single-
    version pool the blinding harness must draw from. Mixing exemplar_version in one
    pool would invalidate the blinded rater comparison.
    """
    client = client or ReplayClient()
    return await client.select_pool(exemplar_version)


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", choices=["seed", "historical_replay"])
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--exemplar-version", default=None,
                    help="Defaults to the current khaleeji_shadow_exemplars.json version.")
    p.add_argument("--run-id", default=None, help="Defaults to a generated replay-<uuid8>.")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--rate-delay-s", type=float, default=0.0)
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _build_arg_parser().parse_args(argv)
    run_id = args.run_id or f"replay-{uuid.uuid4().hex[:8]}"
    summary = asyncio.run(run_replay(
        args.source,
        limit=args.limit,
        exemplar_version=args.exemplar_version,
        run_id=run_id,
        concurrency=args.concurrency,
        rate_delay_s=args.rate_delay_s,
    ))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
