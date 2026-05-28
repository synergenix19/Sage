"""LLM-based completion criteria evaluator for structured skills.

Mirrors the resistance-scoring pattern in skill_executor.py:
called by skill_executor_node for the 4 target skills only, after
evaluate_step_policy() returns _criteria_blocked=True.
Falls back to word-count heuristic on any failure so users are never
permanently stalled by a failing LLM call.
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


async def evaluate_completion_criteria(message_en: str, criterion: str) -> bool:
    """Return True if the user's message satisfies the step completion criterion.

    Uses the classifier LLM when criterion is non-empty. Falls back to
    word-count heuristic (> 1 word) on LLM failure to avoid stalling users.
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
        _log.warning(
            "[criteria_eval] LLM evaluation failed (%s); falling back to word-count heuristic",
            exc,
        )
        return len(message_en.split()) > 1
