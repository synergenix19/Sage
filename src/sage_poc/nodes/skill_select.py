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
_CLUSTER_ARGMAX_FLOOR: float = 0.42   # sub-threshold floor for within-cluster argmax
_RERANK_MARGIN: float = 0.05          # invoke reranker when top-2 scores are within this margin
_RERANK_TOP_K: int = 3                # max candidates passed to reranker

_embed_model = None
_anchor_skill_ids: list[str] = []    # one entry per anchor (description or semantic_anchors item)
_anchor_embeddings: np.ndarray | None = None  # shape (n_anchors, 1024)
_init_lock = threading.Lock()


def _ensure_semantic_ready() -> None:
    """Load BGE-M3 and embed all skill descriptions + semantic_anchors. No-op when ready."""
    global _embed_model, _anchor_skill_ids, _anchor_embeddings
    if _embed_model is not None and _anchor_embeddings is not None:
        return
    with _init_lock:
        if _embed_model is not None and _anchor_embeddings is not None:
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

        pairs: list[tuple[str, str]] = []
        for sid, skill in _SKILLS.items():
            if sid in KEYWORD_SEMANTIC_SKIP:
                continue
            if skill.semantic_description:
                pairs.append((sid, skill.semantic_description))
            for anchor in skill.semantic_anchors:
                pairs.append((sid, anchor))

        _anchor_skill_ids = [sid for sid, _ in pairs]
        anchor_texts = [text for _, text in pairs]
        _anchor_embeddings = model.encode(anchor_texts, normalize_embeddings=True)
        _embed_model = model  # assign last so the outer guard only passes after full init


def _skill_cluster(skill_id: str) -> str | None:
    from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
    for cluster, skills in CLINICAL_CLUSTERS.items():
        if skill_id in skills:
            return cluster
    return None


def _semantic_match_sync(
    message_en: str,
    profile_context: str = "",
) -> tuple[str | None, float]:
    """Max-over-anchors matching with cluster argmax, state-in-query, and rerank margin guard.

    Each skill contributes one score: the max cosine similarity across its semantic_description
    and all semantic_anchors entries. Cluster argmax: when top-2 share a cluster and the second
    score exceeds _CLUSTER_ARGMAX_FLOOR, routes by argmax rather than absolute threshold
    (useful for within-cluster disambiguation below SEMANTIC_THRESHOLD). For cross-cluster
    decisions above threshold where top-2 are within _RERANK_MARGIN, routes to rerank_candidates.
    """
    _ensure_semantic_ready()
    if _anchor_embeddings is None or not message_en.strip():
        return None, 0.0

    query_text = f"{profile_context}\n{message_en}".strip() if profile_context else message_en
    msg_emb = _embed_model.encode([query_text], normalize_embeddings=True)[0]
    raw_scores = np.dot(_anchor_embeddings, msg_emb)

    skill_scores: dict[str, float] = {}
    for i, sid in enumerate(_anchor_skill_ids):
        score = float(raw_scores[i])
        if score > skill_scores.get(sid, 0.0):
            skill_scores[sid] = score

    if not skill_scores:
        return None, 0.0

    ranked = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
    best_sid, best_score = ranked[0]

    # Within-cluster argmax: when top-2 share a clinical cluster and the second exceeds
    # the soft floor, trust relative ordering rather than absolute threshold gating.
    if len(ranked) >= 2:
        second_sid, second_score = ranked[1]
        if second_score >= _CLUSTER_ARGMAX_FLOOR:
            best_cluster = _skill_cluster(best_sid)
            if best_cluster is not None and best_cluster == _skill_cluster(second_sid):
                return best_sid, best_score

    # Absolute threshold gate — cross-cluster or single-cluster without argmax floor
    above = [(sid, score) for sid, score in ranked if score >= SEMANTIC_THRESHOLD]
    if len(above) == 1:
        return above[0]
    if len(above) >= 2:
        if above[0][1] - above[1][1] < _RERANK_MARGIN:
            from sage_poc.nodes.skill_rerank import rerank_candidates
            return rerank_candidates(message_en, above[:_RERANK_TOP_K])
        return above[0]

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
    _matched_skill_ids: set[str] = set()
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            kw_lower = keyword.lower()
            if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
                _matched_skill_ids.add(skill_id)
                if _best_kw is None or len(kw_lower) > _best_kw[1]:
                    _best_kw = (skill_id, len(kw_lower))

    # C1 acute-overlap tiebreak (clinical sign-off 2026-06-13). When BOTH grounding_5_4_3_2_1
    # and dbt_tipp keyword-match, prefer grounding for ambiguous overwhelm: it is the
    # contraindication-free, lower-activation skill, and under autonomous (unscreened) delivery
    # the lower-medical-risk default. This adjudicates ONLY this one clinically-reviewed overlap:
    # it fires only when dbt_tipp would otherwise be the longest-match winner, so SF-1
    # longest-match is preserved for every other skill pair, and a genuinely third skill with a
    # longer keyword still wins. "i can't calm down" matches dbt_tipp ONLY, so it is unaffected.
    # See docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md
    if (
        _best_kw is not None
        and _best_kw[0] == "dbt_tipp"
        and {"grounding_5_4_3_2_1", "dbt_tipp"} <= _matched_skill_ids
    ):
        _best_kw = ("grounding_5_4_3_2_1", _best_kw[1])

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

    # Tier 2: Multi-vector semantic with optional profile context
    profile = state.get("therapeutic_profile") or {}
    profile_context = (
        profile.get("summary", "") or "" if isinstance(profile, dict) else ""
    )
    try:
        semantic_skill, score = await asyncio.wait_for(
            asyncio.to_thread(_semantic_match_sync, state["message_en"], profile_context),
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
