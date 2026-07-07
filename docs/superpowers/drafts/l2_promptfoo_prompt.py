"""PromptFoo prompt provider — composes the DRAFT L2 templates into a prompt.

The engagement drafts live in docs/ and are NOT loaded in prod. This shim makes
the composer use the DRAFT content for the eval, then returns the composed
system+user messages, so the PromptFoo cases exercise the PROPOSED wording, not
the live v1.0.0.

PromptFoo calls `compose(context)` with context['vars']['state'] (the scenario's
partial SageState); we merge it over defaults, patch get_intent_template to
return the draft, and compose.

RUN (requires OPENROUTER_API_KEY from `railway variables -s sage-api -e production`):
  PYTHONPATH=<repo>/src OPENROUTER_API_KEY=... \
    npx promptfoo@latest eval -c docs/superpowers/drafts/2026-07-07-l2-engagement-promptfoo.yaml
"""
import copy
import json
from pathlib import Path

_DRAFTS = Path(__file__).resolve().parent
_DRAFT_BY_INTENT = {
    "info_request": "2026-07-07-info_request-v2.0.0-draft.json",
    "new_skill": "2026-07-07-new_skill-v1.1.0-draft.json",
    "exit_skill": "2026-07-07-exit_skill-v1.1.0-draft.json",
    "low_confidence": "2026-07-07-low_confidence-v1.1.0-draft.json",
}

_STATE_DEFAULTS = {
    "raw_message": "", "message_en": "", "detected_language": "en",
    "primary_intent": "info_request", "secondary_intent": None,
    "intent_confidence": 1.0, "emotional_intensity": 3, "engagement": 5,
    "clinical_flags": [], "crisis_state": "none", "conversation_history": [],
    "knowledge_passages": [], "knowledge_abstain": False, "path": [],
}


def _draft_template(intent):
    from sage_poc.prompts.loader import get_intent_template
    real = get_intent_template(intent)
    fname = _DRAFT_BY_INTENT.get(intent)
    if not fname or real is None:
        return real
    fake = copy.copy(real)
    fake.content = json.loads((_DRAFTS / fname).read_text())["content"]
    return fake


def compose_messages(state_in: dict) -> list:
    """Deterministic core: return [system, user] messages for a scenario state.
    Importable directly so the wiring can be verified without an LLM call."""
    from sage_poc.prompts import composer
    state = {**_STATE_DEFAULTS, **(state_in or {})}
    orig = composer.get_intent_template
    composer.get_intent_template = lambda intent, variant=None: (
        _draft_template(intent) if intent in _DRAFT_BY_INTENT else orig(intent, variant=variant)
    )
    try:
        system, user, _ = composer.compose_prompt(state)
    finally:
        composer.get_intent_template = orig
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def compose(context):
    """PromptFoo entry point."""
    return compose_messages(context.get("vars", {}).get("state"))
