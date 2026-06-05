"""LLM-based completion criteria evaluator for structured skills.

Mirrors the resistance-scoring pattern in skill_executor.py:
called by skill_executor_node for target skills only, after
evaluate_step_policy() returns _criteria_blocked=True.
For ordinary steps: falls back to word-count heuristic on LLM failure.
For entry_screen steps: fails closed (returns False, holds the skill) — "graceful
degradation" is the wrong instinct on a safety gate; degrade to held, not advanced.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).parent.parent
    / "rules" / "data" / "criteria_eval" / "completion_criteria_prompt.json"
)


async def _call_llm(prompt: str) -> str:
    """Call the classifier LLM and return the raw text response."""
    from sage_poc.llm import get_classifier
    from sage_poc.resilience import resilient_invoke
    llm = get_classifier()
    return await resilient_invoke(
        llm,
        [{"role": "user", "content": prompt}],
        node="criteria_eval",
    )


async def evaluate_completion_criteria(
    message_en: str,
    criterion: str,
    fail_closed: bool = False,
) -> bool:
    """Return True if the user's message satisfies the step completion criterion.

    Uses the classifier LLM when criterion is non-empty.
    On LLM failure: if fail_closed is True (entry_screen steps), returns False so the
    skill holds rather than advancing — an LLM error must not open a safety gate. If
    fail_closed is False, falls back to word-count heuristic to avoid stalling users on
    non-critical steps.
    Always returns True for empty message_en (calling node skips this check).
    """
    if not message_en.strip():
        return True
    if not criterion.strip():
        return len(message_en.split()) > 1

    try:
        template = json.loads(_PROMPT_PATH.read_text(encoding="utf-8"))
        prompt = (
            template["prompt"]
            .replace("{message_en}", message_en)
            .replace("{criterion}", criterion)
        )
        raw = await _call_llm(prompt)
        return raw.startswith("yes")
    except Exception as exc:
        if fail_closed:
            _log.error(
                "[criteria_eval] LLM evaluation failed on entry_screen (%s); holding skill (fail-closed)",
                exc,
            )
            return False
        _log.warning(
            "[criteria_eval] LLM evaluation failed (%s); falling back to word-count heuristic",
            exc,
        )
        return len(message_en.split()) > 1
