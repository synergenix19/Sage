"""Psychoed classifiers (spec §5.3/§5.4). Pure functions; deterministic inputs only.
Classifier A fail direction: ambiguity -> acute (doc: 'default to the higher tier').
Classifier B data (row framing mappings, the fail-to-personal default) is
safety-rule governed (spec §5.4) — changes need clinical sign-off."""
from __future__ import annotations
import json, re
from pathlib import Path

_DATA = json.loads(
    (Path(__file__).resolve().parents[3] / "data" / "psychoed" / "classifier_a.en.json").read_text()
)
FRAMING_FALLBACK = "personal"

def acute_distress(state_like: dict, message_en: str) -> bool:
    if state_like.get("crisis_state") == "monitoring":
        return True
    if state_like.get("fired_safety_routes"):
        return True
    msg = message_en.lower()
    if any(m in msg for m in _DATA["distress_markers"]):
        return True
    s = _DATA["structural"]
    if re.search(s["numeric_self_report_pattern"], msg):
        return True
    frags = [f for f in re.split(r"[.!?\n]+", message_en) if f.strip()]
    short = [f for f in frags if len(f.strip()) <= s["fragment_max_len"]]
    return len(frags) >= s["fragment_min_count"] and len(short) == len(frags)

def framing_for_row(row: dict) -> str:
    return row.get("framing") or FRAMING_FALLBACK
