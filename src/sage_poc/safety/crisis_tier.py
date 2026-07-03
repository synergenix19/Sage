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
import re
from typing import Iterable

_RULES_PATH = pathlib.Path(__file__).parent.parent / "rules" / "data" / "safety" / "tier_routing.json"

# s3_semantic is the only non-keyword (semantic) flag; everything else is an S1 keyword flag.
_S3_FLAG = "s3_semantic"

# Arabizi "chatspeak" letter-digits used mid-word for Arabic phonemes (3=ع, 7=ح, 5=خ, 2=ء,
# 6=ط, 9=ص). Interim heuristic (full Arabizi language-ID is the pending arabizi project):
# a digit immediately adjacent to a Latin letter is a letter-substitution, not a numeral —
# so "m5taneg"/"ta3ban" flag, but "3 kids"/"2 jobs" (space-separated numerals) do not.
_ARABIZI_LETTERDIGIT_RE = re.compile(r"(?i)[a-z][2356789]|[2356789][a-z]")


def _is_arabizi_suspect(raw: str | None) -> bool:
    """Conservative Arabizi heuristic on the raw message. Errs toward suspect (fail-closed):
    if it fires, a T1 (warm) route is downgraded to T2 (acute)."""
    if not raw:
        return False
    return bool(_ARABIZI_LETTERDIGIT_RE.search(raw))


def _load_tier_rules() -> list[dict]:
    data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return data["rules"]


def _default_tier() -> str:
    data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    return data.get("default_tier", "none")


def _matches(when: dict, *, s1_fired: bool, s3_fired: bool, lang: str, confident_lang: bool) -> bool:
    if "s1_fired" in when and when["s1_fired"] != s1_fired:
        return False
    if "s3_fired" in when and when["s3_fired"] != s3_fired:
        return False
    if "lang_in" in when and lang not in when["lang_in"]:
        return False
    if "require_confident_lang" in when and when["require_confident_lang"] != confident_lang:
        return False
    return True


def resolve_crisis_tier(
    fired_flags: Iterable[str],
    lang: str,
    *,
    code_switching: bool = False,
    arabizi_suspect: bool = False,
) -> str:
    """Resolve the crisis tier from the fired flag set + language via tier_routing.json.

    The T1 (warm) route requires CONFIDENT English: lang=='en' AND not code_switching AND
    not arabizi_suspect. Anything else with a fired semantic signal is caught fail-closed
    (s3_failclosed -> T2), so a mis-classified Arabizi/code-switched true-SI message never
    drops to T1. First matching rule wins; only a turn with NO fired signal reaches the
    JSON default_tier ("none").
    """
    flags = set(fired_flags or ())
    s3_fired = _S3_FLAG in flags
    s1_fired = bool(flags - {_S3_FLAG})  # any keyword flag
    confident_lang = (lang == "en") and (not code_switching) and (not arabizi_suspect)
    for rule in _load_tier_rules():
        if _matches(rule.get("when", {}), s1_fired=s1_fired, s3_fired=s3_fired,
                    lang=lang, confident_lang=confident_lang):
            return rule["tier"]
    return _default_tier()
