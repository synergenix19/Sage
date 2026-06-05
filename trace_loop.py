#!/usr/bin/env python3
"""
Trace script: diagnose the sleep_hygiene assess_sleep loop.
Uses a dedicated test session_id — does not touch real user data.

Run: cd sage-poc && .venv/bin/python trace_loop.py
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# ── Logging: emit everything at WARNING+ but highlight our trace lines ───────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
# Silence noisy libraries; keep our trace and any unexpected errors
for noisy in ("httpx", "httpcore", "openai", "langchain", "psycopg"):
    logging.getLogger(noisy).setLevel(logging.ERROR)


# ── Messages that reproduced the loop ────────────────────────────────────────
CONVERSATION = [
    "hi",
    "I'm doing great, how about you!??",
    (
        "well, i don't know whats going well, but i do know i'm incredibly "
        "stressed off late and not sleeping too well"
    ),
    "just waking up really late, sleeping at 7 am, lying restless in bed",
    "just a lot of thoughts in my mind, about work, money, no relationships",
    "money",
    "i dont have stable income",
]

TEST_SESSION = "trace-loop-investigation-20260602"

# ── Minimal request/message stubs (mirrors server_helpers._RequestLike) ──────
class _Msg:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class _Req:
    def __init__(self, messages, session_id):
        self.messages = messages
        self.session_id = session_id
        self.user_id = None


async def main() -> None:
    from psycopg import AsyncConnection
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from sage_poc.graph import build_graph
    from sage_poc.server_helpers import _build_state, _stale_skill_overrides

    db_url = os.environ["DATABASE_URL"]

    # Mirror server.py lifespan: autocommit setup conn, then pool for saver
    async with await AsyncConnection.connect(
        db_url, autocommit=True, prepare_threshold=0, row_factory=dict_row
    ) as setup_conn:
        await AsyncPostgresSaver(setup_conn).setup()

    saver_pool = AsyncConnectionPool(conninfo=db_url, open=False)
    await saver_pool.open()

    try:
        saver = AsyncPostgresSaver(saver_pool)
        graph = build_graph(checkpointer=saver)

        history: list[_Msg] = []

        for turn_num, user_text in enumerate(CONVERSATION, start=1):
            history.append(_Msg("user", user_text))
            req = _Req(messages=list(history), session_id=TEST_SESSION)
            state = _build_state(req)
            state["therapeutic_profile"] = None

            # Print checkpoint state BEFORE this turn (mirrors checkpoint_read log)
            try:
                snap = await graph.checkpointer.aget(
                    {"configurable": {"thread_id": TEST_SESSION}}
                )
                ckpt = (snap.get("channel_values") or {}) if snap else {}
                overrides = _stale_skill_overrides(ckpt)
                state.update(overrides)
                print(
                    f"\n{'─'*70}\n"
                    f"TURN {turn_num}: {user_text[:72]}\n"
                    f"  CHECKPOINT_BEFORE  active_skill_id={ckpt.get('active_skill_id')!r}  "
                    f"active_step_id={ckpt.get('active_step_id')!r}"
                )
            except Exception as exc:
                print(f"\nTURN {turn_num}: checkpoint read error: {exc}")

            try:
                result = await asyncio.wait_for(
                    graph.ainvoke(
                        state,
                        config={"configurable": {"thread_id": TEST_SESSION}},
                    ),
                    timeout=30.0,
                )
                print(
                    f"  RESULT             primary_intent={result.get('primary_intent')!r}  "
                    f"executed_step_id={result.get('executed_step_id')!r}  "
                    f"active_step_id(written)={result.get('active_step_id')!r}"
                )
                asst = result.get("response") or result.get("response_en") or ""
                history.append(_Msg("assistant", asst))

            except asyncio.TimeoutError:
                print(f"  TIMEOUT after 30s")
            except Exception as exc:
                print(f"  ERROR: {exc}")
                import traceback
                traceback.print_exc()

    finally:
        await saver_pool.close()

    print("\n\n✓ Trace complete. Review the [STEP-ADVANCE-TRACE] lines above.")


if __name__ == "__main__":
    asyncio.run(main())
