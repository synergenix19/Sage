"""Full-graph eval for the turn-aware info_request close (D4 amendment).

Runs the ACTUAL seam the standing gate requires: compose_prompt (branch v2.1.0
templates) -> live generation (prod responder) -> the REAL output_gate
question-discipline helpers (_limit_to_one_question, _strip_trailing_question,
_strip_output_format). This is deliberately NOT a PromptFoo LLM-only eval, because
that class cannot see output_gate — the exact blindness that let the v2.0.0 bridge
be amputated in prod while an isolated eval scored 4/5.

Assertions (the rewritten rubrics, Gap 2, applied to the POST-GATE text):
  - FIRST info_request  -> exactly one question, and it SURVIVES the gate (Abby triage)
  - REPEAT info_request -> zero questions, statement close (survives trivially)
  - no em/en dashes on either
Run: railway run -- PYTHONPATH=<branch>/src <venv>/python <this>
"""
import asyncio, sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])  # for the compose shim, if reused
from sage_poc.prompts import composer
from sage_poc.llm import get_responder
from sage_poc.nodes.output_gate import (
    _limit_to_one_question, _strip_trailing_question, _strip_output_format,
)
from sage_poc.resilience import resilient_invoke

_KP = [{"text": "Anxiety is the body's response to perceived threat; it becomes a concern when persistent and interfering.", "citation": "kb"}]
_DEFAULTS = dict(
    detected_language="en", primary_intent="info_request", secondary_intent=None,
    intent_confidence=1.0, emotional_intensity=3, engagement=5, clinical_flags=[],
    crisis_state="none", conversation_history=[], active_skill_id=None,
    step_instruction=None, knowledge_passages=_KP, path=[],
    directive_posture=False,  # D4 amendment: never set on info_request now
)

SCENARIOS = [
    ("first_turn", dict(message_en="what is anxiety", prev_primary_intent=None)),
    ("first_after_detour", dict(message_en="what is anxiety", prev_primary_intent="general_chat")),
    ("repeat_lookup", dict(message_en="what are the symptoms of anxiety", prev_primary_intent="info_request")),
]


async def _run_one(msg_state):
    state = {**_DEFAULTS, **msg_state}
    system, user, _ = composer.compose_prompt(state)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    raw = await resilient_invoke(get_responder(), messages, node="eval", language="en", fallback_llm=None)
    # real output_gate question-discipline (directive_posture False -> no trailing strip)
    gated = _limit_to_one_question(raw or "")
    if state["directive_posture"]:
        gated = _strip_trailing_question(gated)
    gated = _strip_output_format(gated)
    return gated


def _q(t):
    return t.count("?") + t.count("؟")


async def main():
    print("=== info_request turn-aware full-graph eval (compose -> generate -> output_gate) ===")
    passed = 0
    for name, st in SCENARIOS:
        out = await _run_one(st)
        is_repeat = st.get("prev_primary_intent") == "info_request"
        nq = _q(out)
        dash = ("—" in out) or ("–" in out)
        last = out.strip().splitlines()[-1] if out.strip() else ""
        if is_repeat:
            ok = (nq == 0) and (not dash)
            expect = "REPEAT -> 0 questions (statement), no dash"
        else:
            ok = (nq == 1) and last.rstrip().endswith(("?", "؟")) and (not dash)
            expect = "FIRST -> exactly 1 question that SURVIVES the gate, no dash"
        passed += ok
        print(f"\n[{'PASS' if ok else 'FAIL'}] {name}  ({expect})")
        print(f"   post-gate questions={nq} em_dash={dash}")
        print(f"   last line: {last[:140]}")
    print(f"\n=== {passed}/{len(SCENARIOS)} passed ===")


asyncio.run(main())
