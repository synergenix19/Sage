from __future__ import annotations

import asyncio
import logging
import threading

import numpy as np

from sage_poc.state import SageState
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill
from sage_poc.resilience import EMBEDDING_TIMEOUT_SECONDS
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

logger = logging.getLogger(__name__)

_BGE_M3_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"

_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

# Calibrated 2026-05-27 post-audit-fix (v7 sprint + 13-item audit remediation).
# Architecture: gap test is cross-cluster only. Within-cluster somatic_distress overlap
# is expected and handled by Tier 1 keyword rules. See calibrate_threshold.py.
# Gap = 0.0533 (lowest cross-cluster hit=0.4856, highest off-topic miss=0.4323).
# Threshold = 0.4593 (recalibrated 2026-06-07 after BA/PD keyword re-bucketing).
# Gap = 0.0526 (lowest hit 0.4856, highest off-topic miss 0.4330). Re-run
# scripts/calibrate_threshold.py after any semantic_description or keyword edit.
SEMANTIC_THRESHOLD: float = 0.4593

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
            try:
                model = SentenceTransformer(
                    "BAAI/bge-m3",
                    local_files_only=True,
                    revision=_BGE_M3_REVISION,
                )
            except (OSError, EnvironmentError):
                model = SentenceTransformer("BAAI/bge-m3", revision=_BGE_M3_REVISION)
        ids, texts = [], []
        for sid, skill in _SKILLS.items():
            if sid in KEYWORD_SEMANTIC_SKIP:
                continue
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
    # Info requests go directly to knowledge_retrieve. If a skill is currently active,
    # don't clear active_skill_id — the executor exclusively owns that field's lifecycle.
    # Preserving it lets _route_after_skill_select still reach knowledge_retrieve while
    # keeping the skill alive for the turn that follows.
    if state.get("primary_intent") == "info_request":
        result: dict = {
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }
        if not state.get("active_skill_id"):
            result["active_skill_id"] = None
            result["active_step_id"] = None
        return result

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

    # Psychotic disclosure auto-select: fires when CF-006 flag is active AND referral not yet delivered.
    # Post-crisis auto-select above takes precedence.
    # delivered guard prevents re-selection loop (flag_immutable_within_session keeps the flag
    # for the full session; without this guard, psychotic_referral would re-select every turn).
    if (
        "psychotic_disclosure" in (state.get("clinical_flags") or [])
        and not state.get("psychotic_referral_delivered")
    ):
        skill_id = "psychotic_referral"
        skill = _SKILLS[skill_id]
        return {
            "active_skill_id": skill_id,
            "active_step_id": skill.steps[0].step_id,
            "skill_match_method": "psychotic_disclosure_auto_select",
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }

    message_en = state["message_en"].lower()
    raw_message = (state.get("raw_message") or "").lower()
    detected_language = state.get("detected_language") or "en"

    # Tier 1: Keyword matching — synchronous, deterministic, fast.
    # For Arabic sessions, also match against raw_message: Arabic-script keywords
    # cannot match a translated English string.
    # Stopgap: proper fix is language-tagged rules in Rules Service (backlog R1).
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            kw_lower = keyword.lower()
            if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
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
