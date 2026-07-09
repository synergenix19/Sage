import json
import re
from functools import lru_cache
from pathlib import Path

from langdetect import detect_langs, LangDetectException

try:
    from sage_poc.llm import get_translator
except Exception:  # pragma: no cover – circular-import guard during early startup
    get_translator = None  # type: ignore[assignment]

# Languages that use the Latin script and may be confused with English by
# langdetect on short inputs. We treat these as English when text contains no
# Arabic characters.
_LATIN_SCRIPT_LANGS = {
    "af", "ca", "cs", "cy", "da", "de", "en", "eo", "es", "et", "eu", "fi",
    "fr", "ga", "gl", "hr", "hu", "id", "it", "lt", "lv", "mk", "ms", "mt",
    "nl", "no", "pl", "pt", "ro", "sk", "sl", "sq", "sr", "sv", "sw", "tl",
    "tr", "vi",
    # Known false-positive codes langdetect assigns to short English phrases
    "so", "ha", "mg", "st", "ht",
}

# P2-5: Unicode bidirectional and directional formatting marks that can
# corrupt langdetect results and must be stripped before detection.
_DIRECTIONAL_MARKS = re.compile(r'[‎‏‪-‮⁦-⁩]')


def detect_language(text: str | None) -> str:
    """Detect the language of *text*, returning "en" as a safe default.

    Handles None and empty input (P2-4). Strips Unicode directional marks
    before detection (P2-5) — these can corrupt langdetect on RTL text.

    Arabic Unicode block presence overrides langdetect to handle code-switching
    (mixed Arabic/English messages are classified as Arabic).

    For pure Latin-script text, langdetect is unreliable on short inputs and
    may return codes like "so" (Somali) for English phrases. Falls back to
    "en" whenever the detected code is a known Latin-script language and the
    text is pure ASCII/Latin.
    """
    if not text:
        return "en"

    text = _DIRECTIONAL_MARKS.sub('', text)

    if re.search(r'[؀-ۿ]', text):
        return "ar"
    try:
        langs = detect_langs(text)
        top = langs[0]
        if top.lang in _LATIN_SCRIPT_LANGS and not re.search(r'[^\x00-\x7F]', text):
            return "en"
        return top.lang
    except LangDetectException:
        return "en"


def text_direction(language: str | None) -> str:
    """Writing direction for a language code: 'rtl' for Arabic, 'ltr' otherwise.

    Authoritative source for the X-Sage-Direction response header. The frontend uses this
    instead of re-inferring direction from message content, because dir="auto" keys off the
    first strong character and flips an Arabic answer that opens on a Latin token (e.g. "CBT").
    """
    return "rtl" if language == "ar" else "ltr"


_EXEMPLARS_PATH = Path(__file__).parent / "data" / "khaleeji_translation_exemplars.json"
_GLOSSARY_PATH = Path(__file__).parent / "data" / "clinical_term_glossary.json"


def _clinical_glossary() -> dict:
    """W5 (G6): clinician-extendable therapy-term map anchoring CBT/ACT/DBT technique names to
    clinically sensible Khaleeji Arabic (avoids literal errors like grounding->'للتواصل مع الأرض')."""
    return json.loads(_GLOSSARY_PATH.read_text(encoding="utf-8"))


def _glossary_lines_for(text: str) -> list[str]:
    """Only the glossary entries whose EN term appears in this message (no prompt bloat)."""
    low = (text or "").lower()
    hits = [t for t in _clinical_glossary()["terms"] if t["en"].lower() in low]
    if not hits:
        return []
    out = ["", "Clinical terms — render these EXACTLY as given, never translate them literally:"]
    for t in hits:
        out.append(f"  {t['en']} -> {t['ar']}")
    return out


@lru_cache(maxsize=1)
def _khaleeji_exemplars() -> dict:
    """Load the Emirati Gulf translation exemplars once (cached)."""
    return json.loads(_EXEMPLARS_PATH.read_text(encoding="utf-8"))


# Signed "mirror-when-marked, neutral-when-unknown" gender-address policy applied at the
# translation hop: when the user's own message grammatically self-marks their gender
# (see sage_poc.gender_marker.detect_gender_marking), the reply mirrors it in correct
# Emirati Khaleeji second-person address; when unmarked, the reply is gender-neutral.
# The exemplars in khaleeji_translation_exemplars.json are all masculine-addressed
# (وياك/عليك/تحس) -- these directives override that masculine default per-turn.
_GENDER_DIRECTIVES: dict[str, str] = {
    "f": (
        "The user identifies as female (self-marked in their message). Address them in "
        "FEMININE Emirati Khaleeji second-person forms (عليج not عليك, وياج not وياك, "
        "تحسّين not تحسّ). The exemplars show register/warmth -- follow their dialect and "
        "tone but use feminine address, overriding the exemplars' masculine forms."
    ),
    "m": (
        "The user identifies as male (self-marked in their message). Address them in "
        "MASCULINE Emirati Khaleeji second-person forms (عليك, وياك, تحسّ), matching the "
        "exemplars' masculine address."
    ),
    "none": (
        "The user's gender is not marked. Use gender-NEUTRAL constructions -- avoid "
        "gendered second-person verbs/pronoun suffixes; prefer first-person presence, "
        "collaborative forms (خلنا), impersonal/nominal phrasing. Do NOT guess a gender."
    ),
}


