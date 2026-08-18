"""
Cultural overrides condensation smoke test.

PURPOSE
-------
Verify that condensed cultural_overrides transmit their guidance to the model.
Runs each scenario twice: once WITH the condensed override (worktree JSON files),
once WITHOUT any override (simulating current main-branch behaviour, where
over-budget blocks are silently dropped after the Task 0 cap reduction).

FRAMING CAUTION — READ BEFORE INTERPRETING RESULTS
----------------------------------------------------
Scores measure "did the cultural guidance transmit to the model response."
They do NOT measure "is the cultural guidance correct."
A response can score 5/5 — clearly in-frame, culturally calibrated-looking —
and still contain phrasing an Emirati speaker would flag as subtly off.
This output is evidence FOR the clinical reviewer, not a substitute for any
part of their judgment. Emirati-speaker review and dual-clinician approval
(§9.4–9.5) remain the gate. Label your findings accordingly.

SYNTHETIC DATA ONLY
--------------------
The --call-llm path sends prompts to OpenRouter (outside UAE).
This script MUST only be run with the synthetic scenarios defined below.
Never pass real session transcripts or user data through this script.
Doing so would violate PDPL data residency requirements.
The scenarios in SCENARIOS are the only permitted input when --call-llm is used.

LOCKSTEP RULE
-------------
If you edit cultural_overrides in the worktree JSON files during Phase 4
iteration, update docs/cms-drafts/2026-05-30-cultural-overrides-condensation-drafts.md
with the SAME text before generating the final report. The thing reviewed and
the thing tested must be identical. Divergence means the clinician blesses one
version while the smoke test exercised another.

Usage:
    # Structural only (fast, no API call)
    python scripts/smoke_cultural_overrides.py --skill assertive_communication

    # Both structural and LLM response
    python scripts/smoke_cultural_overrides.py --skill assertive_communication --call-llm

    # All skills
    python scripts/smoke_cultural_overrides.py --all

    # All skills with LLM, generate markdown report
    python scripts/smoke_cultural_overrides.py --all --call-llm --report
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sage_poc.prompts.composer import compose_prompt
from sage_poc.prompts.tokens import count_words
from sage_poc.skills.schema import Skill, load_skill

# ---------------------------------------------------------------------------
# SYNTHETIC TEST SCENARIOS ONLY — see module docstring
# Each scenario: (label, user_message, step_instruction, primary_intent)
# step_instruction=None → freeflow (L1_base=600); set → skill turn (L1_base=450)
# ---------------------------------------------------------------------------
SCENARIOS: dict[str, list[tuple[str, str, str | None, str]]] = {
    "assertive_communication": [
        (
            "A — indirect refusal / family obligation",
            "My mother keeps asking me to take on responsibilities I do not have capacity for "
            "and I do not know how to tell her without hurting her or seeming disrespectful.",
            "Help the user identify one situation where they want to set a limit and explore "
            "how to express it in a way that feels right to them.",
            "skill_continuation",
        ),
        (
            "B — workplace disagreement / Islamic frame",
            "I want to tell my manager that I think his decision is wrong but in our culture "
            "you don't challenge people above you. Is being assertive even allowed in Islam?",
            "Help the user understand that expressing a view respectfully is different from "
            "disrespecting authority, and explore what an honest, face-saving response might look like.",
            "skill_continuation",
        ),
    ],
    "mindfulness_body_scan": [
        (
            "A — Islamic compatibility question",
            "Is this meditation? I'm worried it might conflict with my prayers or be haram.",
            "Clarify what the body scan is and guide the user to try a short version.",
            "skill_continuation",
        ),
        (
            "B — privacy / shared space",
            "I live with my whole family and I don't have a private room. "
            "Can I do this practice without anyone noticing?",
            "Reassure the user and guide them through a seated, eyes-open version.",
            "skill_continuation",
        ),
    ],
    "psychoed_anxiety": [
        (
            "A — somatic presentation",
            "My chest feels tight all the time and my heart races. "
            "I went to the doctor and they said nothing is physically wrong. "
            "I don't know what is happening to me.",
            "Validate the user's physical experience and gently introduce the idea "
            "that the body and nervous system are connected to emotional states.",
            "skill_continuation",
        ),
        (
            "B — tawakkul framing",
            "I keep feeling anxious even though I pray and try to trust in God. "
            "I feel like my anxiety means my iman is weak.",
            "Help the user understand that anxiety is a physiological response, "
            "not a sign of spiritual weakness, and that both can coexist.",
            "skill_continuation",
        ),
    ],
    "psychoed_depression": [
        (
            "A — somatic / no emotional vocabulary",
            "I'm always tired. My body aches everywhere. I have no energy to do anything. "
            "I don't even know why I am like this.",
            "Validate the physical experience and introduce the biological framing of depression.",
            "skill_continuation",
        ),
        (
            "B — stigma / faith framing",
            "I think I might be depressed but I feel ashamed to say it. "
            "Doesn't depression mean you have weak faith?",
            "Normalise depression as a medical condition and gently address the faith framing.",
            "skill_continuation",
        ),
    ],
    "psychoed_stress": [
        (
            "A — relational stressors",
            "I feel overwhelmed. My family has so many expectations — my parents, "
            "my wife, my children, my work. Everyone needs something from me and "
            "I feel like I am drowning.",
            "Validate the relational load before introducing any coping framework.",
            "skill_continuation",
        ),
        (
            "B — tawakkul / stress shame",
            "I know I should trust in God more. I feel like if my tawakkul was stronger "
            "I wouldn't feel this stressed. But I can't stop worrying.",
            "Validate that stress is biological, not a spiritual failing, "
            "and that both registers can coexist.",
            "skill_continuation",
        ),
    ],
    "self_compassion_break": [
        (
            "A — selfishness objection",
            "I feel so weak for struggling like this. I just need to be stronger. "
            "Being kind to myself feels selfish when others have real problems.",
            "Gently challenge the selfishness frame and introduce self-compassion "
            "as a tool, not indulgence.",
            "skill_continuation",
        ),
        (
            "B — Islamic anchor opportunity",
            "I have been very harsh with myself. I pray and I ask for God's mercy "
            "but I don't give any mercy to myself.",
            "Use the rahma anchor if it fits naturally; guide the user through "
            "the compassion break.",
            "skill_continuation",
        ),
    ],
    "values_clarification": [
        (
            "A — collective values / no individual frame",
            "I don't know what I want anymore. Everything I do is for my family. "
            "When people ask me what my values are I don't even know what that means for me.",
            "Help the user explore values through a collective rather than individual lens.",
            "skill_continuation",
        ),
        (
            "B — faith as foundation",
            "My most important value is my faith, my relationship with God. "
            "But I feel like I am failing at it. Is that a value I can work with?",
            "Affirm faith as a valid ACT value and explore what committed action "
            "toward it looks like in the user's life.",
            "skill_continuation",
        ),
    ],
}

# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------

def _make_state(
    skill_id: str,
    user_message: str,
    step_instruction: str | None,
    primary_intent: str,
    history: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "raw_message": user_message,
        "detected_language": "en",
        "message_en": user_message,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "code_switching": False,
        "primary_intent": primary_intent,
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 6,
        "active_skill_id": skill_id if step_instruction else None,
        "active_step_id": "s1" if step_instruction else None,
        "executed_step_id": None,
        "step_instruction": step_instruction,
        "skill_match_method": "semantic",
        "semantic_score": 0.85,
        "escalation_triggered": None,
        "gate_path": None,
        "rule_fired": None,
        "stale_skill_id": None,
        "re_escalation_within_monitoring": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 1,
        "conversation_history": history or [],
        "prompt_layers": [],
        "token_usage": {},
        "knowledge_passages": None,
        "knowledge_abstain": False,
        "knowledge_source": None,
        "therapeutic_profile": None,
    }


def _no_rules_mock() -> MagicMock:
    m = MagicMock()
    m.actions = []
    return m


# ---------------------------------------------------------------------------
# Core runner — two arms per scenario
# ---------------------------------------------------------------------------

def run_scenario(
    skill_id: str,
    label: str,
    user_message: str,
    step_instruction: str | None,
    primary_intent: str,
    call_llm: bool,
) -> dict[str, Any]:
    """Run one scenario through compose_prompt for both arms and return results."""
    state = _make_state(skill_id, user_message, step_instruction, primary_intent)

    results: dict[str, Any] = {
        "skill_id": skill_id,
        "label": label,
        "user_message": user_message,
        "arms": {},
    }

    for arm_name, use_override in [("with_override", True), ("no_override", False)]:
        # Load the real skill from JSON (worktree files when use_override=True,
        # or strip cultural_overrides to simulate main-branch dropped behaviour).
        real_skill = load_skill(skill_id)
        if not use_override:
            # Simulate main-branch: override silently dropped (over 200w cap on master)
            real_skill = real_skill.model_copy(update={"cultural_overrides": None})

        with (
            patch(
                "sage_poc.prompts.composer.rules_engine.evaluate",
                return_value=_no_rules_mock(),
            ),
            patch("sage_poc.prompts.composer.load_skill", return_value=real_skill),
        ):
            system_str, user_str, layers = compose_prompt(state)

        has_skill = bool(step_instruction)
        has_knowledge = primary_intent == "info_request"
        l1_base = 450 if (has_skill or has_knowledge) else 600
        l1_base_label = "450 (skill/knowledge turn)" if l1_base == 450 else "600 (freeflow turn)"

        override_injected = "cultural_skill_overrides" in layers
        override_block = ""
        if override_injected and real_skill.cultural_overrides:
            lines = "\n".join(
                f"  - {v}" for v in real_skill.cultural_overrides.values()
            )
            override_block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{lines}"
        override_words = count_words(override_block) if override_injected else 0

        system_words = count_words(system_str)
        user_words = count_words(user_str)
        total_words = system_words + user_words

        arm: dict[str, Any] = {
            "override_injected": override_injected,
            "override_words": override_words,
            "override_block": override_block,
            "l1_base_label": l1_base_label,
            "layers": layers,
            "system_words": system_words,
            "user_words": user_words,
            "total_words": total_words,
            "system_str": system_str,
            "user_str": user_str,
            "llm_response": None,
            "score": None,
            "score_notes": None,
        }

        if call_llm and override_injected:
            # SYNTHETIC SCENARIOS ONLY — never call with real session data.
            # Sends to OpenRouter (outside UAE). See module docstring.
            arm["llm_response"] = _call_llm(system_str, user_str)
        elif call_llm and not override_injected:
            # No override injected: still call LLM to show the baseline response.
            arm["llm_response"] = _call_llm(system_str, user_str)

        results["arms"][arm_name] = arm

    return results


def _call_llm(system_str: str, user_str: str) -> str:
    """Call the responder LLM via OpenRouter. Synthetic scenarios only."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from sage_poc.llm import get_responder

    llm = get_responder()
    messages = [
        SystemMessage(content=system_str),
        HumanMessage(content=user_str),
    ]
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as exc:
        return f"[LLM call failed: {exc}]"


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

