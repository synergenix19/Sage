#!/usr/bin/env python3
# tests/experiment_4_4/generate_quality_log.py
#
# Experiment 4.4 — Clinician quality review log generator
#
# NOT a pytest test. Run directly:
#   cd sage-poc && python tests/experiment_4_4/generate_quality_log.py
#
# Requires a live API key (OPENROUTER_API_KEY). Calls both skill_executor_node
# and freeflow_respond_node (real LLM) for each scenario turn, writing:
#   docs/experiment_4_4_quality_log_<date>.json
#
# Each entry includes a blank clinician rubric for manual scoring by three
# independent reviewers. The ≥4.0/5.0 quality KPI is computed once scoring
# is complete (not by this script).
#
# Usage:
#   python tests/experiment_4_4/generate_quality_log.py
#   python tests/experiment_4_4/generate_quality_log.py --scenario S01 --scenario S02
#   python tests/experiment_4_4/generate_quality_log.py --max-turns 5 --dry-run

import asyncio
import argparse
import json
import sys
import copy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).parent.parent.parent
# Ensure both sage_poc and the tests package are importable when run as a script
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO))

from sage_poc.nodes.skill_executor import skill_executor_node
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.skills.schema import load_skill

# Absolute imports — works both as `python script.py` and `python -m ...`
from tests.experiment_4_4.conftest import make_executor_state
from tests.experiment_4_4.scenarios import ALL_SCENARIOS

# Default cooperative follow-up used when a scenario doesn't specify a recurring message.
# Only appropriate for happy-path scenarios where the user is engaged and progressing.
_LONG_MSG = (
    "I have been thinking carefully about what you asked and I feel like I am "
    "making some progress with this exercise today."
)
_DEFAULT_MAX_TURNS = 10  # enough to cover most completion paths without running too long


def _build_initial_state(scenario: dict) -> dict:
    overrides = scenario.get("initial_state_overrides") or {}
    msg = overrides.pop("message_en", _LONG_MSG)
    return make_executor_state(
        skill_id=scenario["skill_id"],
        step_id=scenario["initial_step"],
        message_en=msg,
        **overrides,
    )


def _blank_rubric() -> dict:
    """Clinician scoring rubric — all fields null until manually filled."""
    return {
        "tone_appropriate":       None,   # 1-5: emotionally attuned tone
        "matches_instruction":    None,   # 1-5: response follows step_instruction
        "validation_genuine":     None,   # 1-5: validation feels authentic, not scripted
        "socratic_quality":       None,   # 1-5: open questions invite reflection
        "overall":                None,   # 1-5: holistic quality rating
        "reviewer_notes":         None,
    }


async def _run_scenario(
    scenario: dict,
    max_turns: int = _DEFAULT_MAX_TURNS,
    dry_run: bool = False,
) -> list[dict]:
    """Run one scenario, collecting a log entry per turn."""
    scenario_id = scenario["id"]
    skill_id = scenario["skill_id"]
    state = _build_initial_state(scenario)
    skill = load_skill(skill_id)
    entries: list[dict] = []
    conversation_history: list[dict] = []

    # Recurring message used for turns 2+. Rule scenarios supply their own to keep
    # the conversation context consistent with the state signals the rule relies on.
    recurring_message = scenario.get("_recurring_message", _LONG_MSG)

    resistance_score = scenario.get("_requires_resistance_score")

    for turn in range(1, max_turns + 1):
        # ── Node 5: skill_executor ────────────────────────────────────────────
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch(
                 "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
             ) as mock_resistance:
            mock_resistance.return_value = resistance_score
            exec_result = await skill_executor_node(state)

        step_instruction = exec_result.get("step_instruction", "")
        # Use the authoritative rule_fired flag from skill_executor_node directly.
        # exec_result["rule_fired"] is True when a step_policy rule override fired
        # (action not in advance/complete/stay/None). Fall back to escalation level
        # for L1/L2 audit labelling.
        rule_fired: bool | str | None = exec_result.get("rule_fired") or None
        if exec_result.get("escalation_triggered"):
            rule_fired = exec_result["escalation_triggered"].get("level")

        skill_complete = exec_result.get("skill_complete", False)
        skill_exited   = exec_result.get("active_skill_id") is None

        # ── Node 7: freeflow_respond ──────────────────────────────────────────
        freeflow_state = {
            **state,
            "step_instruction":     step_instruction,
            "executed_step_id":     exec_result.get("executed_step_id"),
            "active_step_id":       exec_result.get("active_step_id"),
            "active_skill_id":      exec_result.get("active_skill_id"),
            "escalation_triggered": exec_result.get("escalation_triggered"),
            "rule_fired":           exec_result.get("rule_fired"),
            # L1 history: accumulated from prior turns so the LLM sees realistic context.
            "conversation_history": list(conversation_history),
        }
        if dry_run:
            llm_response = "[DRY RUN — LLM not called]"
        else:
            ff_result = await freeflow_respond_node(freeflow_state)
            llm_response = ff_result.get("response_en", "")

        # ── Log entry ─────────────────────────────────────────────────────────
        entry = {
            "scenario_id":      scenario_id,
            "scenario_description": scenario.get("description", ""),
            "turn":             turn,
            "state_snapshot": {
                "active_skill_id":   state.get("active_skill_id"),
                "active_step_id":    state.get("active_step_id"),
                "emotional_intensity": state.get("emotional_intensity"),
                "engagement":        state.get("engagement"),
                "resistance_history": list(state.get("resistance_history") or []),
                "engagement_trajectory": list(state.get("engagement_trajectory") or []),
                "clinical_flags":    list(state.get("clinical_flags") or []),
                "new_clinical_flags_turn": list(state.get("new_clinical_flags_turn") or []),
                "therapeutic_profile": copy.deepcopy(state.get("therapeutic_profile") or {}),
            },
            "step_instruction": step_instruction,
            "rule_fired":       rule_fired,
            "skill_complete":   skill_complete,
            "skill_exited":     skill_exited,
            "llm_response":     llm_response,
            "rubric":           _blank_rubric(),
        }
        entries.append(entry)

        # ── Advance state for next turn ───────────────────────────────────────
        # Accumulate history so L1 reflects prior conversation context.
        conversation_history.append({"role": "user",      "content": state["message_en"]})
        conversation_history.append({"role": "assistant", "content": llm_response or ""})

        state["active_skill_id"] = exec_result.get("active_skill_id")
        state["active_step_id"]  = exec_result.get("active_step_id", state["active_step_id"])
        state["resistance_history"] = list(exec_result.get("resistance_history") or state["resistance_history"])
        state["conversation_history"] = list(conversation_history)
        # Use the scenario's recurring message (matches state signals) rather than
        # the generic cooperative _LONG_MSG, which contradicts rule instructions.
        state["message_en"] = recurring_message
        state["raw_message"] = recurring_message
        state["path"] = []
        state["new_clinical_flags_turn"] = []  # flags only new once

        if skill_complete or skill_exited:
            break

    return entries


