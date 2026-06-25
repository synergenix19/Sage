"""Deterministic: is the user asking to recall something THEY told Sage earlier?

Sole consumer: composer eviction-exemption (never drop the disclosure being recalled,
see composer overflow logic). It does NOT gate the L0 MEMORY clause — that fix is
unconditional and correct on every turn, so scoping it to this detector would leave the
bug live for recall phrasings the regex misses.

Fails toward firing: a false positive only protects history from eviction, which is safe.
Reads raw_message for Arabic, message_en for English (mirrors knowledge_retrieve's split).
"""
from __future__ import annotations
import re
from sage_poc.state import SageState

_EN = (
    r"\bwhat did i (just )?(tell|say to|mention to) you\b",
    r"\bdidn'?t i (say|tell|mention)\b",
    r"\b(do|don'?t) you remember (what|when|that) i\b",
    r"\byou said\b",
    r"\bi (told|said to) you\b",
)
# Arabic markers first (Arabic-example-ordering convention).
_AR = (
    r"ماذا قلت لك",
    r"ألم (أقل|أخبرك|أذكر)",
    r"هل تتذكر (ما|أن|عندما)",
    r"قلت لك",
    r"كما (قلت|ذكرت|أخبرتك)",
)


def detect_self_reference(state: SageState) -> bool:
    lang = state.get("detected_language", "en")
    text = state.get("raw_message", "") if lang == "ar" else state.get("message_en", "")
    if not text:
        return False
    low = text.lower()
    return any(re.search(m, low) for m in (_AR if lang == "ar" else _EN))