SEP = "─" * 70


def _arm_summary(arm_name: str, arm: dict) -> str:
    tag = "WITH override" if arm_name == "with_override" else "NO override (main baseline)"
    injected = "YES" if arm["override_injected"] else "NO (silently dropped)"
    lines = [
        f"  Arm: {tag}",
        f"  Override injected: {injected}",
    ]
    if arm["override_injected"]:
        lines.append(f"  Override word count: {arm['override_words']}w")
    lines += [
        f"  L1 base: {arm['l1_base_label']}",
        f"  Layers: {arm['layers']}",
        f"  System: {arm['system_words']}w  User: {arm['user_words']}w  Total: {arm['total_words']}w",
    ]
    if arm["override_injected"] and arm["override_block"]:
        lines.append("\n  Override block injected into system prompt:")
        for line in arm["override_block"].splitlines():
            lines.append(f"    {line}")
    return "\n".join(lines)


def print_result(result: dict, verbose_prompt: bool = False) -> None:
    skill = result["skill_id"]
    label = result["label"]
    print(f"\n{SEP}")
    print(f"  {skill} / Scenario {label}")
    print(f"  User: \"{result['user_message'][:80]}{'...' if len(result['user_message'])>80 else ''}\"")
    print(SEP)

    for arm_name in ("with_override", "no_override"):
        arm = result["arms"][arm_name]
        print(_arm_summary(arm_name, arm))
        if arm["llm_response"]:
            print(f"\n  LLM response ({arm_name}):")
            wrapped = textwrap.fill(arm["llm_response"], width=66, initial_indent="    ", subsequent_indent="    ")
            print(wrapped)
        print()

    if verbose_prompt:
        print("  Full system prompt (with_override arm):")
        print(textwrap.indent(result["arms"]["with_override"]["system_str"], "    "))


