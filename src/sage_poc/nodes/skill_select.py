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

# Calibrated 2026-05-27 post-audit-fix (v7 sprint + 13-item audit remediation).
# Architecture: gap test is cross-cluster only. Within-cluster somatic_distress overlap
# is expected and handled by Tier 1 keyword rules. See calibrate_threshold.py.
# Gap = 0.0533 (lowest cross-cluster hit=0.4856, highest off-topic miss=0.4323).
# Threshold = midpoint = 0.459. Re-run scripts/calibrate_threshold.py after any
# semantic_description or keyword edit.
SEMANTIC_THRESHOLD: float = 0.459

_embed_model = None
_semantic_skill_ids: list[str] = []
_semantic_embeddings: np.ndarray | None = None
_init_lock = threading.Lock()


def _ensure_semantic_ready() -> None:
    """Load BGE-M3 and embed all skill descriptions. No-op when both model and embeddings are ready."""
    global _embed_model, _semantic_skill_ids, _semantic_embeddings
    if _embed_model is not None and _semantic_embeddings is not None:
        return
    with _init_lock:
        if _embed_model is not None and _semantic_embeddings is not None:
            return
        model = _embed_model  # reuse resident model if available (avoids ANE recompilation)
        if model is None:
            from sentence_transformers import SentenceTransformer
            _REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
            try:
                model = SentenceTransformer(
                    "BAAI/bge-m3",
                    local_files_only=True,
                    revision=_REVISION,
                )
            except (OSError, EnvironmentError):
                model = SentenceTransformer("BAAI/bge-m3", revision=_REVISION)
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
    # Info requests always go directly to knowledge_retrieve, even during crisis monitoring.
    # A user in post-crisis check-in asking for a phone number or resource must be served.
    if state.get("primary_intent") == "info_request":
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }

    # Post-crisis auto-select bypasses keyword and semantic matching
    if state.get("crisis_state") == "monitoring":
        skill_id = "post_crisis_check_in"
        base = {
            "active_skill_id": skill_id,
            "skill_match_method": "post_crisis_auto_select",
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }
        # Guard: if the check-in is already active, pass through to executor without
        # re-initialising. Prevents step regression when active_skill_id is cleared
        # mid-check-in by a blended intent, low-confidence path.
        if state.get("active_skill_id") == skill_id:
            return {**base, "active_step_id": state.get("active_step_id")}
        # Not yet active — start from step 1.
        skill = _SKILLS[skill_id]
        return {**base, "active_step_id": skill.steps[0].step_id}

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
