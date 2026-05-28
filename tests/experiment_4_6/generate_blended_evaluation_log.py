#!/usr/bin/env python3
# tests/experiment_4_6/generate_blended_evaluation_log.py
#
# Experiment 4.6 — Blended intent evaluation log generator
#
# NOT a pytest test. Run directly:
#   cd sage-poc && python tests/experiment_4_6/generate_blended_evaluation_log.py
#
# Requires OPENROUTER_API_KEY. For each scenario, mocks intent_route to inject
# the scenario's primary/secondary intents, then calls freeflow_respond_node (or
# skill_executor_node when route==skill_executor), and logs:
#   scenario, route, llm_response.
#
# Reviewers fill in successfully_blended: true/false.
# KPI: >=80% true (>=16/20) = PASS.
#
# Usage:
#   python tests/experiment_4_6/generate_blended_evaluation_log.py
#   python tests/experiment_4_6/generate_blended_evaluation_log.py --scenario B01 --scenario B02
#   python tests/experiment_4_6/generate_blended_evaluation_log.py --dry-run

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock

_REPO = Path(__file__).parent.parent.parent
# Ensure both sage_poc and the tests package are importable when run as a script
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO))

from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.skill_executor import skill_executor_node

from tests.experiment_4_6.conftest import make_compose_state
from tests.experiment_4_6.scenarios import ALL_SCENARIOS


def _build_scenario_state(scenario: dict) -> dict:
    """Build a compose-level state dict from a scenario definition."""
    return make_compose_state(
        message_en=scenario["message"],
        raw_message=scenario["message"],
        primary_intent=scenario["primary_intent"],
        secondary_intent=scenario["secondary_intent"],
        intent_confidence=scenario["confidence"],
        emotional_intensity=scenario["emotional_intensity"],
        engagement=scenario["engagement"],
        active_skill_id=scenario["active_skill_id"],
        # No history: single-turn evaluation
        conversation_history=[],
        # No knowledge pre-loaded: this log tests blending in the response,
        # not retrieval accuracy. For knowledge scenarios, the LLM will respond
        # with its parametric knowledge.
        knowledge_passages=[],
        knowledge_abstain=False,
    )


async def _run_scenario(scenario: dict, dry_run: bool = False) -> dict:
    """Run one scenario and return a log entry dict."""
    scenario_id = scenario["id"]
    expected_route = scenario["expected_route"]
    state = _build_scenario_state(scenario)
    llm_response = ""

    if dry_run:
        llm_response = "[DRY RUN — LLM not called]"
    else:
        try:
            if expected_route == "skill_executor":
                # skill_executor needs a step_instruction; mock it if absent
                if not state.get("step_instruction") and state.get("active_skill_id"):
                    state["step_instruction"] = (
                        f"Continue the {state['active_skill_id']} skill. "
                        f"Address the user's secondary intent: {scenario['secondary_intent']}."
                    )
                # skill_executor → freeflow_respond pipeline
                with patch(
                    "sage_poc.nodes.skill_executor._score_resistance_via_rules_service",
                    new=AsyncMock(return_value=None),
                ):
                    exec_result = await skill_executor_node(state)

                freeflow_state = {
                    **state,
                    "step_instruction": exec_result.get("step_instruction", state.get("step_instruction", "")),
                    "executed_step_id": exec_result.get("executed_step_id"),
                    "active_step_id": exec_result.get("active_step_id"),
                    "active_skill_id": exec_result.get("active_skill_id"),
                    "escalation_triggered": exec_result.get("escalation_triggered"),
                    "rule_fired": exec_result.get("rule_fired"),
                }
                ff_result = await freeflow_respond_node(freeflow_state)
                llm_response = ff_result.get("response_en", "")
            elif expected_route in ("freeflow", "skill_select"):
                # For freeflow/skill_select routes, call freeflow_respond directly
                # (skill_select would normally run semantic matching; we skip it here
                # since the scenario already has the primary intent set)
                ff_result = await freeflow_respond_node(state)
                llm_response = ff_result.get("response_en", "")
            else:
                # crisis, gate: these routes don't produce an LLM response in the
                # normal sense. Log a placeholder.
                llm_response = (
                    f"[SKIPPED — route={expected_route!r} does not call freeflow_respond]"
                )
        except Exception as exc:
            llm_response = f"[ERROR: {exc}]"

    return {
        "scenario_id": scenario_id,
        "description": scenario["description"],
        "primary_intent": scenario["primary_intent"],
        "secondary_intent": scenario["secondary_intent"],
        "message": scenario["message"],
        "expected_route": expected_route,
        "knowledge_expected": scenario["knowledge_expected"],
        "llm_response": llm_response,
        "successfully_blended": None,   # filled in by human reviewer
        "reviewer_notes": None,
    }


