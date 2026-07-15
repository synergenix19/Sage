"""Deterministic venting / "just listen" detection for routing authority (F6).

Reuses the PI-VI-001 keyword set (rules/data/prompt_injection/venting_intent.json) —
the SAME signal that already injects a hold-space instruction into freeflow, now given
authority over routing so it can suppress skill imposition (its detection previously had
no such authority; see B1 skill-clear finding — same class)."""
import json
from functools import lru_cache
from pathlib import Path

_PI_VI = Path(__file__).resolve().parent.parent / "rules" / "data" / "prompt_injection" / "venting_intent.json"


@lru_cache(maxsize=1)
def _keywords() -> tuple[str, ...]:
    data = json.loads(_PI_VI.read_text(encoding="utf-8"))
    kws = []
    for rule in data.get("rules", []):
        if rule.get("rule_id") == "PI-VI-001" and rule.get("active"):
            kws.extend(k.lower() for k in rule.get("trigger_keywords", []))
    return tuple(kws)


def detect_venting(message_en: str, raw_message: str, detected_language: str) -> bool:
    """True if an explicit don't-fix / just-listen signal is present (EN via message_en,
    Arabic via raw_message — PI-VI-001 carries Khaleeji keywords). Substring, case-insensitive."""
    hay = f"{message_en} \n {raw_message}".lower()
    return any(kw in hay for kw in _keywords())
