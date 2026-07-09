# ARCHITECTURE WARNING — SINGLE-LAYER SAFETY
#
# v7 spec §5.1 defines Layer 1 as OR-fusion: S1 (crisis lexicon) OR S2 (MARBERT
# classifier) OR S3 (semantic crisis embeddings) OR S6 (clinical flag escalation).
# Any layer catching a phrase is sufficient; the layers provide redundancy.
#
# CURRENT STATE: S1 (lexicon) + S3 (BGE-M3 semantic, advisory). S2 (MARBERT) not built.
#
# S3 STATUS (2026-06-05, scripts/s3_threshold_sweep.py, 75 CRADLE passive-SI cases):
#   ADVISORY ONLY — adds ZERO measured recall above S1 at any threshold from 0.65 to 0.8059.
#   At 0.8059 (deployed): 0 S3-only adds, 0 new FPs — a paraphrase-matcher for S1 at best.
#   At 0.70: 3 adds, 2 new FPs — worse than 1:1 tradeoff, not a viable operating point.
#   Missed passive-SI cluster sits at 0.62–0.72 cosine similarity, overlapping with
#   therapeutic acceptance language — BGE-M3 cannot separate them without context.
#   S3 remains on the crisis path and records s3_score in state for auditability.
#   Do NOT cite s3_semantic in crisis_flags as evidence of semantic coverage — the coverage
#   is not demonstrated by measurement. Genuine semantic coverage requires MARBERT (Exp 4.2).
#
# NEXT STEPS (priority order before feature expansion):
#   S2: off-the-shelf MARBERT binary classifier (crisis/not-crisis) — no fine-tuning
#       required for baseline coverage. Route Arabic text through MARBERT before
#       lexicon to catch dialectal expressions outside the keyword vocabulary.
#   Reference: CRISP-DM plan, Experiment 4.2.

import re
import asyncio
import logging
from sage_poc.state import SageState
from sage_poc.language import detect_language, async_translate_to_english
from sage_poc.observability import stage_timer
from sage_poc.rules import engine as rules_engine
from sage_poc.nodes.post_crisis_classifier import evaluate_s7
from sage_poc.safety.s3_semantic import check_s3, check_s3_bilingual, S3_THRESHOLD

_log = logging.getLogger(__name__)

_HAS_ARABIC_RE = re.compile(r'[؀-ۿ]')
_HAS_LATIN_RE = re.compile(r'[A-Za-z]')

_DISTRESS_WINDOW = 4
_DISTRESS_FLOOR = 6
_DISTRESS_STREAK = 3

_ENGAGEMENT_WINDOW = 4
_ENGAGEMENT_LOW = 4
_ENGAGEMENT_STREAK = 3

# W2 / G4: consecutive S7-clear monitoring turns required to step down monitoring -> supportive.
STEP_DOWN_CLEAR_TURNS = 2


def _update_distress_trajectory(state: SageState) -> tuple[list[int], bool]:
    """Append current turn's intensity to trajectory; return (updated_trajectory, escalating).

    Note: emotional_intensity in state is from the PREVIOUS turn (set by intent_route,
    which runs after safety_check). The trajectory is therefore one turn lagged.
    This is acceptable for a 3-turn streak heuristic — detection is delayed by one turn at most.
    """
    trajectory = list(state.get("distress_trajectory") or [])
    current = state.get("emotional_intensity", 5)
    trajectory.append(current)
    trajectory = trajectory[-_DISTRESS_WINDOW:]
    escalating = (
        len(trajectory) >= _DISTRESS_STREAK
        and all(s >= _DISTRESS_FLOOR for s in trajectory[-_DISTRESS_STREAK:])
    )
    return trajectory, escalating


def _update_engagement_trajectory(state: SageState) -> tuple[list[int], bool]:
    """Track engagement across turns; return (updated_trajectory, declining).

    Engagement is also one-turn lagged (set by intent_route, which runs after
    safety_check). Declining is True if the last 3 turns are all <= _ENGAGEMENT_LOW.
    """
    trajectory = list(state.get("engagement_trajectory") or [])
    current = state.get("engagement", 5)
    trajectory.append(current)
    trajectory = trajectory[-_ENGAGEMENT_WINDOW:]
    declining = (
        len(trajectory) >= _ENGAGEMENT_STREAK
        and all(s <= _ENGAGEMENT_LOW for s in trajectory[-_ENGAGEMENT_STREAK:])
    )
    return trajectory, declining


