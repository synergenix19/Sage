"""Static gate: safety-critical detectors must read RAW user input, never only the translated
message_en (the language contract, ADR 2026-07-16). Root class of #329/#330 — a safety decision
routed through the translator, recall hostage to translation quality on distress-register Khaleeji.

Flags any call to a known safety detector that passes `message_en` WITHOUT also passing raw
(`raw_message`/`safety_text`/`raw`/`text_ar`). Allowlist-with-ticket for legitimate transitional
exceptions (EXEMPT pattern, #227). Exit 1 on any un-allowlisted violation.
Run: python scripts/check_safety_reads_raw.py
"""
import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src" / "sage_poc"

# Detectors whose text argument is a safety decision. A call passing message_en alone is drift.
SAFETY_DETECTORS = ("is_ocd_compulsion", "is_harm_intrusive", "detect_medical_redflag", "evaluate_s7")
# Tokens that signal the raw path is being read (call is conformant / defense-in-depth).
_RAW_TOKENS = ("raw_message", "safety_text", "text_ar", ", raw", "(raw")

# Allowlist: "file:call_fn" -> reason+ticket. Transitional debt stays VISIBLE, not silent.
ALLOWLIST = {
    "nodes/skill_select.py:is_harm_intrusive": "#330 — translation currently catches AR; switching to "
        "raw before AR patterns exist would REGRESS coverage. Conform when harm AR-pattern ticket lands.",
    "nodes/safety_check.py:evaluate_s7": "#330-audit — post-crisis S7 classifier reads message_en; "
        "raw-vs-translated review pending (own row in the audit table).",
}


def main() -> int:
    violations = []
    fn_re = "|".join(SAFETY_DETECTORS)
    call_re = re.compile(rf"\b({fn_re})\s*\(")
    for path in sorted(_SRC.rglob("*.py")):
        rel = str(path.relative_to(_SRC))
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = call_re.search(line)
            if not m:
                continue
            if line.lstrip().startswith(("#", '"', "*", "def ", "async def ")):
                continue  # comment/docstring/definition — the concern is CALL sites passing message_en
            fn = m.group(1)
            if "message_en" in line and not any(tok in line for tok in _RAW_TOKENS):
                key = f"{rel}:{fn}"
                status = "ALLOWLISTED" if key in ALLOWLIST else "VIOLATION"
                violations.append((status, key, i, line.strip()))
    viol = [v for v in violations if v[0] == "VIOLATION"]
    allow = [v for v in violations if v[0] == "ALLOWLISTED"]
    print("safety detectors reading translated message_en without raw (language contract):\n")
    for status, key, ln, src in violations:
        mark = "❌ VIOLATION" if status == "VIOLATION" else "⚠️  allowlisted"
        print(f"  {mark}  {key}  (L{ln})")
        if status == "ALLOWLISTED":
            print(f"        {ALLOWLIST[key]}")
    if viol:
        print(f"\n❌ {len(viol)} safety detector(s) read only message_en. Use safety_text(state) (raw), "
              f"or allowlist-with-ticket in ALLOWLIST.")
        return 1
    print(f"\n✅ every safety detector reads raw (or is allowlisted-with-ticket: {len(allow)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
