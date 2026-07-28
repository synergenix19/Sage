"""Node 6: knowledge_retrieve — RAG retrieval for info_request intent.

Fires when skill_select routes here: intent == info_request and no active skill.
Distinct from the knowledge_lookup tool (which fires mid-protocol inside freeflow_respond).
Both paths use PostgresKnowledgeRepository — invocation path differs, not retrieval logic.

Psychoed integration (Phase 2 Task 10; flag-gated by config.PSYCHOED_PATHWAYS_ENABLED,
default OFF -> node body below is byte-identical to pre-Task-10 behavior):
  - outcome-1: skill_select already resolved a `psychoed_serve` payload (deterministic
    trigger hit). The store is authoritative and in-process, so repo.retrieve() is never
    called -- no DB round trip for ratified copy that's already loaded in memory.
  - menu-after-weave passthrough: a clear-negative PSY-WEAVE-1 reply with no new trigger
    (skill_match_method == "psychoed_menu_after_weave") gets the same no-DB shape; there is
    no payload to enrich or append from.
  - outcome-2 (semantic backstop): normal retrieval ran (no psychoed_serve was set) and the
    TOP passage's source_id happens to be a psychoed block id -- the RAG corpus and the
    psychoed store can collide on ids because both were seeded from the same source
    articles. Rather than let a psychoed article surface as an anonymous RAG passage, this
    builds a fail-to-personal backstop serve payload for it (classifiers.FRAMING_FALLBACK).
  - L4 quarantine: regardless of which outcome fired (or neither), any passage whose
    source_id is a known psychoed block id is stripped from knowledge_passages. This is
    the actual safety property -- ratified psychoed copy must never reach LLM synthesis
    as an uncontrolled RAG passage; the backstop above is a courtesy upgrade (serve it
    properly instead of just deleting it), not a substitute for the quarantine.
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


def _psychoed_family(store_mod, category: str, block_id: str | None) -> str | None:
    """Family-exposure key for a psychoed_serve payload (outcome-1 and outcome-2 backstop).

    When a specific block was served, use ITS OWN article_family (precise -- reflects the
    content actually shown to the user this turn). When no block was served yet (a
    menu-first hit, block_id=None -- only the framing + menu offer went out, no article
    content), fall back to the category's first manifest block's family, so the exposure
    channel still records that this category's family was touched. Both branches resolve
    through store.family_of_kb_ref -- article_family is read from exactly one function,
    never duplicated inline (single-sourcing convention)."""
    bid = block_id or store_mod.manifest(category)["blocks"][0]
    return store_mod.family_of_kb_ref(bid)


async def knowledge_retrieve_node(state: SageState) -> dict:
    from sage_poc import config  # noqa: PLC0415 — local import so monkeypatch.setattr(config, ...) takes effect
    path = (state.get("path") or []) + ["knowledge_retrieve"]

    if config.PSYCHOED_PATHWAYS_ENABLED:
        from sage_poc.psychoed import store as psy_store, classifiers as psy_cls  # noqa: PLC0415

        serve_payload = state.get("psychoed_serve")
        if serve_payload:
            block_id = serve_payload.get("block_id")
            category = serve_payload["category"]
            payload = {**serve_payload}
            if block_id:
                payload["content_hash"] = psy_store.block_sha256(block_id)
            family = _psychoed_family(psy_store, category, block_id)
            _log.info(
                "[knowledge_retrieve] outcome-1 store fetch: category=%s block_id=%s (no DB call)",
                category, block_id,
            )
            return {
                "psychoed_serve": payload,
                "psychoed_blocks_served": (state.get("psychoed_blocks_served") or [])
                + ([block_id] if block_id else []),
                "psychoed_family_exposures": (state.get("psychoed_family_exposures") or []) + [family],
                "knowledge_passages": [],
                "knowledge_abstain": False,
                "knowledge_source": "psychoed_store",
                "path": path,
            }

        if state.get("skill_match_method") == "psychoed_menu_after_weave":
            _log.info("[knowledge_retrieve] menu-after-weave passthrough (no DB call)")
            return {
                "knowledge_passages": [],
                "knowledge_abstain": False,
                "knowledge_source": "psychoed_store",
                "path": path,
            }

    pool = _get_pool()

    if pool is None:
        _log.warning("[knowledge_retrieve] DB pool unavailable, returning abstain")
        return {
            "knowledge_passages": [],
            "knowledge_abstain": True,
            "knowledge_source": "node_6",
            "path": path,
        }

    lang = state.get("detected_language", "en")
    # Use original text for Arabic FTS matching; translated text for English.
    query = state.get("raw_message", "") if lang == "ar" else state.get("message_en", "")

    repo = PostgresKnowledgeRepository(pool)
    result = await repo.retrieve(query, language=lang, top_k=5)
    passages = [p.to_dict() for p in result.passages]

    extra: dict = {}
    if config.PSYCHOED_PATHWAYS_ENABLED:
        from sage_poc.psychoed import store as psy_store, classifiers as psy_cls  # noqa: PLC0415

        block_ids = psy_store.block_ids()

        # Outcome-2: semantic backstop, fail-to-personal (spec §2.2).
        if not result.abstain and passages and passages[0]["source_id"] in block_ids:
            article_id = passages[0]["source_id"]
            category = psy_store.category_of(article_id)
            manifest = psy_store.manifest(category)
            weave_due = bool(manifest.get("safety_weave")) and not state.get("psychoed_weave_fired")
            backstop_payload = {
                "category": category,
                "block_id": article_id,
                "route": "standard",
                "framing": psy_cls.FRAMING_FALLBACK,
                "weave_due": weave_due,
                "matched_row_id": None,
                "collision_path": "semantic_backstop",
                "content_hash": psy_store.block_sha256(article_id),
            }
            family = _psychoed_family(psy_store, category, article_id)
            _log.info(
                "[knowledge_retrieve] outcome-2 semantic backstop fired: category=%s block_id=%s",
                category, article_id,
            )
            extra = {
                "psychoed_serve": backstop_payload,
                "psychoed_active_category": category,
                "psychoed_delivery_shape": "answer_first",
                "psychoed_matched_row_id": None,
                "psychoed_collision_path": "semantic_backstop",
                "psychoed_framing": psy_cls.FRAMING_FALLBACK,
                "psychoed_weave_pending": weave_due,
                "psychoed_weave_fired": weave_due or bool(state.get("psychoed_weave_fired", False)),
                "psychoed_blocks_served": (state.get("psychoed_blocks_served") or []) + [article_id],
                "psychoed_family_exposures": (state.get("psychoed_family_exposures") or []) + [family],
            }

        # L4 quarantine: ratified psychoed copy must never enter LLM synthesis via
        # knowledge_passages, whether or not the backstop above fired for it.
        quarantined = [p for p in passages if p["source_id"] not in block_ids]
        stripped_count = len(passages) - len(quarantined)
        if stripped_count:
            _log.info("[knowledge_retrieve] L4 quarantine: stripped %d psychoed passage(s)", stripped_count)
        passages = quarantined

    return {
        "knowledge_passages": passages,
        "knowledge_abstain": result.abstain,
        "knowledge_source": "node_6",
        "knowledge_query_raw": result.query_raw,
        "knowledge_query_searched": result.query_searched,
        "knowledge_top_similarity": result.top_similarity,
        "path": path,
        **extra,
    }