async def safety_check_node(state: SageState) -> dict:
    raw = state["raw_message"]
    code_switching = bool(_HAS_ARABIC_RE.search(raw) and _HAS_LATIN_RE.search(raw))
    lang = detect_language(raw)

    if lang == "ar":
        message_en = await async_translate_to_english(raw)
        text_ar = raw
    else:
        message_en = raw
        text_ar = None

    safety_result = rules_engine.evaluate("safety", {
        "text_en": message_en,
        "text_ar": text_ar,
        "language": lang,
        "text_raw": raw,  # lang="az" rules always match against the original message
    })

    new_crisis_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "crisis_flag"
    ]
    new_clinical_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "clinical_flag"
    ]
    third_party_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "third_party_crisis"
    ]

    # Third-party crisis overrides direct crisis — more specific pattern wins
    if third_party_flags:
        new_crisis_flags = []

    # S3: semantic crisis detection — OR-fusion with S1
    # Two-path: max(EN score, AR score) so Arabic crisis phrases in crisis_phrases.json
    # are reachable without translation. BGE-M3 is multilingual; the Arabic corpus entries
    # are only queryable via this second path when the raw text is Arabic.
    # Fail-open: exceptions and timeouts → score 0.0, no crash, S1 result stands.
    # v7 target: <50ms total for Layer 1. S3 embedding adds ~200-500ms per turn.
    # Acceptable for POC; production requires async pre-warm and potential GPU inference.
    #
    # STRUCTURAL SINGLE-TIER WARNING (2026-06-05): S3 is advisory at current threshold.
    # CRADLE sweep (scripts/s3_threshold_sweep.py) confirmed S3 adds 0 recall above S1 at any
    # threshold 0.65–0.8059 on 75 passive-SI cases. s3_score is returned in state and recorded
    # in the session audit row for clinical review — not as evidence of coverage.
    # For Arabic and Arabizi, S3 does NOT generalise at the current threshold:
    #   - Arabic idioms (SK-AR-002/003) score 0.70–0.74 — below S3_THRESHOLD=0.8059
    #   - Arabizi phrases (SK-AZ-001/002) score 0.39–0.81; only one phrase clears (+0.002)
    # S1 keyword coverage is therefore LOAD-BEARING for Arabic and Arabizi.
    # DO NOT prune Arabic/Arabizi keywords on the assumption that S3 or S2 (MARBERT,
    # not yet built) provides a semantic backstop — that backstop does not exist in POC.
    # Before pruning any AR/AZ keyword, run: uv run python scripts/verify_arabic_safety.py
    s3_score: float = 0.0  # initialized before try so it's always in scope for the return
    try:
        # check_s3_bilingual batches text_en + text_ar in one forward pass — avoids
        # two sequential encode() calls for Arabic (was the source of the latency regression).
        # stage_timer is log-only and wraps the call UNCHANGED — it cannot perturb the S3
        # encode or crisis verdict (asserted by test_embed_cache_equivalence's reference path).
        with stage_timer(
            "s3_encode",
            session_id=state.get("session_id"),
            turn=state.get("turn_count"),
            lang=lang,
        ):
            s3_score = await asyncio.wait_for(
                asyncio.to_thread(check_s3_bilingual, message_en, text_ar),
                timeout=5.0,
            )
        if s3_score >= S3_THRESHOLD:
            s3_suppressed = any(
                a.get("type") == "crisis_suppress" for a in safety_result.actions
            )
            if not s3_suppressed and "s3_semantic" not in new_crisis_flags:
                # Advisory: CRADLE sweep shows S3 adds 0 recall at this threshold.
                # Flag is recorded for audit trail visibility, not as a coverage claim.
                new_crisis_flags.append("s3_semantic")
    except asyncio.TimeoutError:
        # OPEN DECISION (clinical/product): is S1-only an acceptable crisis fallback?
        # Current behaviour: proceed as if S3 returned 0.0 (S1 lexicon result stands).
        # Alternative: fail conservative — surface crisis resources / escalate to human.
        # Until that decision is made, log at ERROR so log-based alerts fire.
        _log.error(
            "[safety_check] S3_TIMEOUT session=%s; semantic crisis detection disabled for this turn; "
            "S1-only (lexicon) result stands — verify BGE-M3 index is warmed",
            None,  # session_id not yet in state at this node; surfaced in output_gate audit row
        )
    except Exception as exc:
        _log.warning(
            "[safety_check] S3 check failed: %s; crisis detection degraded to S1 only", exc
        )

    trajectory, escalating = _update_distress_trajectory(state)
    engagement_trajectory, engagement_declining = _update_engagement_trajectory(state)

    # Suppress escalating_distress during active skill execution with good engagement:
    # high intensity is therapeutically expected when a user works through distressing material.
    # The heuristic is preserved for freeflow conversations where sustained high intensity
    # without a skill context is genuinely concerning.
    skill_active = bool(state.get("active_skill_id"))
    engagement_ok = state.get("engagement", 5) >= 5

    # Carry forward clinical flags from prior turns (set union — flags don't reset).
    # Also seed from cross-session persisted flags stored in therapeutic_profile.
    # third_party_flags are intentionally excluded: they signal concern about someone else,
    # not the current user's own clinical state. They flow through third_party_crisis instead.
    profile_persisted = (state.get("therapeutic_profile") or {}).get("persisted_clinical_flags") or []
    persisted_non_computed = list(set(
        [f for f in state.get("clinical_flags", []) if f != "escalating_distress"]
        + profile_persisted
    ))
    distress_signal = escalating or engagement_declining
    extra = ["escalating_distress"] if distress_signal and not (skill_active and engagement_ok) else []
    all_clinical = list(set(new_clinical_flags + extra + persisted_non_computed))

    crisis_state = state.get("crisis_state", "none")
    s7_result: str | None = None
    s7_method: str | None = None

    if crisis_state == "monitoring":
        s7_result, s7_method = await evaluate_s7(message_en)

    # Dedup crisis flags once, after all detection paths (S1 rules engine + S3 semantic) have
    # contributed. S1 can fire the same flag_id on both the raw Khaleeji text and its
    # English translation in the same evaluation pass, producing duplicates like
    # ["si_explicit", "si_explicit", "s3_semantic"]. dict.fromkeys preserves insertion order
    # (unlike set()) so the stored flag sequence is deterministic for the same input — a
    # clinical audit-trail requirement. is_safe, the header, and the messages insert all read
    # from this single deduped list.
    new_crisis_flags = list(dict.fromkeys(new_crisis_flags))

    # W2 / G4 warm de-escalation: while monitoring, count CONSECUTIVE S7-clear turns and step down
    # monitoring -> supportive after STEP_DOWN_CLEAR_TURNS. A "clear" turn is S7=RECOVERING AND no
    # S1/S3 fire this turn (is_safe). Any non-clear turn (STILL_DISTRESSED / UNCLEAR / NEW_CRISIS, or
    # a crisis fire) resets the streak — the safety floor is never softened by a broken streak. This
    # is a STATE computation; it never touches _route_after_safety (supportive is not 'monitoring',
    # so routing lets it fall through to the normal graph on its own). Never steps to 'none' in-session.
    _this_turn_is_safe = len(new_crisis_flags) == 0
    monitoring_clear_turns = state.get("monitoring_clear_turns", 0)
    if crisis_state == "monitoring":
        if _this_turn_is_safe and s7_result == "RECOVERING":
            monitoring_clear_turns += 1
        else:
            monitoring_clear_turns = 0
        if monitoring_clear_turns >= STEP_DOWN_CLEAR_TURNS:
            crisis_state = "supportive"  # stepped down; supportive is the in-session floor, never 'none'

    # v7.1 tiering (flag-gated). Fields are ABSENT when OFF, so a flag-off state write / audit
    # row is byte-identical to master (Check B); populated only when ON (F). is_safe and
    # crisis_flags below are UNCHANGED either way (is_safe stays the truthful detector aggregate);
    # routing authority moves to crisis_tier in _route_after_safety only when the flag is ON.
    tier_update: dict = {}
    from sage_poc import config as _cfg  # noqa: PLC0415
    if _cfg.CRISIS_TIERING_ENABLED:
        from sage_poc.safety.crisis_tier import (  # noqa: PLC0415
            resolve_crisis_tier_detail, _is_arabizi_suspect,
        )
        _tier, _tier_rule = resolve_crisis_tier_detail(
            new_crisis_flags, lang,
            code_switching=code_switching,
            arabizi_suspect=_is_arabizi_suspect(raw),
        )
        tier_update = {
            "crisis_tier": _tier,
            "tier_rule_id": _tier_rule,
            "supportive_posture": _tier == "T1",
            # G1b session counter: incremented on each T1 turn (output_gate flags the 2nd).
            "t1_count": state.get("t1_count", 0) + (1 if _tier == "T1" else 0),
        }

    # E7 §6a IPV pre-emption — detection expansion (flag-gated SAGE_IPV_PREEMPTION). Merges
    # domestic_situation for the 19 §6a-guard phrases so the route reaches ≥95% recall and the
    # precedence resolver/audit below see the IPV hit. OFF -> {} (byte-identical: only CF-005 fires).
    # Runs BEFORE apply_precedence so domestic_situation is present when the resolver ranks routes.
    from sage_poc.nodes.ipv_preempt import apply_ipv_preempt  # noqa: PLC0415
    ipv_update = apply_ipv_preempt({
        "message_en": message_en, "raw_message": raw, "clinical_flags": all_clinical,
    })
    if ipv_update:
        all_clinical = ipv_update["clinical_flags"]

    # B0 §4.5 precedence (flag-gated, same discipline as tier_update above). apply_precedence
    # returns {} when SAGE_ROUTE_PRECEDENCE is OFF -> this write is byte-identical to master.
    # When ON it emits precedence_winner + the full fired_safety_routes list (crisis/HR/IPV read
    # off the flags just computed; medical reads an empty channel until E3/B1 lands). is_safe and
    # crisis_flags are UNCHANGED either way — the resolver records, it does not yet re-route.
    from sage_poc.nodes.safety_precedence import apply_precedence  # noqa: PLC0415
    precedence_update = apply_precedence({
        "is_safe": len(new_crisis_flags) == 0,
        "clinical_flags": all_clinical,
    })

    return {
        **tier_update,
        **precedence_update,
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "s3_score": s3_score,  # advisory; recorded in audit for clinical reviewers
        "third_party_crisis": bool(third_party_flags),
        "new_clinical_flags_turn": new_clinical_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "engagement_trajectory": engagement_trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "monitoring_clear_turns": monitoring_clear_turns,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
        "turn_number": state.get("turn_number", 0) + 1,
    }
