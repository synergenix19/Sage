"""Interim medical red-flag pre-screen (B1 harm floor).

STOPGAP, not the fix. Deterministic literal/regex match over the BOT BEHAVIOUR §1
phrase list. Poor recall against paraphrase BY DESIGN — closes the exact-phrase
and near-phrase case the fixtures were written for while the full E3 detector is
built to the >=95% per-class recall gate (medical_e3_recall.json). Do NOT present
this as coverage. It does not reduce or defer B1's real detector.

ARABIC: INTERIM native coverage (#329, 2026-07-16) — NOT full coverage. The phrase list
now carries native-Arabic regex patterns for the §1 descriptor classes (crushing/
squeezing/radiating chest pain, etc.), matched on RAW input (never machine translation)
per the reads-raw language contract. This closes the exact- and near-phrase Arabic case
(verified by tests/test_medical_redflag_ar_329.py); paraphrase and colloquial-Gulf recall
remain weak BY DESIGN, pending the full E3 detector. Do NOT present this as coverage.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

_PHRASES_PATH = Path(__file__).resolve().parent.parent / "rules" / "data" / "safety" / "medical_redflag_phrases.json"


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[str, "re.Pattern[str]"], ...]:
    data = json.loads(_PHRASES_PATH.read_text(encoding="utf-8"))
    out = []
    for p in data["phrases"]:
        expr = p["phrase"] if p.get("match") == "regex" else re.escape(p["phrase"])
        out.append((p["id"], re.compile(expr, re.IGNORECASE)))
    return tuple(out)


def detect_medical_redflag(*texts: str) -> list[str]:
    """Ids of any §1 red-flag phrases present across the given texts. [] = none.
    Case-insensitive; entries are literal substrings unless flagged match:"regex".
    Includes interim native-Arabic §1 patterns (#329) matched on raw input; paraphrase
    and colloquial-Gulf recall intentionally weak/absent pending the full E3 detector."""
    hay = " \n ".join(t for t in texts if t)
    return [pid for pid, pat in _patterns() if pat.search(hay)]
