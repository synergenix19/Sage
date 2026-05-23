from __future__ import annotations
import json
import logging
from typing import Optional

from sage_poc.llm import get_classifier
from sage_poc.resilience import resilient_invoke

_log = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = (
    "You are extracting structured facts from a mental health support conversation "
    "to update a cross-session user profile. Extract only what was explicitly stated. "
    "Return valid JSON with these exact keys:\n"
    "  effective_techniques: list of technique names the user said helped (strings)\n"
    "  ineffective_techniques: list the user said didn't work or resisted\n"
    "  distortion_patterns: cognitive distortion patterns observed (strings)\n"
    "  disclosed_concerns: life areas or concerns the user mentioned\n"
    "  communication_style: one sentence on how this user communicates\n"
    "  cultural_preferences: object with keys religious_framing (bool), "
    "family_context (bool), gender_address (string or null)\n"
    "  mood_score: integer 1-5 (1=very low, 5=good) at session end\n"
    "  skills_completed: integer count of skills fully completed this excerpt\n"
    "Return ONLY the JSON object. No preamble."
)


async def extract_session_profile(
    history: list[dict],
    llm=None,
) -> Optional[dict]:
    """Extract structured profile facts from a conversation excerpt.
    Returns dict on success, None on unparseable output.
    Only explicitly stated facts are extracted.
    """
    if llm is None:
        llm = get_classifier()
    turns = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM},
        {"role": "user", "content": f"Conversation:\n{turns}"},
    ]
    try:
        raw = await resilient_invoke(llm, messages, node="profile_extractor", language="en")
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as exc:
        _log.warning("[profile_extractor] parse failed: %s", exc)
        return None
