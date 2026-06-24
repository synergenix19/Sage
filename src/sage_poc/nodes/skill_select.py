from __future__ import annotations

import asyncio
import logging
import os
import re
import threading

import numpy as np

from sage_poc.state import SageState
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import load_skill
from sage_poc.resilience import EMBEDDING_TIMEOUT_SECONDS
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP, SEMANTIC_EXCLUSION_WORDS
from sage_poc.rules import engine as rules_engine
from sage_poc.config import (
    SKILL_RUNNER_UP_MIN, SKILL_RUNNER_UP_MARGIN,
)

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


def _select_runner_up(
    ranked: list[tuple[str, float]], best_sid: str, best_score: float
) -> tuple[str, float] | None:
    """Second offer candidate: the highest OTHER skill that is both strong
    (>= SKILL_RUNNER_UP_MIN) and close to the primary (within SKILL_RUNNER_UP_MARGIN).
    Returns None otherwise, so a weak/distant second skill is never offered (feedback #6)."""
    for sid, sc in ranked:
        if sid == best_sid:
            continue
        if sc >= SKILL_RUNNER_UP_MIN and (best_score - sc) <= SKILL_RUNNER_UP_MARGIN:
            return (sid, sc)
        # ranked is descending; once a candidate fails the min, none after it can pass
        return None
    return None


_embed_model = None
_anchor_skill_ids: list[str] = []    # one entry per anchor (description or semantic_anchors item)
_anchor_embeddings: np.ndarray | None = None  # shape (n_anchors, 1024)
_init_lock = threading.Lock()

# Retrieval-core flag (spec rev4). Default OFF — production routing is unchanged until
# the POC demonstrates the delta and we flip it deliberately.
SKILL_ROUTING_V2: bool = os.environ.get("SKILL_ROUTING_V2", "0") == "1"


def _v2_enabled() -> bool:
    """The retrieval-core flag, read DYNAMICALLY. Every calibrated-V2 behavior gates on this
    (not the import-time SKILL_ROUTING_V2 constant) so the byte-identical guard can toggle the
    flag per-test and a flip needs no module reload. The module constant is retained only for
    the warmup anchor build (read once at startup — the prod path)."""
    return os.environ.get("SKILL_ROUTING_V2", "0") == "1"


# Calibrated per-route/per-language threshold table (V2 behavior #1). None until a table fit by
# the §2 offline calibration on real held_out=False scores is loaded at warmup. While None (and
# always when the flag is off) the router uses the global SEMANTIC_THRESHOLD, so flag-on without
# a calibrated table is byte-identical to V1 too.
_THRESHOLD_TABLE = None


def routing_threshold(lang: str, route: str) -> float:
    """The operating threshold for one candidate route. Flag-off OR no calibrated table → the
    global SEMANTIC_THRESHOLD (byte-identical to V1). Flag-on with a table → the route's own
    (lang, route) τ; a route the calibration never saw falls back to global (the safe direction
    given the over-firing failure mode). Per-(lang, route) by construction — no stratum pooling."""
    if not _v2_enabled() or _THRESHOLD_TABLE is None:
        return SEMANTIC_THRESHOLD
    try:
        return _THRESHOLD_TABLE.threshold(lang, route)
    except KeyError:
        return SEMANTIC_THRESHOLD

# Referral/after-care pathways excluded as skill_select targets under v2, per the FROZEN
# A1 boundary (2026-06-23): reached via deterministic/clinical-state paths, not semantic match.
EXCLUDED_REFERRALS = ("psychotic_referral", "post_crisis_check_in")


