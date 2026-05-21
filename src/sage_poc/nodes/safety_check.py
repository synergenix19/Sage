from sage_poc.state import SageState
from sage_poc.language import detect_language, translate_to_english
from sage_poc.rules import engine as rules_engine


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

    # Carry forward clinical flags from prior turns (set union — flags don't reset)
    persisted = state.get("clinical_flags", [])
    all_clinical = list(set(new_clinical_flags + persisted))

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "clinical_flags": all_clinical,
        "path": state["path"] + ["safety_check"],
    }