def _build_khaleeji_translation_prompt(text: str, *, strict: bool = False, gender: str = "none") -> str:
    """Build a few-shot prompt that anchors the translator on named Emirati Gulf
    exemplars so the output dialect stays consistent turn to turn.

    Single source of truth for both the sync and async Arabic translators.

    When strict=True, the prompt forbids leaving any English word untranslated,
    forcing the LLM to transliterate or translate all terms.

    gender is "f" | "m" | "none" (see sage_poc.gender_marker.detect_gender_marking) and
    selects the second-person address-form directive per the signed gender policy.
    Defaults to "none" (gender-neutral) so callers that do not pass it keep the safe,
    non-guessing behavior.
    """
    data = _khaleeji_exemplars()
    dialect = data["dialect_name"]
    lines = [
        f"You are translating warm, supportive messages from a wellness companion "
        f"named Sage into {dialect}. Keep the same warmth and conversational rhythm. "
        f"Use natural everyday {dialect} phrasing, not formal or clinical Modern "
        f"Standard Arabic. Stay in {dialect} consistently across the whole message. "
        f"Return only the translation."
        + (
            " The output must be entirely in Arabic script with no English words; "
            "translate or transliterate any names or terms." if strict else ""
        ),
        "",
        _GENDER_DIRECTIVES.get(gender, _GENDER_DIRECTIVES["none"]),
    ]
    # W5 (G6): inject the clinical-term glossary for any technique names present in this message,
    # so CBT/ACT/DBT terms render as clinically sensible Arabic instead of literal mistranslations.
    lines.extend(_glossary_lines_for(text))
    lines += ["", "Examples:"]
    for ex in data["exemplars"]:
        lines.append(f"English: {ex['en']}")
        lines.append(f"Arabic: {ex['ar']}")
        lines.append("")
    lines.append("Now translate this:")
    lines.append(f"English: {text}")
    lines.append("Arabic:")
    return "\n".join(lines)


def translate_to_english(text: str) -> str:
    """Translate *text* to English.

    Falls back to the original text if the API is unavailable so that the
    English-language crisis keyword filter still runs on the raw input.
    """
    try:
        from sage_poc.llm import get_translator
        llm = get_translator()
        response = llm.invoke([{
            "role": "user",
            "content": (
                "Translate the following text to English. "
                "Return ONLY the translation, nothing else:\n\n"
                f"{text}"
            ),
        }])
        return response.content.strip()
    except Exception:
        return text


def translate_to_arabic(text: str, *, gender: str = "none") -> str:
    """Translate *text* to Khaleeji Gulf Arabic.

    Falls back to the original English text if the API is unavailable so the
    user receives a response rather than a crash.

    gender is "f" | "m" | "none" (signed gender-address policy); default "none" preserves
    existing callers' current (gender-neutral) behavior.
    """
    try:
        from sage_poc.llm import get_translator
        llm = get_translator()
        response = llm.invoke([{
            "role": "user",
            "content": _build_khaleeji_translation_prompt(text, gender=gender),
        }])
        return response.content.strip()
    except Exception:
        return text


TRANSLATION_TIMEOUT_SECONDS: float = 30.0


async def async_translate_to_arabic(text: str, *, strict: bool = False, gender: str = "none") -> str:
    """Translate text to Khaleeji Gulf Arabic using resilient_invoke. Returns original on failure.

    gender is "f" | "m" | "none" (signed "mirror-when-marked, neutral-when-unknown" address
    policy; see sage_poc.gender_marker.detect_gender_marking). Default "none" preserves the
    prior (gender-neutral) prompt for any caller that does not pass it.
    """
    from sage_poc.resilience import resilient_invoke
    result = await resilient_invoke(
        get_translator(),
        [{
            "role": "user",
            "content": _build_khaleeji_translation_prompt(text, strict=strict, gender=gender),
        }],
        node="translate_to_arabic",
        language="ar",
    )
    return result or text


async def async_translate_to_english(text: str) -> str:
    """Translate text to English using resilient_invoke. Returns original on failure."""
    from sage_poc.resilience import resilient_invoke
    result = await resilient_invoke(
        get_translator(),
        [{
            "role": "user",
            "content": (
                "Translate the following text to English. "
                "Return ONLY the translation, nothing else:\n\n"
                f"{text}"
            ),
        }],
        node="translate_to_english",
        language="en",
    )
    return result or text
