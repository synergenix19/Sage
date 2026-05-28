# ARCHITECTURE WARNING — SINGLE-LAYER SAFETY (2026-05-26)
#
# v7 spec §5.1 defines Layer 1 as OR-fusion: S1 (crisis lexicon) OR S2 (MARBERT
# classifier) OR S3 (semantic crisis embeddings) OR S6 (clinical flag escalation).
# Any layer catching a phrase is sufficient; the layers provide redundancy.
#
# CURRENT STATE: S1 (lexicon) + S3 (BGE-M3 semantic). S2 (MARBERT classifier) not implemented.
# S3 was added in V7 Door 1.5 (2026-05-26). OR-fusion: either layer catching → crisis protocol.
# Phrases not caught by S1 keywords AND scoring < S3_THRESHOLD (0.8059) will be missed.
#
# IMPLICATION: S3 extends coverage beyond enumerable keywords to semantic neighbours of
# the 48-phrase crisis corpus. Short hopelessness phrases (e.g. "no future for me")
# are covered by SK-EN-002 keyword expansion. Remaining gap: novel phrasing not
# semantically close to the existing corpus — add to crisis_phrases.json and re-calibrate.
#
# NEXT STEPS (priority order before feature expansion):
#   S2: off-the-shelf MARBERT binary classifier (crisis/not-crisis) — no fine-tuning
#       required for baseline coverage. Route Arabic text through MARBERT before
#       lexicon to catch dialectal expressions outside the keyword vocabulary.
#   S3: BGE-M3 semantic similarity against a crisis phrase embedding index.
#       Infrastructure is now available (see sage_poc/memory/embedding.py).
#   Reference: CRISP-DM plan, Experiment 4.2 (Week N).

import re
import asyncio
import logging
from sage_poc.state import SageState
from sage_poc.language import detect_language, async_translate_to_english
from sage_poc.rules import engine as rules_engine
from sage_poc.nodes.post_crisis_classifier import evaluate_s7
from sage_poc.safety.s3_semantic import check_s3, S3_THRESHOLD

_log = logging.getLogger(__name__)

_HAS_ARABIC_RE = re.compile(r'[؀-ۿ]')
_HAS_LATIN_RE = re.compile(r'[A-Za-z]')

_DISTRESS_WINDOW = 4
_DISTRESS_FLOOR = 6
_DISTRESS_STREAK = 3

_ENGAGEMENT_WINDOW = 4
_ENGAGEMENT_LOW = 4
_ENGAGEMENT_STREAK = 3


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
    # Fail-open: exceptions and timeouts → score 0.0, no crash, S1 result stands.
    # v7 target: <50ms total for Layer 1. S3 embedding adds ~200-500ms per turn.
    # Acceptable for POC; production requires async pre-warm and potential GPU inference.
    # TODO: Run S3 on both message_en and raw Arabic text for bilingual coverage. Currently EN-only.
    try:
        s3_score = await asyncio.wait_for(
            asyncio.to_thread(check_s3, message_en),
            timeout=5.0,
        )
        if s3_score >= S3_THRESHOLD:
            s3_suppressed = any(
                a.get("type") == "crisis_suppress" for a in safety_result.actions
            )
            if not s3_suppressed and "s3_semantic" not in new_crisis_flags:
                new_crisis_flags.append("s3_semantic")
    except asyncio.TimeoutError:
        _log.warning(
            "[safety_check] S3 timeout after 5.0s; crisis detection degraded to S1 only"
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

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "third_party_crisis": bool(third_party_flags),
        "new_clinical_flags_turn": new_clinical_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "engagement_trajectory": engagement_trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
        "turn_number": state.get("turn_number", 0) + 1,
    }
