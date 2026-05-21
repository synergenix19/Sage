from __future__ import annotations

import numpy as np
from sage_poc.state import SageState
from sage_poc.skills.schema import load_skill

SKILL_REGISTRY = ["cbt_thought_record", "grounding_5_4_3_2_1", "sleep_hygiene"]
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

# Threshold from empirical calibration (Task 3).
SEMANTIC_THRESHOLD: float = 0.5253  # calibrated 2026-05-21 (Task D clean); gap=0.0131 (lowest hit 0.5345, highest miss 0.5214); prior 0.5235 used 2 contaminated KNOWN_HITS ('heart is pounding', 'spinning' now Tier 1) — re-run calibrate_threshold.py after any semantic_description or target_presentations edit

# Lazy semantic components — initialised on first semantic miss, not at import
_embed_model = None
_semantic_skill_ids: list[str] = []
_semantic_embeddings: np.ndarray | None = None


def _ensure_semantic_ready() -> None:
    """Load BGE-M3 and embed all skill descriptions. No-op on subsequent calls."""
    global _embed_model, _semantic_skill_ids, _semantic_embeddings
    if _embed_model is not None:
        return
    from sentence_transformers import SentenceTransformer
    _embed_model = SentenceTransformer("BAAI/bge-m3")
    ids, texts = [], []
    for sid, skill in _SKILLS.items():
        if skill.semantic_description:
            ids.append(sid)
            texts.append(skill.semantic_description)
    _semantic_skill_ids = ids
    _semantic_embeddings = _embed_model.encode(texts, normalize_embeddings=True)


def _semantic_match(message_en: str) -> tuple[str | None, float]:
    """Cosine similarity against all skill semantic_descriptions. Tier 2 fallback only."""
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


def skill_select_node(state: SageState) -> dict:
    message = state["message_en"].lower()

    # Tier 1: Keyword matching — deterministic, fast, auditable
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

    # Tier 2: Semantic fallback — fires only when keywords miss
    semantic_skill, score = _semantic_match(state["message_en"])
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
