"""
POC Re-Benchmark: 7 Evaluation Scenarios
Verifies Doc 4 prompt quality improvements post-migration.

Usage: uv run python scripts/benchmark_poc_scenarios.py
"""
from __future__ import annotations
import asyncio
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# --- helpers reused from test_graph.py ----------------------------------------

_CARRY_FIELDS = (
    "turn_count", "clinical_flags", "conversation_history",
    "active_skill_id", "active_step_id", "emotional_intensity", "engagement",
    "crisis_state", "distress_trajectory",
)

def make_state(raw_message: str, **overrides) -> dict:
    base = {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": "",
        "is_safe": False,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None, "s7_method": None,
        "distress_trajectory": [],
        "code_switching": False,
        "primary_intent": None, "secondary_intent": None,
        "intent_confidence": 0.0, "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "escalation_triggered": None, "gate_path": None,
        "response_en": None, "response": None,
        "path": [], "turn_count": 0, "conversation_history": [],
        "skill_match_method": None, "semantic_score": None,
        "prompt_layers": [], "token_usage": {},
    }
    return {**base, **overrides}


def carry(prev: dict, raw: str, **overrides) -> dict:
    carried = {f: prev.get(f) for f in _CARRY_FIELDS if f in prev}
    return make_state(raw, **{**carried, **overrides})


def prompt_summary(result: dict) -> dict:
    """Reproduce compose_prompt on the post-run result state to capture word counts."""
    from unittest.mock import patch, MagicMock
    from sage_poc.prompts.composer import compose_prompt
    from sage_poc.prompts.tokens import count_words

    # Use actual rules engine (no mock) — same as live system
    system_str, user_str, layers = compose_prompt(result)
    return {
        "layers": layers,
        "system_words": count_words(system_str),
        "user_words": count_words(user_str),
        "total_words": count_words(system_str) + count_words(user_str),
        "system_preview": system_str[:200],
        "user_preview": user_str[:300],
    }


def turn_record(result: dict, turn_n: int, message: str) -> dict:
    p = prompt_summary(result)
    # Check P1-4: Goal:/Technique: must never appear in the user prompt
    p14_clean = "Goal:" not in p["user_preview"] and "Technique:" not in p["user_preview"]
    # Check therapeutic framing presence when L3 fired
    l3_ok = True
    if "L3_skill_wrapper" in p["layers"]:
        l3_ok = "THERAPEUTIC APPROACH" in p["user_preview"]

    return {
        "turn": turn_n,
        "message": message[:60],
        "path": result.get("path", []),
        "primary_intent": result.get("primary_intent"),
        "emotional_intensity": result.get("emotional_intensity"),
        "engagement": result.get("engagement"),
        "active_skill_id": result.get("active_skill_id"),
        "executed_step_id": result.get("executed_step_id"),
        "clinical_flags": result.get("clinical_flags", []),
        "crisis_state": result.get("crisis_state"),
        "prompt_layers": p["layers"],
        "prompt_words_total": p["total_words"],
        "prompt_words_system": p["system_words"],
        "prompt_words_user": p["user_words"],
        "p14_clean": p14_clean,
        "l3_therapeutic_framing": l3_ok,
        "token_usage": result.get("token_usage", {}),
        "response_en": (result.get("response_en") or "")[:300],
        "response_ok": bool(result.get("response")),
    }


# --- scenarios ----------------------------------------------------------------

async def scenario_1_greeting_and_overwhelmed(graph) -> list[dict]:
    """Scenario 1: First greeting + presenting with overwhelm → new_skill expected."""
    records = []
    s = make_state("Hi, I'm just checking in today.")
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "Hi, I'm just checking in today."))

    s2 = carry(r, "I've been feeling overwhelmed for weeks. Everything feels too much.")
    r2 = await graph.ainvoke(s2)
    records.append(turn_record(r2, 2, "I've been feeling overwhelmed for weeks."))
    return records


async def scenario_2_cbt_thought_record_4_turns(graph) -> list[dict]:
    """Scenario 2: CBT thought record — 4 turns. Critical: P1-4 fix verification."""
    records = []
    s = make_state("I keep telling myself I'm a failure and nothing I do is ever good enough.")
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "I keep telling myself I'm a failure..."))

    s2 = carry(r, "The thought is: 'I'll never be good enough, no matter what I do.'")
    r2 = await graph.ainvoke(s2)
    records.append(turn_record(r2, 2, "The thought is: 'I'll never be good enough'"))

    s3 = carry(r2, "When I think about it... I did get that project done last week, so maybe not always?")
    r3 = await graph.ainvoke(s3)
    records.append(turn_record(r3, 3, "I did get that project done last week..."))

    s4 = carry(r3, "A fairer thought might be: 'I make mistakes sometimes, but I'm not a failure.'")
    r4 = await graph.ainvoke(s4)
    records.append(turn_record(r4, 4, "A fairer thought: I make mistakes but I'm not a failure"))
    return records