async def _main(
    scenario_ids: list[str] | None = None,
    max_turns: int = _DEFAULT_MAX_TURNS,
    dry_run: bool = False,
) -> None:
    scenarios = ALL_SCENARIOS
    if scenario_ids:
        scenarios = [s for s in scenarios if s["id"] in scenario_ids]
        if not scenarios:
            print(f"No scenarios matched: {scenario_ids}", file=sys.stderr)
            sys.exit(1)

    print(f"Generating quality log for {len(scenarios)} scenario(s), max_turns={max_turns}")
    if dry_run:
        print("DRY RUN — LLM calls skipped")

    all_entries: list[dict] = []
    for scenario in scenarios:
        print(f"  Running {scenario['id']}: {scenario['description']}")
        try:
            entries = await _run_scenario(scenario, max_turns=max_turns, dry_run=dry_run)
            all_entries.extend(entries)
            print(f"    → {len(entries)} turns logged")
        except Exception as exc:
            print(f"    ✗ FAILED: {exc}", file=sys.stderr)
            all_entries.append({
                "scenario_id": scenario["id"],
                "error": str(exc),
            })

    # Write output
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = docs_dir / f"experiment_4_4_quality_log_{date_str}.json"

    payload = {
        "experiment": "4.4",
        "generated_at": datetime.now().isoformat(),
        "scenario_count": len(scenarios),
        "total_turns": len([e for e in all_entries if "turn" in e]),
        "kpi_targets": {
            "completion_rate": "≥80% (≥6/7 happy-path scenarios)",
            "quality_score":   "≥4.0/5.0 clinician-scored",
            "rule_accuracy":   "binary per rule (see test_rule_accuracy.py)",
            "turn_latency":    "<3s p95 (see test_latency.py)",
        },
        "rubric_fields": {
            "tone_appropriate":    "1-5: emotionally attuned tone for this therapeutic moment",
            "matches_instruction": "1-5: response aligns with the step_instruction directive",
            "validation_genuine":  "1-5: validation feels authentic (not scripted or hollow)",
            "socratic_quality":    "1-5: open questions genuinely invite reflection",
            "overall":             "1-5: holistic quality — would a clinician use this response",
        },
        "entries": all_entries,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nLog written to: {out_path}")
    print(f"Total entries: {len(all_entries)}")
    print(
        "\nNext step: three independent clinical reviewers fill in the 'rubric' "
        "blocks. Mean overall ≥4.0 across all reviewed turns satisfies the KPI."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Experiment 4.4 clinician quality log")
    parser.add_argument("--scenario", dest="scenarios", action="append",
                        help="Scenario ID to include (repeatable). Default: all 20.")
    parser.add_argument("--max-turns", type=int, default=_DEFAULT_MAX_TURNS,
                        help=f"Max turns per scenario (default {_DEFAULT_MAX_TURNS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip LLM calls; log placeholder responses")
    args = parser.parse_args()

    asyncio.run(_main(
        scenario_ids=args.scenarios,
        max_turns=args.max_turns,
        dry_run=args.dry_run,
    ))
