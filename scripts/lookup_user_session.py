#!/usr/bin/env python3
"""
One-shot admin lookup: find a user by email and dump their recent session audit,
therapeutic profile, notifications, and raw LangGraph checkpoint turns.

Usage: uv run python scripts/lookup_user_session.py alec@sage-clinics.com
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

import asyncpg


async def main(email: str) -> None:
    url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(url)

    # 1. Resolve user_id
    user = await conn.fetchrow(
        "SELECT id, email, created_at FROM auth.users WHERE email = $1",
        email,
    )
    if not user:
        print(f"No user found for {email}")
        await conn.close()
        return

    user_id = str(user["id"])
    print(f"\n=== USER ===")
    print(f"  id:         {user_id}")
    print(f"  email:      {user['email']}")
    print(f"  created_at: {user['created_at']}")

    # 2. Session audit — all turns, ordered
    rows = await conn.fetch(
        """
        SELECT session_id, turn_number, inserted_at,
               node_path, primary_intent, secondary_intent,
               active_skill_id, active_step_id,
               crisis_state, crisis_flags, clinical_flags,
               engagement, emotional_intensity, latency_ms
        FROM public.session_audit
        WHERE user_id = $1
        ORDER BY inserted_at DESC
        LIMIT 100
        """,
        user["id"],
    )
    print(f"\n=== SESSION AUDIT ({len(rows)} turns) ===")
    for r in rows:
        print(
            f"  [{r['inserted_at'].strftime('%Y-%m-%d %H:%M:%S')}] "
            f"sess={r['session_id'][:8]}… turn={r['turn_number']} "
            f"intent={r['primary_intent'] or '-'} "
            f"skill={r['active_skill_id'] or '-'} "
            f"step={r['active_step_id'] or '-'} "
            f"crisis={r['crisis_state'] or '-'} "
            f"crisis_flags={list(r['crisis_flags'] or [])} "
            f"clinical_flags={list(r['clinical_flags'] or [])} "
            f"path={list(r['node_path'] or [])}"
        )

    # 3. Therapeutic profile
    profile = await conn.fetchrow(
        """
        SELECT effective_techniques, ineffective_techniques,
               distortion_patterns, disclosed_concerns,
               mood_trajectory, persisted_clinical_flags,
               session_count, total_skills_completed, last_updated_at
        FROM public.user_therapeutic_profiles
        WHERE user_id = $1
        """,
        user_id,
    )
    print(f"\n=== THERAPEUTIC PROFILE ===")
    if profile:
        for k, v in profile.items():
            val = v
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            print(f"  {k}: {val}")
    else:
        print("  (no profile yet)")

    # 4. Clinician notifications
    notifs = await conn.fetch(
        """
        SELECT session_id, reason, source, severity, status, created_at, message
        FROM public.clinician_notifications
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 20
        """,
        user_id,
    )
    print(f"\n=== CLINICIAN NOTIFICATIONS ({len(notifs)}) ===")
    for n in notifs:
        print(
            f"  [{n['created_at'].strftime('%Y-%m-%d %H:%M:%S')}] "
            f"severity={n['severity']} reason={n['reason']} "
            f"source={n['source']} status={n['status']}"
        )
        if n["message"]:
            print(f"    msg: {n['message'][:120]}")

    # 5. Audit log (rule substitutions / crisis activations)
    audit = await conn.fetch(
        """
        SELECT session_id, turn_number, rule_id, created_at, substitute_with
        FROM public.audit_log
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 20
        """,
        user_id,
    )
    print(f"\n=== AUDIT LOG / RULE ACTIVATIONS ({len(audit)}) ===")
    for a in audit:
        print(
            f"  [{a['created_at'].strftime('%Y-%m-%d %H:%M:%S')}] "
            f"sess={a['session_id'][:8]}… turn={a['turn_number']} "
            f"rule={a['rule_id']} sub={str(a['substitute_with'] or '')[:80]}"
        )

    # 6. Raw LangGraph messages — last session only
    if rows:
        last_session = rows[0]["session_id"]
        cp = await conn.fetchrow(
            """
            SELECT checkpoint
            FROM langgraph_checkpoints
            WHERE thread_id = $1
            ORDER BY checkpoint_id DESC
            LIMIT 1
            """,
            last_session,
        )
        if not cp:
            # Try alternate table name used by older LangGraph versions
            cp = await conn.fetchrow(
                """
                SELECT checkpoint
                FROM checkpoints
                WHERE thread_id = $1
                ORDER BY checkpoint_id DESC
                LIMIT 1
                """,
                last_session,
            )
        print(f"\n=== RAW MESSAGES (last session: {last_session[:8]}…) ===")
        if cp:
            data = cp["checkpoint"]
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, dict):
                messages = (
                    data.get("channel_values", {}).get("messages", [])
                    or data.get("messages", [])
                )
                for m in messages:
                    role = m.get("type") or m.get("role", "?")
                    content = m.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(
                            c.get("text", "") if isinstance(c, dict) else str(c)
                            for c in content
                        )
                    print(f"  [{role}] {str(content)[:300]}")
            else:
                print(f"  (unexpected checkpoint format: {type(data)})")
        else:
            print("  (no checkpoint found)")

    await conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/lookup_user_session.py <email>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