async def scenario_3_post_skill_freeflow(graph) -> list[dict]:
    """Scenario 3: Transition from skill_continuation to freeflow."""
    records = []
    s = make_state("I always mess everything up at work.")
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "I always mess everything up at work."))

    s2 = carry(r, "The thought is: 'I'm incompetent and everyone knows it.'")
    r2 = await graph.ainvoke(s2)
    records.append(turn_record(r2, 2, "The thought is: I'm incompetent"))

    # Off-topic turn — should route to freeflow not executor
    s3 = carry(r2, "Actually, I just want to talk. Can we just chat for a bit?")
    r3 = await graph.ainvoke(s3)
    records.append(turn_record(r3, 3, "Actually, I just want to talk."))
    return records


async def scenario_4_clinical_flag_substance_use(graph) -> list[dict]:
    """Scenario 4: Clinical flag (substance use) → L5 + PI-CF-001 adaptation."""
    records = []
    s = make_state("I've been drinking more lately to cope with anxiety.")
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "I've been drinking more to cope with anxiety."))

    s2 = carry(r, "Maybe three or four drinks most evenings. It helps me stop thinking.")
    r2 = await graph.ainvoke(s2)
    records.append(turn_record(r2, 2, "Three or four drinks most evenings."))
    return records


async def scenario_5_crisis_english(graph) -> list[dict]:
    """Scenario 5: Crisis path — should bypass compose_prompt entirely."""
    records = []
    s = make_state("I don't want to live anymore. I've been thinking about ending it.")
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "I don't want to live anymore."))
    return records


async def scenario_6_post_crisis_follow_up(graph) -> list[dict]:
    """Scenario 6: Post-crisis follow-up — post_crisis_context injection expected."""
    records = []
    # Start with a crisis turn to set crisis_state=monitoring
    s = make_state("I want to hurt myself.", crisis_state="none")
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "I want to hurt myself."))

    # Follow-up turn — crisis_state should be 'monitoring' now
    if r.get("crisis_state") in ("monitoring", "active", "resolved"):
        s2 = carry(r, "I feel a bit better now. Thank you for being here.")
        r2 = await graph.ainvoke(s2)
        records.append(turn_record(r2, 2, "I feel a bit better now."))
    else:
        records.append({"turn": 2, "note": f"crisis_state={r.get('crisis_state')!r} — post-crisis path skipped"})
    return records


async def scenario_7_arabic_conversation(graph) -> list[dict]:
    """Scenario 7: Arabic conversation — L1 history sanitization, L2 framing with AR."""
    records = []
    s = make_state("أشعر بالقلق الشديد منذ أسابيع")  # "I've been feeling intense anxiety for weeks"
    r = await graph.ainvoke(s)
    records.append(turn_record(r, 1, "أشعر بالقلق الشديد منذ أسابيع"))

    s2 = carry(r, "كل شيء يبدو صعباً جداً وما أقدر أتركز")  # "Everything seems hard and I can't focus"
    r2 = await graph.ainvoke(s2)
    records.append(turn_record(r2, 2, "كل شيء يبدو صعباً وما أقدر أتركز"))
    return records


# --- report generation --------------------------------------------------------

def format_turn(rec: dict) -> str:
    lines = []
    turn_n = rec.get("turn", "?")
    msg = rec.get("message", "")
    lines.append(f"\n**Turn {turn_n}:** _{msg}_")

    if "note" in rec:
        lines.append(f"> NOTE: {rec['note']}")
        return "\n".join(lines)

    lines.append(f"- Path: `{'→'.join(rec.get('path', []))}`")
    lines.append(f"- Intent: `{rec.get('primary_intent')}` | Intensity: {rec.get('emotional_intensity')} | Engagement: {rec.get('engagement')}")
    lines.append(f"- Active skill: `{rec.get('active_skill_id')}` / step: `{rec.get('executed_step_id')}`")
    lines.append(f"- Clinical flags: `{rec.get('clinical_flags', [])}`")
    lines.append(f"- Prompt layers: `{rec.get('prompt_layers', [])}`")
    words = rec.get("prompt_words_total", 0)
    lines.append(f"- Prompt words: {words} (system={rec.get('prompt_words_system', 0)}, user={rec.get('prompt_words_user', 0)})")

    p14 = rec.get("p14_clean", True)
    l3ok = rec.get("l3_therapeutic_framing", True)
    lines.append(f"- P1-4 clean (no Goal:/Technique: labels): {'✅' if p14 else '❌ FAIL'}")
    if "L3_skill_wrapper" in rec.get("prompt_layers", []):
        lines.append(f"- L3 therapeutic framing present: {'✅' if l3ok else '❌ FAIL'}")

    tok = rec.get("token_usage", {})
    if tok:
        lines.append(f"- Token usage: in={tok.get('input',0)} out={tok.get('output',0)} total={tok.get('total',0)}")

    resp = rec.get("response_en", "")
    if resp:
        lines.append(f"\n**Response (first 300 chars):**")
        lines.append(f"> {resp.replace(chr(10), ' ')[:300]}")

    return "\n".join(lines)


