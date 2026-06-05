#!/usr/bin/env python3
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
import asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    uid = "82f3ed9f-acf7-4533-93cc-244f81727475"

    cols = await conn.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name='clinician_review_queue' ORDER BY ordinal_position"
    )
    print("clinician_review_queue cols:", [c["column_name"] for c in cols])

    reviews = await conn.fetch(
        "SELECT * FROM public.clinician_review_queue WHERE user_id = $1 ORDER BY created_at DESC LIMIT 10", uid
    )
    print(f"Review queue: {len(reviews)} rows")
    for r in reviews:
        print(f"  {dict(r)}")

    cols2 = await conn.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name='mood_scores' ORDER BY ordinal_position"
    )
    print("\nmood_scores cols:", [c["column_name"] for c in cols2])
    moods = await conn.fetch(
        "SELECT * FROM public.mood_scores WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5", uid
    )
    print(f"Mood rows: {len(moods)}")
    for m in moods:
        print(f"  {dict(m)}")

    await conn.close()

asyncio.run(main())
