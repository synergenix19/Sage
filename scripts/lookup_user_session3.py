#!/usr/bin/env python3
import asyncio, json, os
from dotenv import load_dotenv
load_dotenv()
import asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    user_id = "82f3ed9f-acf7-4533-93cc-244f81727475"

    last_session = "1e193687-6281-458f-b745-4c26f751b5ba"

    # Discover all public tables to know what actually exists
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    print("=== ALL PUBLIC TABLES ===")
    for t in tables:
        print(f"  {t['tablename']}")

    # LangGraph checkpoint tables
    for table in ["langgraph_checkpoints", "checkpoints"]:
        try:
            cp = await conn.fetchrow(
                f"SELECT checkpoint FROM {table} WHERE thread_id = $1 ORDER BY checkpoint_id DESC LIMIT 1",
                last_session
            )
            if cp:
                print(f"\n=== RAW MESSAGES (from {table}) ===")
                data = cp["checkpoint"]
                if isinstance(data, (bytes, memoryview)):
                    data = json.loads(bytes(data))
                elif isinstance(data, str):
                    data = json.loads(data)
                messages = (data.get("channel_values", {}).get("messages", [])
                            or data.get("messages", []))
                for m in messages:
                    role = m.get("type") or m.get("role", "?")
                    content = m.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(c.get("text","") if isinstance(c,dict) else str(c) for c in content)
                    print(f"  [{role}] {str(content)[:400]}")
            else:
                print(f"\n  (no checkpoint rows for this session in {table})")
            break
        except Exception as e:
            print(f"  ({table}: {e})")

    await conn.close()

asyncio.run(main())