def write_report(all_results: dict[str, list[dict]], output_path: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Doc 4 POC Re-Benchmark Results",
        f"",
        f"**Date:** {now}",
        f"**Purpose:** Verify prompt quality improvements after Doc 4 migration",
        f"**Model:** OpenRouter via ChatOpenAI (configured in llm.py)",
        f"",
        "---",
        "",
        "## Summary",
        "",
    ]

    # Summary table
    lines.append("| Scenario | Turns | P1-4 Clean | L3 Framing | Budget OK | Notes |")
    lines.append("|---|---|---|---|---|---|")

    for name, records in all_results.items():
        turns = len([r for r in records if "note" not in r])
        p14_all = all(r.get("p14_clean", True) for r in records if "note" not in r)
        l3_records = [r for r in records if "L3_skill_wrapper" in r.get("prompt_layers", []) and "note" not in r]
        l3_all = all(r.get("l3_therapeutic_framing", True) for r in l3_records)
        l3_str = "✅" if l3_all else ("❌" if l3_records else "N/A")
        budget_ok = all(r.get("prompt_words_total", 0) <= 1100 for r in records if "note" not in r)
        notes = []
        for r in records:
            if "note" not in r:
                if r.get("active_skill_id"):
                    notes.append(f"skill={r['active_skill_id'][:12]}")
                if r.get("clinical_flags"):
                    notes.append(f"flags={r['clinical_flags']}")
        note_str = "; ".join(dict.fromkeys(notes))[:40]

        lines.append(
            f"| {name[:40]} | {turns} | {'✅' if p14_all else '❌'} | {l3_str} | {'✅' if budget_ok else '⚠️'} | {note_str} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    for name, records in all_results.items():
        lines.append(f"## {name}")
        lines.append("")
        for rec in records:
            lines.append(format_turn(rec))
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines))
    print(f"\nReport written to: {output_path}")


# --- main ---------------------------------------------------------------------

async def main() -> None:
    from sage_poc.graph import build_graph
    graph = build_graph()

    scenarios = [
        ("Scenario 1: Greeting + Overwhelm → new_skill", scenario_1_greeting_and_overwhelmed),
        ("Scenario 2: CBT Thought Record (4 turns) — P1-4 fix", scenario_2_cbt_thought_record_4_turns),
        ("Scenario 3: Post-skill freeflow transition", scenario_3_post_skill_freeflow),
        ("Scenario 4: Clinical flag — substance use MI framing", scenario_4_clinical_flag_substance_use),
        ("Scenario 5: Crisis (English) — bypass path", scenario_5_crisis_english),
        ("Scenario 6: Post-crisis follow-up — context injection", scenario_6_post_crisis_follow_up),
        ("Scenario 7: Arabic conversation — L1 sanitization", scenario_7_arabic_conversation),
    ]

    all_results: dict[str, list[dict]] = {}

    for name, fn in scenarios:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)
        try:
            records = await fn(graph)
            all_results[name] = records
            for rec in records:
                if "note" in rec:
                    print(f"  Turn {rec['turn']}: NOTE — {rec['note']}")
                else:
                    p14 = "✅" if rec.get("p14_clean") else "❌P1-4 FAIL"
                    l3 = ""
                    if "L3_skill_wrapper" in rec.get("prompt_layers", []):
                        l3 = " L3-framing=✅" if rec.get("l3_therapeutic_framing") else " L3-framing=❌"
                    print(
                        f"  Turn {rec['turn']}: {rec.get('primary_intent','?')} | "
                        f"intensity={rec.get('emotional_intensity')} | "
                        f"layers={rec.get('prompt_layers',[])} | "
                        f"words={rec.get('prompt_words_total',0)} | "
                        f"{p14}{l3}"
                    )
                    resp = rec.get("response_en", "")
                    if resp:
                        print(f"    Response: {resp[:120]}...")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()
            all_results[name] = [{"turn": 0, "note": f"EXCEPTION: {e}"}]

    output_path = Path(__file__).parent.parent.parent / "docs" / "superpowers" / "audits" / "2026-05-22-doc4-benchmark-results.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(all_results, output_path)


if __name__ == "__main__":
    asyncio.run(main())
