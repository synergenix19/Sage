#!/usr/bin/env python3
import asyncio, json, os
from dotenv import load_dotenv
load_dotenv()
import asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    user_id = "82f3ed9f-acf7-4533-93cc-244f81727475"
    last_session = "1e193687-6281-458f-b745-4c26f751b5ba"

    # Raw messages table
    msgs = await conn.fetch(
        """SELECT role, content, created_at, session_id
           FROM public.messages
           WHERE session_id = $1
           ORDER BY created_at ASC""",
        last_session
    )
    print(f"=== MESSAGES ({len(msgs)} rows) ===")
    for m in msgs:
        content = m["content"]
        if isinstance(content, (bytes, memoryview)):
            content = json.loads(bytes(content))
        print(f"  [{m['created_at'].strftime('%H:%M:%S')}] [{m['role']}] {str(content)[:400]}")

    # chat_sessions
    sess = await conn.fetch(
        "SELECT id, user_id, created_at, ended_at FROM public.chat_sessions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5",
        user_id
    )
    print(f"\n=== CHAT SESSIONS ({len(sess)}) ===")
    for s in sess:
        print(f"  id={s['id']} created={s['created_at']} ended={s['ended_at']}")

    # Clinician review queue
    reviews = await conn.fetch(
        """SELECT id, session_id, reason, severity, status, created_at, notes
           FROM public.clinician_review_queue
           WHERE user_id = $1
           ORDER BY created_at DESC LIMIT 10""",
        user_id
    )
    print(f"\n=== CLINICIAN REVIEW QUEUE ({len(reviews)}) ===")
    for r in reviews:
        print(f"  severity={r['severity']} reason={r['reason']} status={r['status']} created={r['created_at']}")
        if r["notes"]:
            print(f"    notes: {r['notes'][:120]}")

    # mood_scores
    moods = await conn.fetch(
        "SELECT score, created_at, session_id FROM public.mood_scores WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10",
        user_id
    )
    print(f"\n=== MOOD SCORES ({len(moods)}) ===")
    for m in moods:
        print(f"  score={m['score']} at={m['created_at']}")

    # session_insights
    insights = await conn.fetch(
        "SELECT * FROM public.session_insights WHERE session_id = $1",
        last_session
    )
    print(f"\n=== SESSION INSIGHTS ({len(insights)}) ===")
    for i in insights:
        print(f"  {dict(i)}")

    # checkpoint blob — may hold message data
    blob_count = await conn.fetchval(
        "SELECT COUNT(*) FROM public.checkpoint_blobs WHERE thread_id = $1",
        last_session
    )
    print(f"\n=== CHECKPOINT BLOBS: {blob_count} blobs for this session ===")
    if blob_count and blob_count > 0:
        blobs = await conn.fetch(
            "SELECT channel, type, blob FROM public.checkpoint_blobs WHERE thread_id = $1 AND channel = 'messages' ORDER BY checkpoint_ns LIMIT 1",
            last_session
        )
        for b in blobs:
            print(f"  channel={b['channel']} type={b['type']}")
            raw = b["blob"]
            if raw:
                if isinstance(raw, (bytes, memoryview)):
                    raw = bytes(raw)
                print(f"  blob preview: {str(raw[:400])}")

    await conn.close()

asyncio.run(main())
