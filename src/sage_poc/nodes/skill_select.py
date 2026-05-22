from __future__ import annotations

import asyncio
import logging
import threading

import numpy as np

from sage_poc.state import SageState
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill
from sage_poc.resilience import EMBEDDING_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

# Calibrated 2026-05-23 after adding 9 new skills to SKILL_REGISTRY (12 total).
# gap=0.0128 (lowest hit=0.5384, highest miss=0.5257). Narrow gap — threshold set
# conservatively at max_miss + gap*0.3 to bias toward false-positive avoidance.
# post_crisis_check_in semantic_description rewritten from generic "warm closure"
# language to dense clinical post-acute monitoring protocol — eliminated 0.5468
# false-positive score on "thanks, that really helped".
# Re-run scripts/calibrate_threshold.py after any semantic_description edit.
# NOTE: CBT semantic_description has inherent overlap with vague negative-affect
# language in BGE-M3 embedding space. Architectural defence: intent_route (Node 2)
# classifies vague openings as general_chat before they reach skill_select (Node 4).
SEMANTIC_THRESHOLD: float = 0.5295

_embed_model = None
_semantic_skill_ids: list[str] = []
_semantic_embeddings: np.ndarray | None = None
_init_lock = threading.Lock()


def _ensure_semantic_ready() -> None:
    """Load BGE-M3 and embed all skill descriptions. No-op after first call."""
    global _embed_model, _semantic_skill_ids, _semantic_embeddings
    if _embed_model is not None:
        return
    with _init_lock:
        if _embed_model is not None:  # re-check under lock: another thread may have loaded first
            return
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-m3")
        ids, texts = [], []
        for sid, skill in _SKILLS.items():
            if skill.semantic_description:
                ids.append(sid)
                texts.append(skill.semantic_description)
        _semantic_skill_ids = ids
        _semantic_embeddings = model.encode(texts, normalize_embeddings=True)
        _embed_model = model  # assign last so the outer guard only passes after full init


def _semantic_match_sync(message_en: str) -> tuple[str | None, float]:
    """Cosine similarity against all skill semantic_descriptions. Runs in thread."""
    _ensure_semantic_ready()
    if _semantic_embeddings is None or not message_en.strip():
        return None, 0.0
    msg_emb = _embed_model.encode([message_en], normalize_embeddings=True)[0]
    scores = np.dot(_semantic_embeddings, msg_emb)
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    if best_score >= SEMANTIC_THRESHOLD:
        return _semantic_skill_ids[best_idx], best_score
    return None, best_score


async def skill_select_node(state: SageState) -> dict:
    # Post-crisis auto-select bypasses keyword and semantic matching
    if state.get("crisis_state") == "monitoring":
        skill_id = "post_crisis_check_in"
        skill = _SKILLS[skill_id]
        current_step = (
            state.get("active_step_id")
            if state.get("active_skill_id") == skill_id
            else skill.steps[0].step_id
        )
        return {
            "active_skill_id": skill_id,
            "active_step_id": current_step,
            "skill_match_method": "post_crisis_auto_select",
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }

    message = state["message_en"].lower()

    # Tier 1: Keyword matching — synchronous, deterministic, fast
    for skill_id, skill in _SKILLS.items():
        for keyword in skill.target_presentations:
            if keyword.lower() in message:
                return {
                    "active_skill_id": skill_id,
                    "active_step_id": skill.steps[0].step_id,
                    "skill_match_method": "keyword",
                    "semantic_score": None,
                    "path": state["path"] + ["skill_select"],
                }

    # Tier 2: Semantic fallback — CPU inference on a separate thread with timeout
    try:
        semantic_skill, score = await asyncio.wait_for(
            asyncio.to_thread(_semantic_match_sync, state["message_en"]),
            timeout=EMBEDDING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            '{"event": "embedding_timeout", "skill_select_tier": "keyword_only", '
            '"timeout_s": %s}',
            EMBEDDING_TIMEOUT_SECONDS,
        )
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "embedding_timeout": True,
            "path": state["path"] + ["skill_select"],
        }

    if semantic_skill is not None:
        skill = _SKILLS[semantic_skill]
        return {
            "active_skill_id": semantic_skill,
            "active_step_id": skill.steps[0].step_id,
            "skill_match_method": "semantic",
            "semantic_score": round(score, 4),
            "path": state["path"] + ["skill_select"],
        }

    return {
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "path": state["path"] + ["skill_select"],
    }
