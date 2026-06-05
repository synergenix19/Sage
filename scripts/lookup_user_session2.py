#!/usr/bin/env python3
import asyncio, json, os, sys
from dotenv import load_dotenv
load_dotenv()
import asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    user_id = "82f3ed9f-acf7-4533-93cc-244f81727475"

    row = await conn.fetchrow(
        "SELECT session_id FROM public.session_audit WHERE user_id = $1 ORDER BY inserted_at DESC LIMIT 1",
        user_id
    )
    last_session = row["session_id"]
    print(f"Last session: {last_session}")

    # Audit log
    audit = await conn.fetch(
        "SELECT session_id, turn_number, rule_id, created_at, substitute_with "
        "FROM public.audit_log WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20",
        user_id
    )
    print(f"\n=== AUDIT LOG ({len(audit)} entries) ===")
    for a in audit:
        print(f"  turn={a['turn_number']} rule={a['rule_id']} sub={str(a['substitute_with'] or '')[:100]}")

    # Which clinical tables exist?
    tables = await conn.fetch(
        """SELECT tablename FROM pg_tables
           WHERE schemaname = 'public'
           AND (tablename LIKE '%notif%' OR tablename LIKE '%review%' OR tablename LIKE '%clinical%')"""
    )
    print(f"\n=== CLINICAL/NOTIFICATION TABLES IN PUBLIC SCHEMA ===")
    for t in tables:
        print(f"  {t['tablename']}")

    # Clinician review queue
    try:
        reviews = await conn.fetch(
            "SELECT id, session_id, reason, severity, status, created_at "
            "FROM public.clinician_review_queue WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
            user_id
        )
        print(f"\n=== CLINICIAN REVIEW QUEUE ({len(reviews)}) ===")
        for r in reviews:
            print(f"  {dict(r)}")
    except Exception as e:
        print(f"  review queue error: {e}")

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
                print(f"\n  (no rows in {table} for this session)")
            break
        except Exception as e:
            print(f"  ({table}: {e})")

    await conn.close()

asyncio.run(main())
