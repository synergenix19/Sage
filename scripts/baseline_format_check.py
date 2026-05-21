#!/usr/bin/env python3
"""
FORMAT VIOLATION baseline run — structured 10-turn conversation.
Covers all major graph paths. Captures [FORMAT VIOLATION] hits per turn.

Run: uv run python scripts/baseline_format_check.py
"""
import asyncio
import contextlib
import io
import os
import sys
from pathlib import Path

# Resolve env before importing sage_poc (avoids missing-key errors)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sage_poc.graph import build_graph  # noqa: E402

# ---------------------------------------------------------------------------
# Test sequence — matches the 10-turn plan from the audit design document
# ---------------------------------------------------------------------------
TURNS = [
    ("Hi, I've been feeling stressed",
     "freeflow / no skill — baseline for L0 prohibition"),
    ("I keep thinking everything is my fault",
     "CBT activate — skill JSON enters L3"),
    ("My intensity is really high right now",
     "CBT validate_only hold — step_policy instruction path"),
    ("What does catastrophising mean?",
     "info_request mid-skill — knowledge snippet path"),
    ("I've been drinking more than usual",
     "clinical flag — substance_use adaptation"),
    ("والله أنا تعبان من كل شي",
     "Arabic freeflow — translation path"),
    ("I can't breathe, I'm panicking, my heart is racing, I'm losing it",
     "grounding trigger — grounding skill JSON enters L3"),
    ("I can't sleep at all",
     "sleep_hygiene skill — sleep JSON enters L3"),
    ("ok",
     "low-effort response — low_confidence_respond path"),
    ("Thanks, I'm feeling better",
     "session close — clean freeflow, no skill active"),
]


def _make_state() -> dict:
    return {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


async def run_baseline() -> list[dict]:
    graph = build_graph()
    state = _make_state()
    records = []

    for idx, (message, label) in enumerate(TURNS, start=1):
        state["raw_message"] = message

        captured = io.StringIO()
        error_msg = None
        result = None

        try:
            with contextlib.redirect_stdout(captured):
                result = await graph.ainvoke(state)
        except Exception as exc:
            error_msg = str(exc)

        stdout_text = captured.getvalue()
        violations = [ln.strip() for ln in stdout_text.splitlines()
                      if "[FORMAT VIOLATION]" in ln]

        record = {
            "turn": idx,
            "label": label,
            "message": message,
            "path": result.get("path", []) if result else [],
            "active_skill": result.get("active_skill_id") if result else None,
            "executed_step": result.get("executed_step_id") if result else None,
            "response": (result.get("response") or "")[:300] if result else "",
            "response_en": (result.get("response_en") or "")[:300] if result else "",
            "violations": violations,
            "error": error_msg,
        }
        records.append(record)

        if result:
            state = {
                **_make_state(),
                "active_skill_id": result.get("active_skill_id"),
                "active_step_id": result.get("active_step_id"),
                "conversation_history": result.get("conversation_history", []),
                "turn_count": result.get("turn_count", 0),
                "engagement": result.get("engagement", 7),
                "emotional_intensity": result.get("emotional_intensity", 5),
                "clinical_flags": result.get("clinical_flags", []),
            }

    return records


def _report(records: list[dict]) -> None:
    sep = "=" * 72
    thin = "─" * 72

    print(f"\n{sep}")
    print("  FORMAT VIOLATION BASELINE REPORT")
    print(f"  Sage POC — post-persona-fix run")
    print(sep)

    violation_turns: list[int] = []
    clean_turns: list[int] = []

    for r in records:
        has_violation = bool(r["violations"])
        has_error = bool(r["error"])
        status = "VIOLATION" if has_violation else ("ERROR" if has_error else "CLEAN")

        if has_violation:
            violation_turns.append(r["turn"])
        elif not has_error:
            clean_turns.append(r["turn"])

        print(f"\n{thin}")
        print(f"Turn {r['turn']:>2}  [{status}]  {r['label']}")
        print(f"  Input:  {r['message'][:80]}")
        print(f"  Path:   {' → '.join(r['path']) or '(none)'}")
        if r["active_skill"]:
            print(f"  Skill:  {r['active_skill']} / step: {r['executed_step']}")
        resp_preview = r["response"].replace("\n", " ")
        print(f"  Reply:  {resp_preview[:220]}")
        if has_violation:
            for v in r["violations"]:
                print(f"  !! {v}")
        if has_error:
            print(f"  ERROR: {r['error'][:120]}")

    print(f"\n{sep}")
    total = len(records)
    print(f"  SUMMARY  {total} turns total")
    print(f"  Violations : {len(violation_turns)} — turns {violation_turns or 'none'}")
    print(f"  Clean      : {len(clean_turns)} — turns {clean_turns}")
    errors = [r['turn'] for r in records if r['error']]
    if errors:
        print(f"  Errors     : turns {errors}")
    print()

    if violation_turns:
        print("  INTERPRETATION:")
        skill_turns = {2, 3, 4, 7, 8}
        non_skill_turns = {1, 5, 6, 9, 10}
        only_skill = all(t in skill_turns for t in violation_turns)
        includes_non_skill = any(t in non_skill_turns for t in violation_turns)
        if only_skill:
            print("  Violations confined to skill-active turns.")
            print("  => L0 prohibition is working. Remaining source: skill JSON em dashes.")
            print("  => Item 1 (CMS cleanup) is the correct next fix.")
        elif includes_non_skill:
            print("  Violations on non-skill turns detected.")
            print("  => L0 prohibition may not be fully suppressing output.")
            print("  => Investigate whether persona prompt is being composed first,")
            print("     or whether another context source is reintroducing the pattern.")
    else:
        print("  INTERPRETATION:")
        print("  Zero violations detected across all turns.")
        print("  => L0 prohibition is strong enough to override L3 skill context.")
        print("  => Skill JSON cleanup (Item 1) becomes polish rather than critical.")
        print("  => Still proceed with CMS cleanup — removes reliance on probabilistic override.")

    print(sep)


if __name__ == "__main__":
    records = asyncio.run(run_baseline())
    _report(records)
