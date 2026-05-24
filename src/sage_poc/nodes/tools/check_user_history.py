"""Pre-retrieval helper: fetch relevant prior session summaries before the LLM call.

Architecture deviation from v7 §6.5.3: the spec defines check_user_history as an
LLM-bound @tool that the LLM "can choose to call or not." This implementation
pre-retrieves deterministically because in a clinical system, missing therapeutic
context (the LLM skips the tool call) carries more risk than irrelevant injection.
The 0.6 similarity threshold guards against irrelevant injection.

NOT an LLM-bound tool. Called deterministically by freeflow_respond_node.
The LLM never decides whether to retrieve — it always does when user_id is present.

Attribution prefix is mandatory (Abby audit G1 fix):
every returned string starts with "In an earlier conversation, you mentioned".

Crisis summaries are excluded by default (Abby audit E4 fix):
summaries generated during crisis turns must not be surfaced without safety re-check.
"""
from __future__ import annotations
import logging

from sage_poc.memory.embedding import get_embedding_async

_log = logging.getLogger(__name__)
_ATTRIBUTION_PREFIX = "In an earlier conversation, you mentioned"
# Calibrated 2026-05-24 using scripts/calibrate_retrieval_threshold.py with BGE-M3.
# gap=0.0331 (lowest KNOWN_RELEVANT=0.5005, highest KNOWN_IRRELEVANT=0.4674).
# Decision: narrow gap (0.008 < 0.0331 ≤ 0.05) → max_irrelevant + gap*0.3 formula.
# Previous uncalibrated value was 0.6 — calibration revealed that 13 of 14 KNOWN_RELEVANT
# queries fell below 0.6, meaning prior context was almost never injected.
# Corpus note: "I have been feeling stressed out lately" was removed from KNOWN_IRRELEVANT
# because a general clinical distress query legitimately matches any clinical summary.
# Re-run scripts/calibrate_retrieval_threshold.py after summarise_history() prompt edits
# or embedding model changes.
_SIMILARITY_THRESHOLD = 0.4774
# v7 §5.6 budgets ~100 words for L5 (user context). 800 chars (~200 words) fits within
# that budget with room for the therapeutic profile summary alongside it. Three uncapped
# summaries at 300 words each would exceed the entire L0+L1+L2 prompt budget combined.
_MAX_PRIOR_CONTEXT_CHARS = 800


async def retrieve_prior_context(
    user_id: str,
    query: str,
    repo,  # MemoryRepository — passed explicitly, no circular import
    top_k: int = 3,
) -> str:
    """Return a formatted string of relevant prior session context, or empty string.

    Args:
        user_id: The authenticated user's UUID. Must be non-empty — caller is
                 responsible for validation. Empty string returns "" without a DB query.
        query:   Current user message (used as embedding query).
        repo:    MemoryRepository instance (injected by caller — no circular import).
        top_k:   Maximum number of prior sessions to retrieve.
    """
    if not user_id:
        return ""
    try:
        embedding = await get_embedding_async(query)
        results = await repo.search_session_summaries(
            user_id=user_id,
            query_embedding=embedding,
            top_k=top_k,
            exclude_safety_levels=["crisis"],
        )
    except Exception as exc:
        _log.warning("[check_user_history] retrieval failed: %s", exc)
        return ""

    lines = [
        f"{_ATTRIBUTION_PREFIX}: {r['summary_text']}"
        for r in results
        if r.get("similarity", 0) >= _SIMILARITY_THRESHOLD
    ]
    return "\n".join(lines)[:_MAX_PRIOR_CONTEXT_CHARS]
