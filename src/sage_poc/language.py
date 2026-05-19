import re

import ollama
from langdetect import detect, LangDetectException

from sage_poc.config import TRANSLATION_MODEL, OLLAMA_BASE_URL


def detect_language(text: str) -> str:
    """Detect the language of *text*.

    Arabic Unicode block presence overrides langdetect to handle code-switching
    (mixed Arabic/English messages are classified as Arabic).
    """
    if re.search(r'[؀-ۿ]', text):
        return "ar"
    try:
        return detect(text)
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
