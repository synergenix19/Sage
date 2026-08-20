import re
import unicodedata

# The single canonical Arabic-detection primitive. Every call site that needs to know
# "does this string contain an Arabic character" (skill few-shot selection, retrieval
# query gating, output-gate translate-out routing, keyword-rule language classification)
# should use has_arabic() below, or ARABIC_CHAR_RE directly when it needs a count/findall
# rather than a bool. Six previously independent reimplementations tested this exact
# Unicode block (U+0600-U+06FF, the Arabic script block) via different code shapes; this
# is the merge point so future callers do not add a seventh.
ARABIC_CHAR_RE = re.compile(r'[؀-ۿ]')


def has_arabic(text: str) -> bool:
    """True if text contains at least one character in the Arabic script block
    (U+0600-U+06FF). Presence check only, not a language classifier: mixed-script
    text returns True, and this does not distinguish Arabic from other languages
    that share the block's punctuation-only characters."""
    return bool(ARABIC_CHAR_RE.search(text or ""))


def strip_invisible(text: str) -> str:
    """Remove ZWSP/ZWNJ/ZWJ (U+200B–U+200D), LTR/RTL marks (U+200E–U+200F), BOM (U+FEFF)."""
    return re.sub(r'[​-‏﻿]', '', text)


def strip_arabic_diacritics(text: str) -> str:
    """Remove Arabic harakat: fatha, damma, kasra, sukun, shadda, and other diacritics."""
    return re.sub(r'[ً-ٰ]', '', text)


def normalize_alef(text: str) -> str:
    """Normalise alef-hamza-above (أ U+0623), alef-madda (آ U+0622),
    alef-hamza-below (إ U+0625), and alef-wasla (ٱ U+0671) to bare alef (ا U+0627)."""
    return re.sub(r'[آأإٱ]', 'ا', text)


_TYPOGRAPHIC_SUBSTITUTIONS = str.maketrans({
    '‘': "'",   # LEFT SINGLE QUOTATION MARK
    '’': "'",   # RIGHT SINGLE QUOTATION MARK (iOS/Android apostrophe)
    '‚': "'",   # SINGLE LOW-9 QUOTATION MARK
    '‛': "'",   # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    '“': '"',   # LEFT DOUBLE QUOTATION MARK
    '”': '"',   # RIGHT DOUBLE QUOTATION MARK
    '„': '"',   # DOUBLE LOW-9 QUOTATION MARK
    '‟': '"',   # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
    '—': '-',   # EM DASH -> hyphen-minus
    '–': '-',   # EN DASH -> hyphen-minus
    '−': '-',   # MINUS SIGN -> hyphen-minus
})


def normalize_text(text: str) -> str:
    """
    Universal pre-processing for all text before keyword matching.
    Pipeline: strip_invisible -> NFKC -> typographic substitution -> lowercase.

    Typographic substitution maps iOS/Android smart quotes (U+2018/U+2019),
    smart double quotes (U+201C/U+201D), and dashes (U+2013/U+2014) to their
    ASCII equivalents so keyword patterns match regardless of input device.
    NFKC folds fullwidth/halfwidth characters and other compatibility variants.
    """
    text = strip_invisible(text)
    text = unicodedata.normalize('NFKC', text)
    text = text.translate(_TYPOGRAPHIC_SUBSTITUTIONS)
    return text.lower()


def normalize_arabic(text: str) -> str:
    """
    Extended normalization for Arabic text.
    Pipeline: strip_invisible -> NFKC -> strip_diacritics -> normalize_alef -> lowercase.
    """
    text = strip_invisible(text)
    text = unicodedata.normalize('NFKC', text)
    text = strip_arabic_diacritics(text)
    text = normalize_alef(text)
    return text.lower()
