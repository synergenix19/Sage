from sage_poc.state import SageState
from sage_poc.language import detect_language, translate_to_english
from sage_poc.rules import engine as rules_engine

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

    # Carry forward clinical flags from prior turns (set union — flags don't reset)
    persisted = state.get("clinical_flags", [])
    extra = ["escalating_distress"] if escalating else []
    all_clinical = list(set(new_clinical_flags + third_party_flags + extra + persisted))

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,   # third_party_crisis does NOT set is_safe=False
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "path": state["path"] + ["safety_check"],
    }