async def _main(
    scenario_ids: list[str] | None = None,
    dry_run: bool = False,
) -> None:
    scenarios = ALL_SCENARIOS
    if scenario_ids:
        scenarios = [s for s in scenarios if s["id"] in scenario_ids]
        if not scenarios:
            print(f"No scenarios matched: {scenario_ids}", file=sys.stderr)
            sys.exit(1)

    print(f"Generating blended evaluation log for {len(scenarios)} scenario(s)")
    if dry_run:
        print("DRY RUN — LLM calls skipped")

    entries: list[dict] = []
    for scenario in scenarios:
        print(f"  Running {scenario['id']}: {scenario['description']}")
        try:
            entry = await _run_scenario(scenario, dry_run=dry_run)
            entries.append(entry)
            blended_preview = entry["llm_response"][:80].replace("\n", " ")
            print(f"    route={entry['expected_route']!r}, response: {blended_preview!r}...")
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            entries.append({
                "scenario_id": scenario["id"],
                "description": scenario["description"],
                "primary_intent": scenario["primary_intent"],
                "secondary_intent": scenario["secondary_intent"],
                "message": scenario["message"],
                "expected_route": scenario["expected_route"],
                "knowledge_expected": scenario["knowledge_expected"],
                "llm_response": f"[ERROR: {exc}]",
                "successfully_blended": None,
                "reviewer_notes": None,
            })

    docs_dir = _REPO / "docs"
    docs_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = docs_dir / f"experiment_4_6_blended_evaluation_log_{date_str}.json"

    payload = {
        "experiment": "4.6",
        "generated_at": datetime.now().isoformat(),
        "scenario_count": len(scenarios),
        "kpi_target": ">=80% successfully_blended (>=16/20 scenarios)",
        "reviewer_instructions": {
            "successfully_blended": (
                "Set to true if: (1) the primary intent is handled correctly "
                "(e.g. skill step delivered, empathy shown, info provided as appropriate), "
                "AND (2) the secondary intent is visibly acknowledged or addressed in the response "
                "(e.g. a factual question is answered, small talk is gently acknowledged). "
                "Set to false if the response ignores the secondary intent entirely or "
                "handles the primary intent incorrectly."
            ),
            "reviewer_notes": "Optional. Record any concerns about clinical safety, tone, or accuracy.",
        },
        "harness_notes": (
            "Each scenario is a single-turn evaluation with no conversation history. "
            "For skill_executor routes, skill_executor_node runs first to set step_instruction, "
            "then freeflow_respond_node generates the response. "
            "For freeflow/skill_select routes, freeflow_respond_node is called directly with "
            "the scenario's intent fields pre-set (skill_select routing is bypassed). "
            "Crisis (B16, B17) and gate (B19, B20) routes do not call freeflow_respond — "
            "those entries are placeholders and count as successfully_blended=false for KPI purposes."
        ),
        "entries": entries,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nLog written to: {out_path}")
    print(f"Total entries: {len(entries)}")
    print(
        "\nNext step: reviewers fill in 'successfully_blended' for each entry. "
        ">=16/20 true = KPI pass."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Experiment 4.6 blended intent evaluation log"
    )
    parser.add_argument(
        "--scenario", dest="scenarios", action="append",
        help="Scenario ID to include (repeatable, e.g. --scenario B01 --scenario B02). Default: all 20.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip LLM calls; write placeholder responses",
    )
    args = parser.parse_args()

    asyncio.run(_main(
        scenario_ids=args.scenarios,
        dry_run=args.dry_run,
    ))
