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
from sage_poc.skills.keyword_matcher import match_skill_keywords
from sage_poc.resilience import EMBEDDING_TIMEOUT_SECONDS
from sage_poc.observability import stage_timer
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP, SEMANTIC_EXCLUSION_WORDS
from sage_poc.skills.info_request_consult_set import INFO_REQUEST_SKILL_CONSULT_SET
from sage_poc.rules import engine as rules_engine
from sage_poc.config import (
    SKILL_RUNNER_UP_MIN, SKILL_RUNNER_UP_MARGIN, SKILL_OFFER_COOLDOWN_TURNS,
    SKILL_OFFER_COOLDOWN_ENABLED,
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


_FLAG_CONTAIN_CACHE: dict[str, dict] | None = None


def _flag_contain_params() -> dict[str, dict]:
    """flag_id -> containment params {family, flag_level, kb_topics, skill_id?} for flags whose
    skill_select_disposition is 'contain' (Phase-2 T2). Same by-reference read as _flag_dispositions;
    the safety lane OWNS which flags contain (declared on the flag action's `contain` object). EMPTY
    until a family declares it (T4) — so this is dormant/inert on master. skill_select is a pure consumer."""
    global _FLAG_CONTAIN_CACHE
    if _FLAG_CONTAIN_CACHE is None:
        import json
        import pathlib as _pl
        path = _pl.Path(__file__).resolve().parent.parent / "rules/data/safety/clinical_flag_patterns.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        out: dict[str, dict] = {}
        for rule in data.get("rules", []):
            action = rule.get("action", {})
            if action.get("skill_select_disposition") == "contain" and action.get("flag_id"):
                out[action["flag_id"]] = action.get("contain", {})
        _FLAG_CONTAIN_CACHE = out
    return _FLAG_CONTAIN_CACHE


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


_RERANK_K: int = 5                         # top-k bi-encoder candidates fed to the cross-encoder (offline-measured config)
_RERANK_TAU: dict | None = None            # {lang: global reranker-τ}, lazy-loaded from rerank_calibration.json


def _rerank_enabled() -> bool:
    """The §4.3 cross-encoder SELECTOR flag, read dynamically. Default OFF — gates the reranker
    pipeline so flag-off routing is byte-identical V1. Expects SKILL_ROUTING_V2 too (the exemplar
    +debias bi-encoder candidate set the offline gate measured)."""
    return os.environ.get("SKILL_RERANK_ENABLED", "0") == "1"


def _load_rerank_calibration() -> dict:
    """{lang: global reranker-τ} from rerank_calibration.json. The τ is the balanced operating point
    on RERANKER LOGITS (not bi-encoder), GLOBAL (not per-route — uniform cross-encoder confidence),
    full-data fit. A missing file/key → {} → every lang resolves to -inf (route top-1, inert)."""
    import json
    import pathlib
    try:
        data = json.loads((pathlib.Path(__file__).parent / "rerank_calibration.json").read_text())
        return {lang: float(tau) for lang, tau in data["rerank_tau"].items()}
    except (FileNotFoundError, KeyError, ValueError):
        return {}


def _rerank_tau(lang: str) -> float:
    """The GLOBAL reranker-τ operating point for `lang`, lazy-loaded into the slot the live path
    reads. A lang with no calibrated τ (e.g. AR pending native review) → -inf → routes top-1 (no
    ABSTAIN), so an uncalibrated language never gets a mis-scaled gate."""
    global _RERANK_TAU
    if _RERANK_TAU is None:
        _RERANK_TAU = _load_rerank_calibration()
    return _RERANK_TAU.get(lang, float("-inf"))


def _rerank_route(
    ranked: list[tuple[str, float]],
    lang: str,
    message_en: str,
    runner_up,
) -> tuple[str | None, float, tuple[str, float] | None]:
    """V2 selector pipeline, faithful to the offline-measured shape (62/90/100): bi-encoder top-k →
    cross-encoder re-score the k → GLOBAL reranker-τ → route-or-ABSTAIN. Supersedes the per-route /
    cluster-argmax decision (#1/#2) when the reranker is on. Runner-up via the same closure → master's
    _select_runner_up stays live."""
    topk = ranked[:_RERANK_K]
    if not topk:
        return None, 0.0, None
    from sage_poc.nodes.skill_rerank_model import score_pairs
    from sage_poc.skills.schema import load_skill
    bi_score = dict(ranked)
    pairs = [(message_en, load_skill(sid).semantic_description or sid) for sid, _ in topk]
    rr_scores = score_pairs(pairs)
    reranked = sorted(((sid, rr) for (sid, _), rr in zip(topk, rr_scores)), key=lambda x: -x[1])
    top_sid, top_rr = reranked[0]
    if top_rr >= _rerank_tau(lang):
        return top_sid, bi_score.get(top_sid, 0.0), runner_up(top_sid)
    return None, ranked[0][1], None  # ABSTAIN — below the reranker's confidence floor


def _keyword_rerank_veto(candidates: list[str], message: str, lang: str) -> bool:
    """True if the reranker would ABSTAIN on a keyword-Tier-1 route — i.e., NONE of the keyword-
    matched skills clears the reranker's confidence floor for this message. Catches the Tier-1
    bypass: a keyword false-match on a clinician-territory (id_oos) disclosure must not route past
    the reranker's ABSTAIN gate (the wired re-gate measured 7 such id_oos over-routes, id_oos
    90→76). A confident keyword in_scope match clears τ and is NOT vetoed."""
    if not candidates:
        return False
    from sage_poc.nodes.skill_rerank_model import score_pairs
    from sage_poc.skills.schema import load_skill
    cands = candidates[:_RERANK_K]
    scores = score_pairs([(message, load_skill(sid).semantic_description or sid) for sid in cands])
    return bool(scores) and max(scores) < _rerank_tau(lang)


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

    # V2 SELECTOR (commit 2): when the cross-encoder reranker is enabled, it re-scores the top-k
    # bi-encoder candidates and a GLOBAL reranker-τ gates route-or-ABSTAIN — the §4.3 selector,
    # the exact pipeline the offline gate measured (62/90/100). It supersedes the per-route /
    # cluster-argmax decision (#1/#2) below. Flag-off (default): this branch is never taken, so the
    # decision is byte-identical V1.
    if _rerank_enabled():
        return _rerank_route(ranked, lang, message_en, _runner_up)

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
    # EMBED-CACHE: reuse S3's query embedding when the same message_en was just encoded on the
    # safety path. float32 cast matches the uncached encode bit-for-bit, so routing is unchanged.
    from sage_poc.config import EMBED_CACHE_ENABLED  # noqa: PLC0415
    if EMBED_CACHE_ENABLED:
        from sage_poc.safety.s3_semantic import cached_get_embedding  # noqa: PLC0415
        msg_emb = np.array(cached_get_embedding(query_text), dtype=np.float32)
    else:
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


def _offer_cooldown_turns() -> int:
    """Return the cooldown window (in turns) after a skill offer is made.

    Reads cooldown_turns from the default_offer skill_matching rule so the value
    is clinician-ownable data. Falls back to config.SKILL_OFFER_COOLDOWN_TURNS
    when the rule is absent or the key is missing.
    """
    try:
        eval_result = rules_engine.evaluate("skill_matching", {
            "matched_skill_id": "__cooldown_probe__",
            "emotional_intensity": 5,
        })
        # default_offer (priority 99) fires for any unmatched skill_id; acute_direct_entry will
        # not fire because "__cooldown_probe__" is not in its matched_skill_in list.
        for fired in (eval_result.fired or []):
            if fired.rule_id == "default_offer":
                return int(fired.action.get("cooldown_turns", SKILL_OFFER_COOLDOWN_TURNS))
    except Exception:
        pass
    return SKILL_OFFER_COOLDOWN_TURNS


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
        "last_offer_turn": state.get("turn_count", 0),
        "skill_match_method": f"{method}_offer",
        "semantic_score": semantic_score,
        "path": state["path"] + audit_markers + ["skill_offer_made"],
    }


