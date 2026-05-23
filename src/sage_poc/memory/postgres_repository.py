from __future__ import annotations
import json
from typing import Optional

from sage_poc.memory.repository import MemoryRepository


class PostgresMemoryRepository(MemoryRepository):
    """MemoryRepository backed by asyncpg pool.
    Portable to any Postgres host — no Supabase-specific SQL.
    """

    def __init__(self, pool) -> None:
        self._pool = pool

    async def get_therapeutic_profile(self, user_id: str) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT effective_techniques, ineffective_techniques,
                       distortion_patterns, disclosed_concerns,
                       communication_style, cultural_preferences,
                       mood_trajectory, total_skills_completed,
                       session_count, last_extraction_turn, last_updated_at,
                       observations
                FROM public.user_therapeutic_profiles
                WHERE user_id = $1
                """,
                user_id,
            )
            if row is None:
                return None
            d = dict(row)
            # asyncpg returns jsonb as str — parse if needed
            for key in ("cultural_preferences", "mood_trajectory", "observations"):
                if isinstance(d.get(key), str):
                    d[key] = json.loads(d[key])
            return d

    async def upsert_therapeutic_profile(
        self,
        user_id: str,
        profile: dict,
        session_id: str,
    ) -> None:
        snapshot = json.dumps(profile)
        async with self._pool.acquire() as conn:
            # Write versioned snapshot first (PDPL audit trail)
            await conn.execute(
                """
                INSERT INTO public.therapeutic_profile_history
                  (user_id, session_id, extraction_source, snapshot)
                VALUES ($1, $2::uuid, 'llm_extraction', $3::jsonb)
                """,
                user_id, session_id, snapshot,
            )
            # Upsert main profile
            await conn.execute(
                """
                INSERT INTO public.user_therapeutic_profiles
                  (user_id, effective_techniques, ineffective_techniques,
                   distortion_patterns, disclosed_concerns, communication_style,
                   cultural_preferences, mood_trajectory, total_skills_completed,
                   session_count, last_extraction_turn, observations, last_updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10, $11, $12::jsonb, now())
                ON CONFLICT (user_id) DO UPDATE SET
                  effective_techniques   = EXCLUDED.effective_techniques,
                  ineffective_techniques = EXCLUDED.ineffective_techniques,
                  distortion_patterns    = EXCLUDED.distortion_patterns,
                  disclosed_concerns     = EXCLUDED.disclosed_concerns,
                  communication_style    = EXCLUDED.communication_style,
                  cultural_preferences   = EXCLUDED.cultural_preferences,
                  mood_trajectory        = EXCLUDED.mood_trajectory,
                  total_skills_completed = EXCLUDED.total_skills_completed,
                  session_count          = EXCLUDED.session_count,
                  last_extraction_turn   = EXCLUDED.last_extraction_turn,
                  observations           = EXCLUDED.observations,
                  last_updated_at        = now()
                """,
                user_id,
                profile.get("effective_techniques", []),
                profile.get("ineffective_techniques", []),
                profile.get("distortion_patterns", []),
                profile.get("disclosed_concerns", []),
                profile.get("communication_style"),
                json.dumps(profile.get("cultural_preferences", {})),
                json.dumps(profile.get("mood_trajectory", [])),
                profile.get("total_skills_completed", 0),
                profile.get("session_count", 0),
                profile.get("last_extraction_turn", 0),
                json.dumps(profile.get("observations", [])),
            )

    async def save_session_summary(
        self,
        session_id: str,
        user_id: str,
        summary_text: str,
        embedding: list[float],
        safety_level: str,
        skills_used: list[str] | None = None,
        mood_score: float | None = None,
    ) -> None:
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
        async with self._pool.acquire() as conn:
            # DELETE + INSERT because UNIQUE session_id is set in migration 005
            await conn.execute(
                "DELETE FROM public.session_summaries WHERE session_id = $1",
                session_id,
            )
            await conn.execute(
                """
                INSERT INTO public.session_summaries
                  (session_id, user_id, summary_text, embedding, safety_level, skills_used, mood_score)
                VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
                """,
                session_id, user_id, summary_text, vector_str, safety_level,
                skills_used or [], mood_score,
            )

    async def search_session_summaries(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 3,
        exclude_safety_levels: list[str] | None = None,
    ) -> list[dict]:
        excluded = exclude_safety_levels or []
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT summary_text, safety_level, skills_used, mood_score, created_at,
                       1 - (embedding <=> $2::vector) AS similarity
                FROM public.session_summaries
                WHERE user_id = $1
                  AND ($3::text[] IS NULL OR safety_level != ALL($3::text[]))
                ORDER BY embedding <=> $2::vector
                LIMIT $4
                """,
                user_id, vector_str, excluded or None, top_k,
            )
            return [dict(r) for r in rows]