def build_anchor_pairs(skills, *, include_exemplars: bool) -> list[tuple[str, str]]:
    """Build (skill_id, text) anchor pairs for the BGE-M3 semantic index.

    v1 (include_exemplars=False, current prod): each skill contributes its
    semantic_description + semantic_anchors. Behavior is unchanged.

    SKILL_ROUTING_V2 (include_exemplars=True): ALSO embed target_presentations as exemplar
    anchors (spec §6.1, "the change that does the real work"), and EXCLUDE the referral
    pathways from the index (frozen A1 boundary). max-over-anchors pooling is unchanged.
    """
    pairs: list[tuple[str, str]] = []
    for sid, skill in skills.items():
        if sid in KEYWORD_SEMANTIC_SKIP:
            continue
        if include_exemplars and sid in EXCLUDED_REFERRALS:
            continue
        if skill.semantic_description:
            pairs.append((sid, skill.semantic_description))
        for anchor in skill.semantic_anchors:
            pairs.append((sid, anchor))
        if include_exemplars:
            for tp in skill.target_presentations:
                pairs.append((sid, tp))
    return pairs


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

        pairs = build_anchor_pairs(_SKILLS, include_exemplars=SKILL_ROUTING_V2)

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


# Anchor-count debias strength (behavior #3, §6.1). Conservative + PRECAUTIONARY: shipped on the
# §3.4 pre-commit (anchor_count/FP correlation is insufficient_power at N=27), NOT validated to
# remove the bias at this scale. Mechanism = reweight (not cap); chosen here, spec left it open.
_ANCHOR_DEBIAS_LAMBDA: float = 0.01


_FLAG_DISPOSITIONS_CACHE: dict[str, str] | None = None


def _flag_dispositions() -> dict[str, str]:
    """flag_id -> declared skill_select_disposition, read BY REFERENCE from the canonical flag
    definitions (rules/data/safety/clinical_flag_patterns.json). The POLICY — which flags carry
    disposition "abstain" — is OWNED by the safety lane / crisis sprint, which declares it on the
    flag definitions; skill_select is a pure CONSUMER. A flag with no declared disposition is
    absent from this map and routes as V1 (the safe default). Cached after first load."""
    global _FLAG_DISPOSITIONS_CACHE
    if _FLAG_DISPOSITIONS_CACHE is None:
        import json
        import pathlib
        path = pathlib.Path(__file__).resolve().parent.parent / "rules/data/safety/clinical_flag_patterns.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, str] = {}
        for rule in data.get("rules", []):
            action = rule.get("action", {})
            fid, disp = action.get("flag_id"), action.get("skill_select_disposition")
            if fid and disp:
                out[fid] = disp
        _FLAG_DISPOSITIONS_CACHE = out
    return _FLAG_DISPOSITIONS_CACHE


def _anchor_counts() -> dict[str, int]:
    """How many index anchors each skill contributes (description + semantic_anchors [+ exemplars
    under v2]). The count that drives the max-over-anchors bias."""
    counts: dict[str, int] = {}
    for sid in _anchor_skill_ids:
        counts[sid] = counts.get(sid, 0) + 1
    return counts


def _apply_anchor_debias(
    skill_scores: dict[str, float],
    anchor_counts: dict[str, int],
) -> dict[str, float]:
    """Counter the max-over-anchors count bias (anchor-rich skills get more shots at a spurious
    high max). Subtract a small penalty monotonic in anchor count, normalized to the MINIMUM count
    so the least-anchored skill is unpenalized and only the RELATIVE advantage is removed. Equal
    counts → exact identity (no relative bias to remove). Called only under flag-on."""
    if not anchor_counts:
        return skill_scores
    min_n = min(anchor_counts.values())
    return {
        sid: score - _ANCHOR_DEBIAS_LAMBDA * float(np.log1p(anchor_counts.get(sid, min_n) - min_n))
        for sid, score in skill_scores.items()
    }