async def _consult_top_match(state: SageState) -> str | None:
    """Identify the single top-ranked skill for THIS message via the SAME Tier-1 keyword
    + Tier-2 semantic matching the non-info_request path below uses (match_skill_keywords,
    the C1 acute-overlap tiebreak, the reranker keyword-veto gated on SKILL_RERANK_ENABLED,
    the semantic exclusion guard, _semantic_match_with_runner_up) -- called via the exact
    same helpers, not reimplemented, so the two paths can never diverge on WHAT counts as a
    match. Returns None on any no-match / ABSTAIN / exclusion outcome; the info_request
    consult treats every such outcome as "no match" (fail-open input).

    Deliberately does NOT include the IPV coaching-confrontation filter or the offer/
    consent resolution (_resolve_entry) — the info_request branch runs BEFORE those
    checks are computed in skill_select_node today, and the consult's contract (design
    doc "Where the code changes") is SELECT the top match directly, not offer it.
    """
    message_en = state["message_en"].lower()
    raw_message = (state.get("raw_message") or "").lower()
    detected_language = state.get("detected_language") or "en"

    kw_matches: dict[str, int] = match_skill_keywords(message_en, raw_message, detected_language)
    if kw_matches:
        ranked_kw = sorted(kw_matches.items(), key=lambda x: x[1], reverse=True)
        candidates = [sid for sid, _ in ranked_kw]
        # C1 acute-overlap tiebreak (mirrors the non-info_request Tier-1 block below).
        if (
            candidates and candidates[0] == "dbt_tipp"
            and {"grounding_5_4_3_2_1", "dbt_tipp"} <= kw_matches.keys()
        ):
            candidates.remove("grounding_5_4_3_2_1")
            candidates.insert(0, "grounding_5_4_3_2_1")
        if _rerank_enabled() and _keyword_rerank_veto(candidates, state["message_en"], detected_language):
            return None
        return candidates[0]

    if _SEMANTIC_EXCLUSION_RE.search(message_en):
        return None

    profile = state.get("therapeutic_profile") or {}
    profile_context = profile.get("summary", "") or "" if isinstance(profile, dict) else ""
    try:
        semantic_skill, _score, _runner_up = await asyncio.wait_for(
            asyncio.to_thread(
                _semantic_match_with_runner_up, state["message_en"], profile_context, detected_language
            ),
            timeout=EMBEDDING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return None
    return semantic_skill


async def skill_select_node(state: SageState) -> dict:
    # #338 D1 ANSWER TURN: when this turn answers a pending screen (answering_screen was set by
    # consume_pending_screen at graph entry, only ever in enforce mode), classify + route the answer
    # DETERMINISTICALLY before any skill matching. The answer ("no, same as always") usually matches no
    # skill and would otherwise fall through to freeflow UNCLASSIFIED — the 2026-07-20 enforce-flip seam.
    # apply_screen_at_route reads answering_screen: clear_no resumes the held skill, disclosure/evaded ->
    # grounding, red_flag -> 998, crisis -> abandon. Flag-off never reaches here (answering_screen requires a
    # prior enforce-mode ask_screen), so this is byte-identical to master with the flag off.
    if state.get("answering_screen"):
        from sage_poc.safety.medical_screen import apply_screen_at_route  # noqa: PLC0415
        return apply_screen_at_route(state, {"active_skill_id": None, "offered_skill_ids": None,
                                             "skill_match_method": None, "semantic_score": None,
                                             "path": state["path"] + ["skill_select"]})
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
            # Psychoed Mechanism-A consult (2026-07-17 design doc): BEFORE force-routing to
            # knowledge_retrieve, consult the SAME keyword+semantic matching the
            # non-info_request path uses. A top match inside INFO_REQUEST_SKILL_CONSULT_SET
            # (the doc-derived disposition set -- see info_request_consult_set.py's axis
            # note) is SELECTED directly. This is a skill-matching CONSULT, not an intent
            # reclassification: primary_intent stays "info_request"; _route_after_skill_select
            # keys the skill_executor diversion on skill_match_method, not this intent. No
            # match, or a match outside the set (an experiential skill, e.g. box_breathing)
            # -> falls through to the KB-bound result below, UNCHANGED — fail-open by
            # construction (design doc Property 1), only reachable from a clean (no
            # pre-existing active skill) state so an incidental info_request mid-skill can
            # never hijack the active skill.
            #
            # KILL-SWITCH: config.INFO_REQUEST_CONSULT_ENABLED, default OFF. Local import
            # (not module-level) so monkeypatch.setattr(config, ...) in tests takes effect —
            # mirrors the psychotic_disclosure HR flag read further down this file. OFF skips
            # the matching call entirely: no keyword/semantic work runs, no skill is ever
            # selected via this path, result stays the KB-bound dict below — byte-identical
            # to the pre-consult info_request -> knowledge_retrieve behavior.
            from sage_poc import config  # noqa: PLC0415
            if config.INFO_REQUEST_CONSULT_ENABLED:
                top_match = await _consult_top_match(state)
                if top_match is not None and top_match in INFO_REQUEST_SKILL_CONSULT_SET:
                    skill = _SKILLS[top_match]
                    result["active_skill_id"] = top_match
                    result["active_step_id"] = skill.steps[0].step_id
                    result["skill_match_method"] = "info_request_skill_consult"
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
    #
    # HR-1 Stage 1 Task 3: hr_disclosure_present broadens this to mania_disclosure and
    # dissociation_disclosure (gated behind HIGH_RISK_DETECTION_ENABLED); psychotic_disclosure
    # always fires. skill_match_method stays "psychotic_disclosure_auto_select" for all three —
    # renaming is Stage 2 scope.
    from sage_poc import config  # noqa: PLC0415
    from sage_poc.safety.hr_disclosure import hr_disclosure_present  # noqa: PLC0415
    if (
        hr_disclosure_present(state.get("clinical_flags") or [], flag_enabled=config.HIGH_RISK_DETECTION_ENABLED)
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

    # E7 §6a IPV pre-emption (flag-gated SAGE_IPV_PREEMPTION). When domestic_situation is set, the §6
    # coaching_confrontation skills (assertive_communication, interpersonal_effectiveness) are
    # contraindicated — encouraging a boundary/assertiveness script in a genuinely unsafe dynamic can
    # increase risk (§6a guard). They are suppressed from BOTH offer-accept promotion and fresh
    # selection; the turn routes to freeflow, where the existing PI-CF-005 clinical adaptation surfaces
    # the safety-first framing + DFWAC/Ewaa referral. Scoped: only these skills — grounding/offload/
    # sleep stay available (don't punish disclosure). Senior to offer-accept + matching below,
    # subordinate to the crisis + psychotic auto-selects above. When the flag is OFF or there is no
    # domestic_situation, _ipv_active is False and every path below is byte-identical to v7.
    from sage_poc.nodes.ipv_preempt import (  # noqa: PLC0415
        COACHING_CONFRONTATION_SKILLS,
        ipv_preempt_active,
    )
    _ipv_active = ipv_preempt_active(state)

    def _ipv_suppressed_return(extra: dict | None = None) -> dict:
        return {
            **(extra or {}),
            "active_skill_id": None,
            "active_step_id": None,
            "offered_skill_ids": None,
            "offer_count": 0,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + ["skill_select", "ipv_preempt_suppressed"],
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
            # E7: a §6 offer accepted in the same turn the user discloses coercive control must NOT
            # promote — the safety referral wins over the engagement-layer accept (mirrors the
            # psychotic-referral-over-accept precedence). Route to freeflow + referral instead.
            if _ipv_active and chosen in COACHING_CONFRONTATION_SKILLS:
                return _ipv_suppressed_return(stale_offer_clear)
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

    # Harm-intrusive iatrogenic veto (deterministic, ARM-INDEPENDENT safety control; Stage 1 of the
    # Clinical Containment Pathway, docs/superpowers/plans/2026-07-08-clinical-containment-pathway.md,
    # mirroring the OCD-compulsion veto precedent; DEPLOY GATED ON CLINICIAN PATTERN SIGN-OFF). A
    # postpartum / parental EGO-DYSTONIC disclosure of intrusive images or thoughts of harming a baby or
    # child must NOT route to a self-help skill: worry, rumination, thought-record and grounding tools
    # REINFORCE the intrusive-thought cycle, so any such route is iatrogenic. ABSTAIN to Node 3
    # (low_confidence_respond) instead, the correct terminal for these cases today (Stage 1). Runs BEFORE
    # both routing tiers (keyword Tier 1 + semantic Tier 2) and is NOT gated on SKILL_ROUTING_V2, so V1
    # (the prod hotfix surface) and V2 behave identically. Subordinate to the crisis + psychotic
    # auto-selects above (active intent is CRISIS, intercepted at Node 1). Carries no user-facing text.
    from sage_poc.nodes.harm_intrusive import is_harm_intrusive  # noqa: PLC0415
    # LANGUAGE-CONTRACT DEBT (#330): still reads translated message_en, not raw. Left unchanged on
    # this branch — translation currently catches the AR ego-dystonic disclosure, and switching to
    # raw before AR patterns exist would REGRESS that coverage. Conformed to safety_text() when the
    # harm_intrusive AR-pattern ticket lands. Allowlisted in check_safety_reads_raw.py with #330.
    if is_harm_intrusive(state.get("message_en")):
        return {
            **stale_offer_clear,
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + ["skill_select", "harm_intrusive_veto"],
        }

    # OCD-compulsion iatrogenic veto (deterministic, ARM-INDEPENDENT safety control; approved
    # expedited hotfix, escalation 2026-07-07-v1-iatrogenic-ocd-routing-escalation.md). A disclosed
    # compulsion or ritual (checking, counting/magic/undoing, scrupulosity, rereading/redoing,
    # contamination/reassurance/symmetry) must NOT route to a self-help skill: worry, rumination,
    # thought-record and grounding tools REINFORCE compulsions, so any such route is iatrogenic.
    # ABSTAIN to Node 3 (low_confidence_respond) instead, the correct terminal for these cases.
    # Runs BEFORE both routing tiers (keyword Tier 1 + semantic Tier 2) and is NOT gated on
    # SKILL_ROUTING_V2, so V1 (the prod hotfix surface) and V2 behave identically. Subordinate to the
    # crisis + psychotic auto-selects above (a crisis still escalates). Carries no user-facing text.
    from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion  # noqa: PLC0415
    from sage_poc.state import safety_text  # noqa: PLC0415
    # Language contract (#330): read RAW input via safety_text(), not translated message_en — the
    # AR compulsion bypass was a translated-path detection drift. First consumer of the accessor.
    if is_ocd_compulsion(safety_text(state)):
        return {
            **stale_offer_clear,
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + ["skill_select", "ocd_compulsion_veto"],
            "abstain_referral": "ocd_erp",  # #218: Node-8 pins the ERP professional-referral signpost
        }

    # V2 behavior #4: enforce the frozen ABSTAIN dispositions DECLARED on the flag definitions.
    # Pure consumer — the safety lane owns which flags carry skill_select_disposition "abstain"
    # (declared on clinical_flag_patterns.json by the crisis sprint); skill_select reads the field
    # and DEFERS (no skill) so a flagged crisis-adjacent disclosure is not routed to a self-help
    # skill, even one that would score above threshold. A flag with no declared disposition routes
    # as V1 (safe no-op). Does NOT detect crisis — acute crisis is Node 1's, intercepted upstream
    # (BC1). Flag-off: untouched.
    # RECONCILE 2026-06-25: this clinical safety gate runs BEFORE the D3 cooldown block below, so a
    # crisis-adjacent disclosure DEFERS for the clinical reason (path "clinical_flag_abstain") rather
    # than being masked by a cooldown suppression. Both blocks are independent early-returns; order
    # picked so the safety reason owns the audit trail when both could fire.
    if _v2_enabled():
        _disp = _flag_dispositions()
        _flags_now = state.get("clinical_flags") or []
        # Phase-2 T2: contain SUPERSEDES abstain for families that declare it (design §2). Dormant
        # until a flag declares skill_select_disposition "contain" (T4); T3's edge routes on the
        # directive. Sets containment_directive; behavior-identical to master while no family declares it.
        _contain_flag = next((f for f in _flags_now if _disp.get(f) == "contain"), None)
        if _contain_flag:
            _cp = _flag_contain_params().get(_contain_flag, {})
            return {
                **stale_offer_clear,
                "active_skill_id": None,
                "active_step_id": None,
                "skill_match_method": None,
                "semantic_score": None,
                "containment_directive": {**_cp, "rule_id": _contain_flag},
                "path": state["path"] + ["skill_select", "clinical_flag_contain"],
            }
        if any(_disp.get(f) == "abstain" for f in _flags_now):
            return {
                **stale_offer_clear,
                "active_skill_id": None,
                "active_step_id": None,
                "skill_match_method": None,
                "semantic_score": None,
                "path": state["path"] + ["skill_select", "clinical_flag_abstain"],
            }

    # D3: offer cooldown. Suppress a fresh offer when the user received one within the
    # last cooldown_turns turns. Runs after the offer-accept promotion block so an
    # accepted or pending offer is never blocked, and stale_offer_clear is {} here in
    # the normal case (only populated on stale-rename, where clearing is correct).
    # G2 safe: cooldown never touches offered_skill_ids; a pending offer that was accepted
    # already returned above. The suppression routes to freeflow so the LLM can continue
    # the conversation naturally without re-presenting the skill menu.
    # GATED: behind SKILL_OFFER_COOLDOWN_ENABLED (default OFF). When off, behaviour is
    # byte-identical to pre-cooldown (the block is skipped entirely). The flip to ON is a
    # logged, signed decision gated on clinical sign-off C3 — not an auto-flip on merge.
    _cooldown = _offer_cooldown_turns()
    _last = state.get("last_offer_turn")
    if SKILL_OFFER_COOLDOWN_ENABLED and _last is not None and (state.get("turn_count", 0) - _last) < _cooldown:
        return {**stale_offer_clear, "active_skill_id": None, "active_step_id": None,
                "skill_match_method": None, "semantic_score": None,
                "path": state["path"] + ["skill_select", "offer_cooldown_suppressed"]}

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
    # Shared matcher (v7.2): the SAME helper the Node-2 keyword pre-pass uses, so the two nodes can
    # never diverge (single-sourced from skill JSON target_presentations). Identical logic to before.
    kw_matches: dict[str, int] = match_skill_keywords(message_en, raw_message, detected_language)

    if kw_matches:
        ranked_kw = sorted(kw_matches.items(), key=lambda x: x[1], reverse=True)
        candidates = [sid for sid, _ in ranked_kw]
        # E7: drop §6 coaching_confrontation skills from the candidate set. If they were the ONLY
        # matches (a §6-only request under an IPV disclosure), suppress -> freeflow + referral;
        # otherwise a non-§6 match still leads and is offered as normal (carve-out preserved).
        if _ipv_active:
            _filtered = [c for c in candidates if c not in COACHING_CONFRONTATION_SKILLS]
            if not _filtered:
                return _ipv_suppressed_return(stale_offer_clear)
            candidates = _filtered
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
        # V2 (wired-re-gate fix): gate keyword routes through the reranker's ABSTAIN too. A keyword
        # match the reranker won't endorse (clinician-territory false-match) must not bypass the
        # safety gate — without this, Tier-1 over-routes id_oos before the reranker can veto (id_oos
        # 90→76). Flag-off (reranker disabled): never runs -> keyword routing is byte-identical V1.
        if _rerank_enabled() and _keyword_rerank_veto(candidates, state["message_en"], detected_language):
            # Reranker vetoed a keyword match (safety-critical abstain producer) → Node 3, not freeflow.
            return {**stale_offer_clear, "active_skill_id": None, "active_step_id": None,
                    "skill_match_method": None, "semantic_score": None, "skill_select_abstained": True,
                    "path": state["path"] + ["skill_select", "keyword_rerank_veto"]}
        # resolve result must win the merge: offer results set offered_skill_ids themselves
        from sage_poc.safety.medical_screen import apply_screen_at_route  # noqa: PLC0415
        return apply_screen_at_route(state, {**stale_offer_clear,
                **_resolve_entry(state, candidates, method="keyword", semantic_score=None)})

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
        # RECONCILE 2026-06-25: master's log-only stage_timer (PR#77 latency instrumentation) wraps the
        # encode UNCHANGED (no effect on match output) AND V2's _semantic_match_with_runner_up takes the
        # detected_language 3rd arg (per-lang routing). Keep BOTH.
        with stage_timer(
            "skill_embed",
            session_id=state.get("session_id"),
            turn=state.get("turn_count"),
            lang=state.get("detected_language"),
        ):
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
        # E7: same §6 filter as the keyword tier — a semantic §6 match (with no non-§6 runner-up)
        # under an IPV disclosure suppresses to freeflow + referral; a non-§6 runner-up survives.
        if _ipv_active:
            _filtered = [c for c in candidates if c not in COACHING_CONFRONTATION_SKILLS]
            if not _filtered:
                return _ipv_suppressed_return(stale_offer_clear)
            candidates = _filtered
        # resolve result must win the merge: offer results set offered_skill_ids themselves
        from sage_poc.safety.medical_screen import apply_screen_at_route  # noqa: PLC0415
        # D1 screen (#338) — flag-gated, byte-identical when off; positioned AFTER the vetoes above, so the
        # supremacy chain holds (a veto turn returned earlier and never reaches here).
        return apply_screen_at_route(state, {**stale_offer_clear,
                **_resolve_entry(state, candidates, method="semantic", semantic_score=round(score, 4))})

    return {
        **stale_offer_clear,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        # Below-τ semantic ABSTAIN under V2 → Node 3 (Cardinal Rule 5). Flag-off: key absent → V1 freeflow.
        **({"skill_select_abstained": True} if _rerank_enabled() else {}),
        "path": state["path"] + ["skill_select"],
    }
