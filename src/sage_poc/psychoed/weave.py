"""PSY-WEAVE-1 response evaluation (spec §6.1). Pure; driven entirely by
data/psychoed/weave/psy_weave_1.en.json's evaluation_semantics. Fail-closed:
anything not a clear negative routes toward crisis. Never-disarm: this module
never reads SageState; callers pass the raw reply text."""
from __future__ import annotations
import re
from sage_poc.psychoed import store

def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s']", "", text.lower()).strip()

def is_clear_negative(reply: str) -> bool:
    data = store.weave_data()
    sem = data["evaluation_semantics"]
    assert sem["default"] == "fail_closed_to_crisis"
    norm = _normalize(reply)
    if not norm:
        return False
    if any(m in norm for m in data["contradiction_markers"]):   # order[0]: markers first
        return False
    return any(re.fullmatch(p, norm) for p in data["clear_negative_patterns"])  # order[1]

def evaluate(reply: str) -> str:
    return "proceed" if is_clear_negative(reply) else "crisis"