def _sanity_gate(result: dict) -> bool:
    """Print the three sanity checks for the first LLM call and ask for confirmation.

    Returns True if the user confirms all three hold and we should proceed to --all.
    """
    with_arm = result["arms"]["with_override"]
    if not with_arm["llm_response"]:
        return True

    print(f"\n{'═' * 70}")
    print("  SANITY GATE — confirm before proceeding to --all")
    print(f"{'═' * 70}")

    print("\n  [1] Language / register: does the response come back in the right")
    print("      language and register for the scenario? (Not flat MSA or English")
    print("      when a Khaleeji-framed prompt was sent. If wrong: model issue,")
    print("      note it before it colours 14 scores.)")
    print(f"\n  Response (with_override arm):")
    print(textwrap.fill(
        with_arm["llm_response"], width=66, initial_indent="    ", subsequent_indent="    "
    ))
    lang_ok = input("\n  Language/register acceptable? (y/n): ").strip().lower() == "y"

    print("\n  [2] Override in prompt: the block below is what the model received.")
    print("      Confirm it matches the condensed override text for this skill.")
    if with_arm["override_block"]:
        print()
        for line in with_arm["override_block"].splitlines():
            print(f"    {line}")
    inject_ok = input("\n  Override block present and correct? (y/n): ").strip().lower() == "y"

    print("\n  [3] Synthetic data: confirm the user message above is the synthetic")
    print("      scenario from SCENARIOS — no real session data present.")
    data_ok = input("  Synthetic scenario only? (y/n): ").strip().lower() == "y"

    all_ok = lang_ok and inject_ok and data_ok
    if all_ok:
        print("\n  ✓ All three checks pass. Safe to proceed to --all.")
    else:
        failed = [
            label for ok, label in [
                (lang_ok, "language/register"),
                (inject_ok, "override injection"),
                (data_ok, "synthetic data"),
            ] if not ok
        ]
        print(f"\n  ✗ Gate failed on: {', '.join(failed)}. Investigate before --all.")
    print(f"{'═' * 70}\n")
    return all_ok