def _route_decision(
    ranked: list[tuple[str, float]],
    lang: str,
    message_en: str,
) -> tuple[str | None, float, tuple[str, float] | None]:
    """Map a ranked (skill_id, score) list to (best|None, best_score, runner_up): cluster-argmax
    tiebreak, the per-route absolute gate, rerank, and ABSTAIN. Flag-off = V1 exactly. Flag-on
    adds explicit ABSTAIN (behavior #2): the cluster-argmax floor no longer routes a winner that
    clears no threshold — it fires only ABOVE the winner's τ (the id_oos over-route fix), while an
    above-τ winner still gets the tiebreak (no in_scope collateral). ABSTAIN returns no runner-up."""
    best_sid, best_score = ranked[0]

    def _runner_up(best: str | None) -> tuple[str, float] | None:
        # RECONCILE: master's runner-up fix (offer-confidence floor: strong AND close to primary,
        # feedback #6) is the runner-up mechanism in BOTH flag states — it superseded behavior-#1's
        # per-route runner-up loop, which was minor (per-route τ still gates the PRIMARY route).
        # Keeping this call is what makes master's fix LIVE, not dead code (the reverse-direction
        # check the runner-up-blind stash-control can't see).
        if best is None:
            return None
        return _select_runner_up(ranked, best, best_score)

    # Within-cluster argmax: when top-2 share a clinical cluster and the second exceeds the soft
    # floor, trust relative ordering rather than absolute threshold gating.
    if len(ranked) >= 2:
        second_sid, second_score = ranked[1]
        if second_score >= _CLUSTER_ARGMAX_FLOOR:
            best_cluster = _skill_cluster(best_sid)
            if best_cluster is not None and best_cluster == _skill_cluster(second_sid):
                # V2 (behavior #2): the tiebreak fires only when the winner clears its own τ —
                # ABOVE threshold, never below (kills the below-τ over-route) — and an above-τ
                # winner still wins the tiebreak (preserves legit in_scope disambiguation).
                # Flag-off: V1's 0.42 floor routes the winner regardless of threshold.
                if not _v2_enabled() or best_score >= routing_threshold(lang, best_sid):
                    return best_sid, best_score, _runner_up(best_sid)

    # Absolute threshold gate — cross-cluster or single-cluster without argmax floor.
    # Per-route: each candidate is gated by ITS OWN (lang, route) τ (global flag-off). No pooling.
    above = [(sid, score) for sid, score in ranked if score >= routing_threshold(lang, sid)]
    if len(above) == 1:
        return above[0][0], above[0][1], _runner_up(above[0][0])
    if len(above) >= 2:
        if above[0][1] - above[1][1] < _RERANK_MARGIN:
            from sage_poc.nodes.skill_rerank import rerank_candidates
            best_sid_r, best_score_r = rerank_candidates(message_en, above[:_RERANK_TOP_K])
            return best_sid_r, best_score_r, _runner_up(best_sid_r)
        return above[0][0], above[0][1], _runner_up(above[0][0])

    return None, best_score, None  # ABSTAIN — no skill, no runner-up offer (pure freeflow)


def _semantic_match_with_runner_up(
    message_en: str,
    profile_context: str = "",
    lang: str = "en",
) -> tuple[str | None, float, tuple[str, float] | None]:
    """Max-over-anchors matching with cluster argmax, state-in-query, and rerank margin guard.

    Each skill contributes one score: the max cosine similarity across its semantic_description
    and all semantic_anchors entries. Cluster argmax: when top-2 share a cluster and the second
    score exceeds _CLUSTER_ARGMAX_FLOOR, routes by argmax rather than absolute threshold
    (useful for within-cluster disambiguation below SEMANTIC_THRESHOLD). For cross-cluster
    decisions above threshold where top-2 are within _RERANK_MARGIN, routes to rerank_candidates.

    Returns (best_skill_id, best_score, runner_up) where runner_up is the
    highest-scoring OTHER skill at/above SEMANTIC_THRESHOLD as (skill_id, score),
    or None. R1 uses the runner-up as the second offer candidate.
    """
    _ensure_semantic_ready()
    if _anchor_embeddings is None or not message_en.strip():
        return None, 0.0, None

    query_text = f"{profile_context}\n{message_en}".strip() if profile_context else message_en
    msg_emb = _embed_model.encode([query_text], normalize_embeddings=True)[0]
    raw_scores = np.dot(_anchor_embeddings, msg_emb)

    skill_scores: dict[str, float] = {}
    for i, sid in enumerate(_anchor_skill_ids):
        score = float(raw_scores[i])
        if score > skill_scores.get(sid, 0.0):
            skill_scores[sid] = score

    if not skill_scores:
        return None, 0.0, None

    # V2 behavior #3: anchor-count debias before ranking. Flag-off skips entirely (byte-identical).
    if _v2_enabled():
        skill_scores = _apply_anchor_debias(skill_scores, _anchor_counts())

    ranked = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
    # RECONCILE (master ↔ V2): _route_decision is the superset — flag-off reproduces master's
    # primary routing exactly, flag-on adds the four V2 behaviors. Master's runner-up fix
    # (_select_runner_up, offer-confidence floor) is kept LIVE inside _route_decision's _runner_up.
    return _route_decision(ranked, lang, message_en)


