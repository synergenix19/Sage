import re
from sage_poc.state import SageState
from sage_poc.language import detect_language, translate_to_english
from sage_poc.rules import engine as rules_engine
from sage_poc.nodes.post_crisis_classifier import evaluate_s7

_HAS_ARABIC_RE = re.compile(r'[؀-ۿ]')
_HAS_LATIN_RE = re.compile(r'[A-Za-z]')

_DISTRESS_WINDOW = 4
_DISTRESS_FLOOR = 6
_DISTRESS_STREAK = 3


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


def safety_check_node(state: SageState) -> dict:
    raw = state["raw_message"]
    code_switching = bool(_HAS_ARABIC_RE.search(raw) and _HAS_LATIN_RE.search(raw))
    lang = detect_language(raw)

    if lang == "ar":
        message_en = translate_to_english(raw)
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

    trajectory, escalating = _update_distress_trajectory(state)

    # Suppress escalating_distress during active skill execution with good engagement:
    # high intensity is therapeutically expected when a user works through distressing material.
    # The heuristic is preserved for freeflow conversations where sustained high intensity
    # without a skill context is genuinely concerning.
    skill_active = bool(state.get("active_skill_id"))
    engagement_ok = state.get("engagement", 5) >= 5

    # Carry forward clinical flags from prior turns (set union — flags don't reset)
    persisted = state.get("clinical_flags", [])
    extra = ["escalating_distress"] if escalating and not (skill_active and engagement_ok) else []
    all_clinical = list(set(new_clinical_flags + third_party_flags + extra + persisted))

    crisis_state = state.get("crisis_state", "none")
    s7_result: str | None = None
    s7_method: str | None = None

    if crisis_state == "monitoring":
        s7_result, s7_method = evaluate_s7(message_en)

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,   # third_party_crisis does NOT set is_safe=False
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
    }
