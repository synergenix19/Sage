# src/sage_poc/nodes/safety_check.py
import re
from sage_poc.state import SageState
from sage_poc.language import detect_language, translate_to_english

CRISIS_KEYWORDS = [
    "kill myself", "want to die", "end my life", "suicide", "suicidal",
    "hurt myself", "self-harm", "cut myself", "overdose", "no reason to live",
    "better off dead", "can't go on", "not worth living",
    "أريد الموت", "انتحار", "أنهي حياتي", "أؤذي نفسي",
]

CLINICAL_KEYWORD_SETS: dict[str, list[str]] = {
    "substance_use": [
        "drinking", "drunk", "alcohol", "alcoholism", "liquor", "beer", "wine",
        "drugs", "drug use", "cocaine", "heroin", "marijuana", "weed",
        "using pills", "numb the pain", "cope with drink",
        "كحول", "مخدرات", "حبوب مخدرة", "مدمن",
    ],
    "trauma_indicator": [
        "abuse", "abused", "assault", "assaulted", "attacked", "violence",
        "hurt me", "hit me", "rape", "molested", "trauma",
        "إساءة", "اعتداء", "عنف",
    ],
    "eating_concern": [
        "purging", "binge eating", "starving myself", "not eating",
        "eating disorder", "anorexia", "bulimia",
        "لا آكل", "أتجوع",
    ],
    "medication_mention": [
        "medication", "antidepressant", "dosage", "prescribed", "prescription",
        "دواء", "مضادات الاكتئاب", "جرعة",
    ],
}


def _contains_crisis(text: str) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in CRISIS_KEYWORDS if kw.lower() in text_lower]


def _detect_clinical_flags(text: str) -> list[str]:
    text_lower = text.lower()
    return [
        flag_type
        for flag_type, keywords in CLINICAL_KEYWORD_SETS.items()
        if any(kw.lower() in text_lower for kw in keywords)
    ]


def safety_check_node(state: SageState) -> dict:
    raw = state["raw_message"]
    lang = detect_language(raw)

    if lang == "ar":
        arabic_crisis = _contains_crisis(raw)
        arabic_clinical = _detect_clinical_flags(raw)
        message_en = translate_to_english(raw)
    else:
        arabic_crisis = []
        arabic_clinical = []
        message_en = raw

    english_crisis = _contains_crisis(message_en)
    english_clinical = _detect_clinical_flags(message_en)

    all_crisis = list(set(arabic_crisis + english_crisis))
    all_clinical = list(set(arabic_clinical + english_clinical))

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(all_crisis) == 0,
        "crisis_flags": all_crisis,
        "clinical_flags": all_clinical,
        "path": state["path"] + ["safety_check"],
    }
