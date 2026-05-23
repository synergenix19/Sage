"""Cross-session episodic retrieval helper (Task 3.3).

Retrieves prior session summaries relevant to the current user query,
excluding crisis-flagged sessions.  Returns a formatted context block
suitable for injection into a prompt, or an empty string when no
sufficiently-similar history exists.
"""
from __future__ import annotations

from sage_poc.memory.embedding import get_embedding_async
from sage_poc.memory.repository import MemoryRepository

_SIMILARITY_THRESHOLD = 0.6


async def retrieve_prior_context(
    user_id: str,
    query: str,
    repo: MemoryRepository,
    top_k: int = 3,
) -> str:
    """Return formatted prior-session context for *user_id* matching *query*.

    Crisis sessions are always excluded from retrieval.
    Results below the 0.6 cosine-similarity threshold are discarded.
    Returns an empty string when no qualifying history is found.
    """
    query_embedding: list[float] = await get_embedding_async(query)

    results: list[dict] = await repo.search_session_summaries(
        user_id,
        query_embedding,
        top_k=top_k,
        exclude_safety_levels=["crisis"],
    )

    qualifying = [r for r in results if r["similarity"] >= _SIMILARITY_THRESHOLD]

    if not qualifying:
        return ""

    lines = [
        f"[Session {i + 1}]: {r['summary_text']}"
        for i, r in enumerate(qualifying)
    ]
    return "Prior session context:\n" + "\n".join(lines)
