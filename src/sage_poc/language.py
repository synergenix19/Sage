import re

import ollama
from langdetect import detect, detect_langs, LangDetectException

from sage_poc.config import TRANSLATION_MODEL, OLLAMA_BASE_URL

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


def detect_language(text: str) -> str:
    """Detect the language of *text*.

    Arabic Unicode block presence overrides langdetect to handle code-switching
    (mixed Arabic/English messages are classified as Arabic).

    For pure Latin-script text, langdetect is unreliable on short inputs and
    may return codes like "so" (Somali) for English phrases.  We fall back to
    "en" whenever the detected code is not a CJK or Arabic language and the
    text contains only Latin-script characters.
    """
    if re.search(r'[؀-ۿ]', text):
        return "ar"
    try:
        langs = detect_langs(text)
        top = langs[0]
        # If the highest-probability language is a known Latin-script language
        # and the text is pure ASCII/Latin, treat it as English.
        if top.lang in _LATIN_SCRIPT_LANGS and not re.search(r'[^\x00-\x7F]', text):
            return "en"
        return top.lang
    except LangDetectException:
        return "en"


def translate_to_english(text: str) -> str:
    """Translate *text* to English using the configured Ollama model."""
    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(
        model=TRANSLATION_MODEL,
        messages=[{
            "role": "user",
            "content": (
                "Translate the following text to English. "
                "Return ONLY the translation, nothing else:\n\n"
                f"{text}"
            ),
        }],
    )
    return response["message"]["content"].strip()


def translate_to_arabic(text: str) -> str:
    """Translate *text* to Modern Standard Arabic using the configured Ollama model."""
    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(
        model=TRANSLATION_MODEL,
        messages=[{
            "role": "user",
            "content": (
                "Translate the following text to Modern Standard Arabic. "
                "Return ONLY the Arabic translation, nothing else:\n\n"
                f"{text}"
            ),
        }],
    )
    return response["message"]["content"].strip()
