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
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

_REPO = Path(__file__).parent.parent.parent
# Ensure both sage_poc and the tests package are importable when run as a script
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO))

from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.skill_executor import skill_executor_node

from tests.experiment_4_6.conftest import make_compose_state
from tests.experiment_4_6.scenarios import ALL_SCENARIOS


# ── Knowledge stubs ───────────────────────────────────────────────────────────
# In the standalone script context, _get_pool() returns None (FastAPI lifespan
# never runs), so knowledge_lookup always abstains. For scenarios that expect
# knowledge injection (primary or secondary intent == "info_request"), we mock
# _get_pool and PostgresKnowledgeRepository.retrieve to return a single
# representative passage. This lets the LLM weave evidence into its response,
# which is what the blended-intent KPI is measuring. Single-passage stubs are
# intentional: multi-passage ranking is Experiment 4.5's scope, not 4.6's.
_KNOWLEDGE_STUBS: dict[str, KnowledgePassage] = {
    "B01": KnowledgePassage(
        text="Cognitive Behavioral Therapy (CBT) is one of the most extensively researched psychological treatments, with strong evidence for depression, anxiety disorders, and many other conditions.",
        source_id="cbt-001-en", citation="Beck (1979)", relevance_score=0.91,
    ),
    "B02": KnowledgePassage(
        text="Behavioral Activation (BA) is an evidence-based treatment for depression that increases engagement with positively reinforcing activities.",
        source_id="ba-001-en", citation="Lewinsohn (1974)", relevance_score=0.88,
    ),
    "B03": KnowledgePassage(
        text="Motivational Interviewing (MI) is a collaborative, goal-oriented communication style shown to be effective for eliciting and strengthening motivation for change.",
        source_id="mi-001-en", citation="Miller & Rollnick (2013)", relevance_score=0.87,
    ),
    "B04": KnowledgePassage(
        text="Assertive communication training has evidence supporting its effectiveness in improving interpersonal relationships, reducing anxiety, and increasing self-efficacy.",
        source_id="assertive-001-en", citation="Alberti & Emmons (1974)", relevance_score=0.84,
    ),
    "B05": KnowledgePassage(
        text="Cognitive Behavioral Therapy (CBT) targets negative thinking patterns and behaviours. It is among the most evidence-supported approaches for depression and anxiety.",
        source_id="cbt-001-en", citation="Beck (1979)", relevance_score=0.90,
    ),
    "B06": KnowledgePassage(
        text="Cognitive Behavioral Therapy including exposure therapy is the gold-standard treatment for panic disorder, with response rates of 70–90% in clinical trials.",
        source_id="cbt-anxiety-001-en", citation="Barlow (2002)", relevance_score=0.89,
    ),
    "B07": KnowledgePassage(
        text="Exercise has strong evidence as an adjunct treatment for depression, with studies showing reductions in depressive symptoms comparable to antidepressant medication.",
        source_id="ba-exercise-001-en", citation="Blumenthal et al. (2007)", relevance_score=0.86,
    ),
    "B10": KnowledgePassage(
        text="Cognitive Behavioral Therapy (CBT) is a structured, time-limited psychological therapy that focuses on the relationship between thoughts, feelings, and behaviours.",
        source_id="cbt-001-en", citation="Beck (1979)", relevance_score=0.91,
    ),
    "B11": KnowledgePassage(
        text="Psychotherapy, including CBT and other evidence-based modalities, is effective for the majority of people with common mental health conditions such as depression and anxiety.",
        source_id="psychoed-001-en", citation="APA (2012)", relevance_score=0.87,
    ),
    "B12": KnowledgePassage(
        text="Dialectical Behavior Therapy (DBT) was developed by Marsha Linehan. Unlike standard CBT, it emphasises dialectical thinking, radical acceptance, and has a strong skills-training component covering mindfulness, distress tolerance, emotion regulation, and interpersonal effectiveness.",
        source_id="dbt-001-en", citation="Linehan (1993)", relevance_score=0.90,
    ),
    "B13": KnowledgePassage(
        text="Mindfulness-Based Cognitive Therapy (MBCT) combines mindfulness practices with CBT elements and is particularly effective for preventing relapse in recurrent depression.",
        source_id="mbct-001-en", citation="Segal et al. (2002)", relevance_score=0.88,
    ),
    "B18": KnowledgePassage(
        text="CBT has response rates of 50–60% for depression and 60–80% for anxiety disorders in randomised controlled trials, making it among the most supported psychological treatments.",
        source_id="cbt-outcomes-001-en", citation="Hofmann et al. (2012)", relevance_score=0.89,
    ),
}


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
        # State starts with no pre-loaded passages. For info_request scenarios,
        # _KNOWLEDGE_STUBS + the mock context in _run_scenario supply passages
        # via the knowledge_lookup tool rather than pre-injecting them here.
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
        # Build knowledge mock context for scenarios where info_request intent is
        # present (primary or secondary). _get_pool() returns None in standalone
        # script context (FastAPI lifespan never runs), causing knowledge_lookup to
        # always abstain. Mock the pool and repository so the LLM receives a real
        # passage and can weave evidence into the response — which is what the
        # blended-intent KPI is measuring. nullcontext() for non-knowledge scenarios.
        stub = _KNOWLEDGE_STUBS.get(scenario_id)
        if stub:
            _mock_repo = MagicMock()
            _mock_repo.retrieve = AsyncMock(
                return_value=KnowledgeResult(passages=[stub], abstain=False)
            )
            _pool_ctx = patch(
                "sage_poc.nodes.tools.knowledge_lookup._get_pool",
                return_value=MagicMock(),
            )
            _repo_ctx = patch(
                "sage_poc.nodes.tools.knowledge_lookup.PostgresKnowledgeRepository",
                return_value=_mock_repo,
            )
        else:
            _pool_ctx = nullcontext()
            _repo_ctx = nullcontext()

        try:
            with _pool_ctx, _repo_ctx:
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