def prompt_scores_blind(result: dict) -> None:
    """Present both arm responses in shuffled order; score before reveal.

    Scoring is against the ORIGINAL clinical intent, not the condensed bullet.
    Scores of 4-5 require a named specific: what in the response reflects
    what the full original override was protecting?
    """
    with_arm = result["arms"]["with_override"]
    no_arm = result["arms"]["no_override"]
    if not with_arm["llm_response"] or not no_arm["llm_response"]:
        return

    arms = [("with_override", with_arm), ("no_override", no_arm)]
    random.shuffle(arms)
    letters = ["A", "B"]

    print(f"\n  {'─' * 66}")
    print(f"  BLIND SCORING — {result['skill_id']} / {result['label']}")
    print(f"  {'─' * 66}")
    print("  Score: did the ORIGINAL clinical intent transmit? (1=not at all, 5=yes)")
    print("  Bar is original intent, not condensed wording. 'Parrots the bullet'")
    print("  ≠ functional. 'Does what the full override would have produced' = yes.")
    print("  NOTE: 5/5 means guidance transmitted. NOT a cultural correctness claim.")
    print("  Scores 4-5: you must name the specific thing. If you can't, it's not a 5.")

    scored: dict[str, tuple[int | None, str]] = {}

    for idx, (arm_name, arm) in enumerate(arms):
        letter = letters[idx]
        print(f"\n  Response {letter}:")
        print(textwrap.fill(
            arm["llm_response"], width=66, initial_indent="    ", subsequent_indent="    "
        ))
        raw = input(f"\n  Score for Response {letter} (1-5, Enter to skip): ").strip()
        score = int(raw) if raw.isdigit() and 1 <= int(raw) <= 5 else None

        note = ""
        if score and score >= 4:
            print(f"  Score {score}/5 — name the specific thing in Response {letter} that")
            print("  reflects the ORIGINAL clinical intent (required for 4+):")
            note = input("  → ").strip()
            if not note:
                print("  (No specific named — consider whether this is truly a 4+.)")
        else:
            note = input(f"  Notes for Response {letter} (optional): ").strip()

        scored[arm_name] = (score, note)

    print("\n  [Reveal]")
    for idx, (arm_name, _) in enumerate(arms):
        letter = letters[idx]
        tag = "WITH condensed override" if arm_name == "with_override" else "NO override (main baseline)"
        print(f"  Response {letter} was: {tag}")

    for arm_name, (score, note) in scored.items():
        result["arms"][arm_name]["score"] = score
        result["arms"][arm_name]["score_notes"] = note


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(all_results: list[dict], output_path: Path) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Cultural Overrides Condensation — Smoke Test Results",
        "",
        f"> Generated: {ts}",
        ">",
        "> **What this report is:** Evidence that condensed cultural overrides transmit their guidance",
        "> to the model. Each scenario ran twice: WITH the condensed override injected (worktree),",
        "> and WITHOUT any override (simulating current main-branch behaviour, where over-budget",
        "> blocks are silently dropped after the Task 0 cap reduction).",
        ">",
        "> **What this report is NOT:** Cultural validation. A score of 5 means the guidance",
        "> landed in the response — it does not mean the guidance is culturally correct or",
        "> clinically appropriate. Emirati-speaker review and dual-clinician approval (§9.4–9.5)",
        "> remain the gate. This report is evidence FOR those reviewers, not a substitute.",
        ">",
        "> **LOCKSTEP:** The condensed overrides tested here must be identical to the text in",
        "> `docs/cms-drafts/2026-05-30-cultural-overrides-condensation-drafts.md`.",
        "> If Phase 4 iteration produced wording changes, that document must be updated before",
        "> this report is sent for clinical review.",
        ">",
        "> **Synthetic scenarios only.** The --call-llm path sends to OpenRouter (outside UAE).",
        "> This report must never include real session transcripts or user data.",
        "",
        "---",
        "",
    ]

    for result in all_results:
        skill = result["skill_id"]
        label = result["label"]
        user_msg = result["user_message"]
        lines += [
            f"## `{skill}` — Scenario {label}",
            "",
            f"**User message:** {user_msg}",
            "",
        ]

        for arm_name in ("with_override", "no_override"):
            arm = result["arms"][arm_name]
            tag = "WITH condensed override" if arm_name == "with_override" else "NO override (main baseline)"
            injected = "YES" if arm["override_injected"] else "NO"
            score_str = str(arm.get("score")) if arm.get("score") else "—"
            notes_str = arm.get("score_notes") or ""

            lines += [
                f"### {tag}",
                "",
                f"- Override injected: **{injected}**  ({arm['override_words']}w)" if arm["override_injected"] else f"- Override injected: **{injected}**",
                f"- L1 base: {arm['l1_base_label']}",
                f"- Total prompt: {arm['total_words']}w (system {arm['system_words']}w + user {arm['user_words']}w)",
                f"- Layers: `{arm['layers']}`",
                f"- Transmission score: **{score_str}/5**" + (f" — {notes_str}" if notes_str else ""),
                "",
            ]

            if arm["override_injected"] and arm["override_block"]:
                lines += [
                    "**Override block tested (what the model saw):**",
                    "```",
                    arm["override_block"],
                    "```",
                    "",
                ]

            if arm["llm_response"]:
                lines += [
                    "**Model response:**",
                    "",
                    arm["llm_response"],
                    "",
                ]

        lines += ["---", ""]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Cultural overrides condensation smoke test.")
    parser.add_argument("--skill", choices=list(SCENARIOS.keys()), help="Run one skill only.")
    parser.add_argument("--all", action="store_true", help="Run all skills.")
    parser.add_argument("--call-llm", action="store_true", dest="call_llm",
                        help="Call the LLM via OpenRouter. SYNTHETIC SCENARIOS ONLY — see module docstring.")
    parser.add_argument("--report", action="store_true",
                        help="Write a markdown report after running.")
    parser.add_argument("--verbose-prompt", action="store_true", dest="verbose_prompt",
                        help="Print the full assembled system prompt for each scenario.")
    parser.add_argument("--no-score", action="store_true", dest="no_score",
                        help="Skip interactive scoring (useful for unattended runs).")
    args = parser.parse_args()

    if not args.skill and not args.all:
        parser.print_help()
        sys.exit(1)

    # OpenRouter key check
    if args.call_llm:
        from sage_poc.config import OPENROUTER_API_KEY
        if not OPENROUTER_API_KEY:
            print("WARNING: OPENROUTER_API_KEY not set. Skipping LLM arm.")
            args.call_llm = False
        else:
            print("NOTE: --call-llm active. Prompts will be sent to OpenRouter (outside UAE).")
            print("      SYNTHETIC SCENARIOS ONLY — do not repurpose this script with real data.\n")

    skills_to_run = list(SCENARIOS.keys()) if args.all else [args.skill]
    all_results: list[dict] = []
    sanity_done = False  # gate fires once on the first LLM scenario

    for skill_id in skills_to_run:
        for label, user_message, step_instruction, primary_intent in SCENARIOS[skill_id]:
            print(f"\nRunning: {skill_id} / Scenario {label}")
            result = run_scenario(
                skill_id, label, user_message, step_instruction, primary_intent, args.call_llm
            )
            print_result(result, verbose_prompt=args.verbose_prompt)

            if args.call_llm and not args.no_score:
                # First LLM result: hard sanity gate before scoring or proceeding.
                if not sanity_done:
                    gate_passed = _sanity_gate(result)
                    sanity_done = True
                    if not gate_passed:
                        print("Stopping. Fix the gate failure before running --all.")
                        all_results.append(result)
                        if args.report:
                            report_path = ROOT / "docs" / "cms-drafts" / "2026-05-30-condensation-smoke-test-results.md"
                            generate_report(all_results, report_path)
                        return

                # Blind scoring: shuffle arms, score before reveal.
                prompt_scores_blind(result)

            all_results.append(result)

    if args.report:
        report_path = ROOT / "docs" / "cms-drafts" / "2026-05-30-condensation-smoke-test-results.md"
        generate_report(all_results, report_path)


if __name__ == "__main__":
    main()
