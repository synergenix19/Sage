"""$0 re-score of the saved opener probe with a COMPREHENSIVE reflective-opener
detector (the prerequisite from the #2 RCA: the old detector under-counted robotic
and over-counted substance-first; it is also the Tier-1 output_gate gate artifact,
so it must be right first). Reads saved replies — no new LLM calls.

reflective_opener := the reply LEADS with a feeling-reflection / normalization /
stock-empathy frame rather than the specific situation. This is precisely what L0
+ intensity_guidance forbid ("...or any reflective opener").
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
RES = ROOT / "tests" / "fixtures" / "counsel_chat" / "openers_probe_results.json"

# Anchored at the start of the reply. Covers the families observed in the probe.
_REFLECTIVE = re.compile(
    r"^\s*(?:oh[,!]?\s+)?(?:"
    r"it\s+sounds\b"
    r"|that\s+sounds\b"
    r"|i'?m\s+(?:so\s+|really\s+|very\s+)?sorry\b"
    r"|i\s+am\s+(?:so\s+|really\s+)?sorry\b"
    r"|it'?s\s+(?:completely\s+|totally\s+|perfectly\s+|quite\s+)?"
    r"(?:understandable|normal|natural|common|okay|ok|valid)\b"
    r"|it\s+is\s+(?:completely\s+)?(?:understandable|normal|natural)\b"
    r"|i\s+(?:can\s+)?(?:hear|understand|imagine)\b"
    r"|i\s+can\s+only\s+imagine\b"
    r"|(?:that|it)\s+must\s+(?:be|feel|have\s+been)\b"
    r"|thank\s+you\s+for\s+(?:sharing|trusting|opening)\b"
    r"|i\s+appreciate\s+you\b"
    r"|what\s+you'?re\s+(?:feeling|going\s+through|describing)\b"
    r"|feeling\s+\w+\s+(?:is|can\s+be)\s+(?:understandable|normal|valid)\b"
    r")",
    re.IGNORECASE,
)
_STOP = set("the a an and or but to of in on for with about that this it is are was were be "
            "been being have has had do does did i you he she they we my your me him her them so "
            "just really very much how what when where why who am feel feeling like dont im ive "
            "can cant could would should your you're".split())


def _first_sentence(text: str) -> str:
    t = text.strip()
    m = re.search(r"[.!?]", t)
    return t[: m.start() + 1] if m else t


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOP}


def rescore(reply: str, question: str) -> dict:
    r = reply.strip()
    reflective = bool(_REFLECTIVE.match(r))
    fs = _first_sentence(r)
    overlap = _content_words(fs) & _content_words(question)
    # substance_first: does NOT lead reflective AND names a specific term from the message
    substance_first = (not reflective) and bool(overlap)
    return {
        "reflective_opener": reflective,
        "substance_first": substance_first,
        "opener": fs[:90],
    }


def main() -> None:
    d = json.loads(RES.read_text())
    core, sweep = d["core"], d["sweep"]

    def rate(items, mode, key):
        return 100 * sum(1 for x in items if rescore(x[mode]["reply"], x["message"])[key]) / len(items)

    print(f"=== CORRECTED OPENER QUALITY (#2), n={len(core)}  baseline -> draft ===")
    for key in ["reflective_opener", "substance_first"]:
        print(f"  {key:18s}: {rate(core,'baseline',key):5.1f}% -> {rate(core,'draft',key):5.1f}%")

    # Which openers flip from old-missed to now-caught (audit the detector)
    print("\n=== newly-caught reflective openers (were missed by old detector) ===")
    seen = set()
    for x in core + sweep:
        for mode in ("baseline", "draft"):
            rs = rescore(x[mode]["reply"], x["message"])
            old = x[mode].get("robotic_opener", False)
            if rs["reflective_opener"] and not old and rs["opener"] not in seen:
                seen.add(rs["opener"])
                print(f"  + {rs['opener']}")
    print(f"\n  ({len(seen)} distinct openers the old detector missed)")

    # Substantive (good) openers for contrast
    print("\n=== confirmed SUBSTANCE-FIRST openers (the target pattern) ===")
    seen2 = set()
    for x in core:
        for mode in ("baseline", "draft"):
            rs = rescore(x[mode]["reply"], x["message"])
            if rs["substance_first"] and rs["opener"] not in seen2:
                seen2.add(rs["opener"])
    for o in sorted(seen2)[:12]:
        print(f"  - {o}")


if __name__ == "__main__":
    main()
