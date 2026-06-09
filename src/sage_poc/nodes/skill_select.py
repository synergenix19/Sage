from __future__ import annotations

import asyncio
import logging
import re
import threading

import numpy as np

from sage_poc.state import SageState
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill
from sage_poc.resilience import EMBEDDING_TIMEOUT_SECONDS
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP, SEMANTIC_EXCLUSION_WORDS

logger = logging.getLogger(__name__)

_BGE_M3_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"

_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

# Compiled word-boundary pattern for SEMANTIC_EXCLUSION_WORDS. Fires after Tier 1
# keyword matching and before BGE-M3 Tier 2. See corpus_constants.py for rationale.
_SEMANTIC_EXCLUSION_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(SEMANTIC_EXCLUSION_WORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Calibrated 2026-05-27 post-audit-fix (v7 sprint + 13-item audit remediation).
# Architecture: gap test is cross-cluster only. Within-cluster somatic_distress overlap
# is expected and handled by Tier 1 keyword rules. See calibrate_threshold.py.
# Gap = 0.0526 (lowest cross-cluster hit=0.4856, highest off-topic miss=0.4330). Re-run
# scripts/calibrate_threshold.py after any semantic_description or keyword edit.
# Recalibrated 2026-06-07 after BA/PD keyword re-bucketing: 0.4593.
# Appetite-loss FP (2026-06-08) resolved by SEMANTIC_EXCLUSION_WORDS guard above,
# not threshold movement. Do not raise threshold into the somatic noise band (0.46-0.47).
SEMANTIC_THRESHOLD: float = 0.4593
_RERANK_MARGIN: float = 0.05   # invoke reranker when top-2 scores are within this margin
_RERANK_TOP_K: int = 3         # max candidates passed to reranker

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


def _semantic_match_sync(
    message_en: str,
    profile_context: str = "",
) -> tuple[str | None, float]:
    """Cosine similarity against all skill semantic_descriptions. Runs in thread.

    When multiple skills score above SEMANTIC_THRESHOLD and their top-2 scores
    are within _RERANK_MARGIN, routes through rerank_candidates for disambiguation.
    The current stub returns the top candidate unmodified; Falcon-3B plugs in later.
    """
    _ensure_semantic_ready()
    if _semantic_embeddings is None or not message_en.strip():
        return None, 0.0
    msg_emb = _embed_model.encode([message_en], normalize_embeddings=True)[0]
    scores = np.dot(_semantic_embeddings, msg_emb)
    ranked = sorted(
        zip(_semantic_skill_ids, (float(s) for s in scores)),
        key=lambda x: x[1],
        reverse=True,
    )

    above = [(sid, score) for sid, score in ranked if score >= SEMANTIC_THRESHOLD]

    if len(above) == 1:
        return above[0]

    if len(above) >= 2:
        if above[0][1] - above[1][1] < _RERANK_MARGIN:
            from sage_poc.nodes.skill_rerank import rerank_candidates
            return rerank_candidates(message_en, above[:_RERANK_TOP_K])
        return above[0]

    best_sid, best_score = ranked[0]
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

    # Tier 1: Best-match keyword scoring — synchronous, deterministic, fast.
    # Collects ALL matches across all skills; returns the skill whose matched keyword
    # is longest (most specific). Fixes SF-1: eliminates registry-order-as-tiebreaker
    # dominant-shadower failures where a short keyword in a low-index skill blocked a
    # longer, more-specific keyword in a high-index skill from ever being reached.
    # For Arabic sessions, also match against raw_message (Arabic-script keywords
    # cannot match a translated English string). Backlog R1: language-tagged rules.
    _best_kw: tuple[str, int] | None = None  # (skill_id, keyword_length)
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            kw_lower = keyword.lower()
            if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
                if _best_kw is None or len(kw_lower) > _best_kw[1]:
                    _best_kw = (skill_id, len(kw_lower))

    if _best_kw is not None:
        t1_skill_id = _best_kw[0]
        t1_skill = _SKILLS[t1_skill_id]
        return {
            "active_skill_id": t1_skill_id,
            "active_step_id": t1_skill.steps[0].step_id,
            "skill_match_method": "keyword",
            "semantic_score": None,
            "path": state["path"] + ["skill_select"],
        }

    # Pre-Tier-2 exclusion guard: words with no therapeutic skill match in this registry.
    # Prevents BGE-M3 from routing somatic/physiological disclosures (appetite loss, food
    # references) to semantically adjacent skills (box_breathing, grounding) via embedding
    # proximity. Short-circuits to freeflow so the LLM can explore empathically.
    # See corpus_constants.SEMANTIC_EXCLUSION_WORDS for the word list and rationale.
    if _SEMANTIC_EXCLUSION_RE.search(message_en):
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
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
