from __future__ import annotations
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    """Yields a ready AsyncPostgresSaver. DATABASE_URL is the sole coupling to the host.
    Swap host by changing the env var — no other code changes required.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required for checkpointing")
    async with asyncpg.create_pool(url) as pool:
        saver = AsyncPostgresSaver(pool)
        await saver.setup()  # idempotent: creates 4 LangGraph tables if missing
        yield saver
