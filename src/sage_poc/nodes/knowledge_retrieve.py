"""Node 6: knowledge_retrieve — RAG retrieval for info_request intent.

Fires when skill_select routes here: intent == info_request and no active skill.
Distinct from the knowledge_lookup tool (which fires mid-protocol inside freeflow_respond).
Both paths use PostgresKnowledgeRepository — invocation path differs, not retrieval logic.
"""
from __future__ import annotations
import logging
from sage_poc.state import SageState
from sage_poc.knowledge.postgres_repository import PostgresKnowledgeRepository

_log = logging.getLogger(__name__)


def _get_pool():
    """Return the DB pool from the running server app, or None if unavailable."""
    try:
        from server import app  # noqa: PLC0415
        return getattr(app.state, "_db_pool", None)
    except Exception:
        return None


async def knowledge_retrieve_node(state: SageState) -> dict:
    pool = _get_pool()
    path = (state.get("path") or []) + ["knowledge_retrieve"]

    if pool is None:
        _log.warning("[knowledge_retrieve] DB pool unavailable, returning abstain")
        return {
            "knowledge_passages": [],
            "knowledge_abstain": True,
            "knowledge_source": "node_6",
            "path": path,
        }

    lang = state.get("detected_language", "en")
    # Phase-2 T4 (DORMANT): on a containment turn the directive seeds the FAMILY psychoeducation
    # article by kb_topics, not the user's message — a contain turn must serve the clinician-approved
    # article, not whatever the message happens to retrieve. containment_directive is None until a
    # family declares contain (T4), so this branch is inert and the retrieval below is unchanged.
    directive = state.get("containment_directive")
    if directive and directive.get("kb_topics"):
        query = " ".join(directive["kb_topics"])
        _log.info("[knowledge_retrieve] containment seed: kb_topics=%s", directive["kb_topics"])
    else:
        # Use original text for Arabic FTS matching; translated text for English.
        query = state.get("raw_message", "") if lang == "ar" else state.get("message_en", "")

    repo = PostgresKnowledgeRepository(pool)
    result = await repo.retrieve(query, language=lang, top_k=5)

    return {
        "knowledge_passages": [p.to_dict() for p in result.passages],
        "knowledge_abstain": result.abstain,
        "knowledge_source": "node_6",
        "knowledge_query_raw": result.query_raw,
        "knowledge_query_searched": result.query_searched,
        "knowledge_top_similarity": result.top_similarity,
        "path": path,
    }
