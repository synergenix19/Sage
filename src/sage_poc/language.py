import re

from langdetect import detect_langs, LangDetectException

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


def translate_to_arabic(text: str) -> str:
    """Translate *text* to Modern Standard Arabic.

    Falls back to the original English text if the API is unavailable so the
    user receives a response rather than a crash.
    """
    try:
        from sage_poc.llm import get_translator
        llm = get_translator()
        response = llm.invoke([{
            "role": "user",
            "content": (
                "Translate the following text to Modern Standard Arabic. "
                "Return ONLY the Arabic translation, nothing else:\n\n"
                f"{text}"
            ),
        }])
        return response.content.strip()
    except Exception:
        return text
