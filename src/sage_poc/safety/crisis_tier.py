"""Crisis-tier resolver (v7.1 amendment to §5.1 OR-fusion).

Pure function: given the set of fired Layer-1 safety flags and the detected language,
return the crisis TIER ("T2" acute / "T1" warm / "none"). The boundary lives entirely in
`rules/data/safety/tier_routing.json` (clinician-editable, 3 signed rules); nothing here
hardcodes it. safety_check calls resolve_crisis_tier() and routes on the result.

CARDINAL RULE 4: this changes only the RESPONSE tier, never DETECTION. The fired-flag set is
produced by the deterministic S1/S3 detectors unchanged; this resolver cannot suppress a flag.
"""
from __future__ import annotations
import json
import pathlib
from typing import Iterable

_RULES_PATH = pathlib.Path(__file__).parent.parent / "rules" / "data" / "safety" / "tier_routing.json"

# s3_semantic is the only non-keyword (semantic) flag; everything else is an S1 keyword flag.
_S3_FLAG = "s3_semantic"


def _load_tier_rules() -> list[dict]:
    data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return data["rules"]


def _default_tier() -> str:
    data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return data.get("default_tier", "none")


def _matches(when: dict, *, s1_fired: bool, s3_fired: bool, lang: str) -> bool:
    if "s1_fired" in when and when["s1_fired"] != s1_fired:
        return False
    if "s3_fired" in when and when["s3_fired"] != s3_fired:
        return False
    if "lang_in" in when and lang not in when["lang_in"]:
        return False
    return True


def resolve_crisis_tier(fired_flags: Iterable[str], lang: str) -> str:
    """Resolve the crisis tier from the fired flag set + language via tier_routing.json.

    First matching rule wins; falls through to the JSON default_tier ("none").
    """
    flags = set(fired_flags or ())
    s3_fired = _S3_FLAG in flags
    s1_fired = bool(flags - {_S3_FLAG})  # any keyword flag
    for rule in _load_tier_rules():
        if _matches(rule.get("when", {}), s1_fired=s1_fired, s3_fired=s3_fired, lang=lang):
            return rule["tier"]
    return _default_tier()