def _semantic_match_sync(message_en: str, profile_context: str = "") -> tuple[str | None, float]:
    """Back-compat 2-tuple wrapper around _semantic_match_with_runner_up."""
    best, score, _ = _semantic_match_with_runner_up(message_en, profile_context)
    return best, score


_FALLBACK_OFFER_ACTION = {"type": "offer", "max_offered": 2, "declined_scope": "session"}


def _resolve_entry(
    state: SageState,
    candidates: list[str],
    method: str,
    semantic_score: float | None,
) -> dict:
    """Ask the skill_matching rules how the primary candidate enters the
    conversation, then build the node result. candidates are ranked, NOT yet
    filtered by declined_skills: declined handling is the fired rule's decision
    (the acute rule substitutes within a pool via action.on_declined)."""
    # declined_skills updates on user decline are intent_route's responsibility (Task 8).
    primary = candidates[0]

    # Arabic-exclusion gate (2026-06-13): the R1 consent-offer flow is English-only
    # until S2-2 ships a tested Khaleeji accept path. The Arabic accept-parse is
    # audit-confirmed broken, so offering in Arabic would create an un-acceptable offer
    # (the consent-gate bypass this layer exists to prevent). Arabic-script sessions
    # therefore fall through to pre-R1 behavior: enter the first non-declined matched
    # skill directly, never produce an offer. When every candidate is declined (only
    # reachable in a mixed-language session that earlier declined an English offer),
    # fall through to the normal path below — which yields acute substitution or an
    # all_candidates_declined no-op, never an Arabic offer.
    detected_language = (state.get("detected_language") or "en").lower()
    if detected_language == "ar":
        declined_ar = set(state.get("declined_skills") or [])
        entry = next((c for c in candidates if c not in declined_ar), None)
        if entry is not None:
            skill = _SKILLS[entry]
            return {
                "active_skill_id": entry,
                "active_step_id": skill.steps[0].step_id,
                "skill_match_method": method,
                "semantic_score": semantic_score,
                "path": state["path"] + ["skill_select", "arabic_offer_excluded"],
            }

    eval_result = rules_engine.evaluate("skill_matching", {
        "matched_skill_id": primary,
        "emotional_intensity": state.get("emotional_intensity", 5),
    })
    if eval_result.fired:
        fired = eval_result.fired[0]
        action, rule_id = fired.action, fired.rule_id
    else:
        # No rules loaded: consent is the fail-safe default, never silent entry.
        action, rule_id = _FALLBACK_OFFER_ACTION, "fallback_offer"
        logger.warning("[skill_select] no skill_matching rule fired; defaulting to offer")

    declined = set(state.get("declined_skills") or [])
    audit_markers = ["skill_select", f"skill_matching_rule:{rule_id}"]

    if action["type"] == "enter_direct":
        if primary not in declined:
            skill = _SKILLS[primary]
            return {
                "active_skill_id": primary,
                "active_step_id": skill.steps[0].step_id,
                "skill_match_method": method,
                "semantic_score": semantic_score,
                "path": state["path"] + audit_markers,
            }
        # The matched acute skill was declined this session. on_declined decides:
        # substitute within a clinician-ordered pool, or (legacy/default) fall to consent.
        on_declined = action.get("on_declined", "offer")
        if on_declined == "substitute":
            pool = action.get("substitute_pool", [])  # deterministic order = data order (grounding-first)
            substitute = next(
                (s for s in pool if s not in declined and s in _SKILLS), None
            )
            if substitute is not None:
                skill = _SKILLS[substitute]
                return {
                    "active_skill_id": substitute,
                    "active_step_id": skill.steps[0].step_id,
                    "skill_match_method": method,
                    "semantic_score": semantic_score,
                    "path": state["path"] + audit_markers + ["acute_substitute_declined"],
                }
            # Whole pool declined — safety floor: enter the matched (declined) skill directly.
            skill = _SKILLS[primary]
            return {
                "active_skill_id": primary,
                "active_step_id": skill.steps[0].step_id,
                "skill_match_method": method,
                "semantic_score": semantic_score,
                "path": state["path"] + audit_markers + ["acute_safety_floor_all_declined"],
            }
        # on_declined == "offer" (legacy/default): consent fallback wins, and the audit
        # trail must say so, the fired rule's action and the action taken differ this turn.
        audit_markers.append("enter_direct_declined_fallback")

    offerable = [sid for sid in candidates if sid not in declined]
    offerable = offerable[: int(action.get("max_offered", 2))]
    if not offerable:
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "offer_count": 0,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + audit_markers + ["all_candidates_declined"],
        }
    return {
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": offerable,
        "offer_count": 1,
        "skill_match_method": f"{method}_offer",
        "semantic_score": semantic_score,
        "path": state["path"] + audit_markers + ["skill_offer_made"],
    }


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

    # R1: accepted offer promotion. Runs after all auto-select safety paths so
    # post-crisis and psychotic referral always take precedence over a stale offer.
    # stale_offer_clear is spread into every return downstream of the promotion
    # block: a local `state` rebind never reaches the LangGraph checkpoint, so an
    # unresolvable stale offer must be cleared via the node's RETURN dict or the
    # offer template re-renders every turn.
    stale_offer_clear: dict = {}
    offered = state.get("offered_skill_ids") or []
    if offered and state.get("offer_response") == "accept":
        chosen = state.get("offer_choice_skill_id")
        if chosen not in _SKILLS or chosen not in offered:
            chosen = next((sid for sid in offered if sid in _SKILLS), None)
        if chosen is not None:
            skill = _SKILLS[chosen]
            return {
                "active_skill_id": chosen,
                "active_step_id": skill.steps[0].step_id,
                "offered_skill_ids": None,
                "offer_count": 0,
                "skill_match_method": "offer_accept",
                "semantic_score": None,
                "path": state["path"] + ["skill_select", "offer_promoted"],
            }
        # Stale checkpoint after a skill rename: no offered id resolves to a known
        # skill. Clear the offer (via the returned dict, not a local rebind) and
        # fall through to normal matching.
        logger.warning(
            "[skill_select] accepted offer contains no known skill ids %s; "
            "clearing offer and re-matching", offered,
        )
        stale_offer_clear = {"offered_skill_ids": None}

    # V2 behavior #4: enforce the frozen ABSTAIN dispositions DECLARED on the flag definitions.
    # Pure consumer — the safety lane owns which flags carry skill_select_disposition "abstain"
    # (declared on clinical_flag_patterns.json by the crisis sprint); skill_select reads the field
    # and DEFERS (no skill) so a flagged crisis-adjacent disclosure is not routed to a self-help
    # skill, even one that would score above threshold. A flag with no declared disposition routes
    # as V1 (safe no-op). Does NOT detect crisis — acute crisis is Node 1's, intercepted upstream
    # (BC1). Flag-off: untouched.
    if _v2_enabled():
        _disp = _flag_dispositions()
        if any(_disp.get(f) == "abstain" for f in (state.get("clinical_flags") or [])):
            return {
                **stale_offer_clear,
                "active_skill_id": None,
                "active_step_id": None,
                "skill_match_method": None,
                "semantic_score": None,
                "path": state["path"] + ["skill_select", "clinical_flag_abstain"],
            }

    message_en = state["message_en"].lower()
    raw_message = (state.get("raw_message") or "").lower()
    detected_language = state.get("detected_language") or "en"

    # Tier 1: Best-match keyword scoring — synchronous, deterministic, fast.
    # Collects ALL matches across all skills, ranked by longest matched keyword
    # (most specific first). Keeps SF-1 semantics: eliminates registry-order-as-
    # tiebreaker dominant-shadower failures where a short keyword in a low-index
    # skill blocked a longer, more-specific keyword in a high-index skill from
    # ever being reached (stable sort preserves registry order on ties).
    # For Arabic sessions, also match against raw_message (Arabic-script keywords
    # cannot match a translated English string). Backlog R1: language-tagged rules.
    kw_matches: dict[str, int] = {}   # skill_id -> longest matched keyword length
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            kw_lower = keyword.lower()
            if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
                if len(kw_lower) > kw_matches.get(skill_id, 0):
                    kw_matches[skill_id] = len(kw_lower)

    if kw_matches:
        ranked_kw = sorted(kw_matches.items(), key=lambda x: x[1], reverse=True)
        candidates = [sid for sid, _ in ranked_kw]
        # C1 acute-overlap tiebreak (clinical sign-off 2026-06-13), ported into the R1 consent
        # model. When BOTH grounding_5_4_3_2_1 and dbt_tipp keyword-match, prefer grounding for
        # ambiguous overwhelm: contraindication-free, lower-activation, the lower-medical-risk
        # default under autonomous (unscreened) delivery. In the pre-R1 path this made grounding
        # the directly-entered skill; in the R1 path it makes grounding the PRIMARY candidate, so
        # _resolve_entry offers (or, on acute_direct_entry, enters) grounding first instead of
        # dbt_tipp. Fires only when dbt_tipp would otherwise lead the longest-match ranking, so
        # SF-1 longest-match is preserved for every other pair and a genuinely-longer third skill
        # still leads. "i can't calm down" matches dbt_tipp ONLY, so it is unaffected.
        # See docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md
        if (
            candidates and candidates[0] == "dbt_tipp"
            and {"grounding_5_4_3_2_1", "dbt_tipp"} <= kw_matches.keys()
        ):
            candidates.remove("grounding_5_4_3_2_1")
            candidates.insert(0, "grounding_5_4_3_2_1")
        # resolve result must win the merge: offer results set offered_skill_ids themselves
        return {**stale_offer_clear,
                **_resolve_entry(state, candidates, method="keyword", semantic_score=None)}

    # Pre-Tier-2 exclusion guard: words with no therapeutic skill match in this registry.
    # Prevents BGE-M3 from routing somatic/physiological disclosures (appetite loss, food
    # references) to semantically adjacent skills (box_breathing, grounding) via embedding
    # proximity. Short-circuits to freeflow so the LLM can explore empathically.
    # See corpus_constants.SEMANTIC_EXCLUSION_WORDS for the word list and rationale.
    if _SEMANTIC_EXCLUSION_RE.search(message_en):
        return {
            **stale_offer_clear,
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
        semantic_skill, score, runner_up = await asyncio.wait_for(
            asyncio.to_thread(_semantic_match_with_runner_up, state["message_en"], profile_context, detected_language),
            timeout=EMBEDDING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            '{"event": "embedding_timeout", "skill_select_tier": "keyword_only", '
            '"timeout_s": %s}',
            EMBEDDING_TIMEOUT_SECONDS,
        )
        return {
            **stale_offer_clear,
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "embedding_timeout": True,
            "path": state["path"] + ["skill_select"],
        }

    if semantic_skill is not None:
        candidates = [semantic_skill]
        if runner_up is not None and runner_up[0] != semantic_skill:
            candidates.append(runner_up[0])
        # resolve result must win the merge: offer results set offered_skill_ids themselves
        return {**stale_offer_clear,
                **_resolve_entry(state, candidates, method="semantic", semantic_score=round(score, 4))}

    return {
        **stale_offer_clear,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "path": state["path"] + ["skill_select"],
    }
