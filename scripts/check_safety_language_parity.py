"""Static gate: safety trigger phrase-files that carry English triggers must also carry Arabic
triggers (this is a bilingual product). Mirrors the check_state_channels.py static-gate pattern,
applied to safety DATA — #329's root class: a safety detector shipping EN-only for a bilingual
demographic (a live prod bypass: AR cardiac red-flags routed to a relaxation exercise).

A file "covers AR" if any trigger string contains Arabic script OR any rule declares an Arabic
`language`. GAP = has EN triggers, zero AR coverage, and not EXEMPT (with a documented reason).
Exit 1 on any un-exempted gap. Run: python scripts/check_safety_language_parity.py
"""
import json
import re
import sys
from pathlib import Path

_SAFETY_DIR = Path(__file__).resolve().parent.parent / "src" / "sage_poc" / "rules" / "data" / "safety"
_AR = re.compile(r"[؀-ۿ]")
_EN = re.compile(r"[A-Za-z]")
_AR_LANGS = {"ar", "arabic", "khaleeji", "both", "bilingual", "az", "arabizi"}

# Files exempt from AR parity — each needs a documented reason (a tracking ticket, not silence).
# These 3 pre-existing EN-only gaps were surfaced by this very check and are tracked in #330;
# EXEMPT keeps the gate GREEN for the enforced files (medical_redflag #329) while the three are
# clinician-authored. Remove each entry as its AR triggers land.
EXEMPT: dict[str, str] = {
    "harm_intrusive_patterns.json": "#330 — AR triggers pending clinician authoring (iatrogenic-harm veto)",
    "ocd_compulsion_patterns.json": "#330 — AR triggers pending clinician authoring (iatrogenic-harm veto)",
    "ipv_preempt_expansion.json": "#330 — AR triggers pending clinician authoring (IPV pre-emption)",
}

# JSON keys whose string values (or string-arrays) are matched against user text.
_TRIGGER_KEYS = {"patterns", "phrases", "phrase", "keywords", "terms", "en", "ar"}


def _collect(node, under_trigger=False):
    """Yield (string, is_ar_declared) for every trigger string; is_ar_declared carries a nearby
    language:ar signal. Walks dicts/lists; only strings under trigger keys count."""
    if isinstance(node, dict):
        lang = str(node.get("language", "")).lower()
        ar_decl = lang in _AR_LANGS
        for k, v in node.items():
            if k in _TRIGGER_KEYS:
                yield from ((s, ar_decl) for s in _strings(v))
            else:
                yield from _collect(v, under_trigger)
    elif isinstance(node, list):
        for item in node:
            yield from _collect(item, under_trigger)


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, list):
        for x in v:
            if isinstance(x, str):
                yield x
            else:
                yield from (s for s, _ in _collect(x))


def audit_file(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    triggers = list(_collect(data))
    en = sum(1 for s, _ in triggers if _EN.search(s))
    ar = sum(1 for s, decl in triggers if _AR.search(s) or decl)
    return en, ar


def main() -> int:
    gaps, report = [], []
    for path in sorted(_SAFETY_DIR.glob("*.json")):
        en, ar = audit_file(path)
        status = "OK" if (ar > 0 or en == 0) else ("EXEMPT" if path.name in EXEMPT else "GAP")
        report.append((path.name, en, ar, status))
        if status == "GAP":
            gaps.append(path.name)
    w = max(len(n) for n, *_ in report)
    print("safety trigger-file language parity (EN triggers require AR coverage):\n")
    for name, en, ar, status in report:
        mark = {"OK": "✅", "GAP": "❌ GAP", "EXEMPT": "⚠️  exempt"}[status]
        print(f"  {name:<{w}}  en={en:<4} ar={ar:<4} {mark}")
    if gaps:
        print(f"\n❌ {len(gaps)} safety file(s) EN-only (bilingual product): {', '.join(gaps)}")
        print("   Add Arabic triggers, or add to EXEMPT with a documented reason.")
        return 1
    print("\n✅ all safety trigger files with EN coverage also carry AR coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
