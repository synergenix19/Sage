# D4 Amendment — info_request Turn-Aware Close — 2026-07-07

**Type:** amendment to a governed carve-out (D4 / **LOCK-QDISC-22**, commit `abf1f8a`). **Authority:** clinical ruling (relayed) + product-owner direction, 2026-07-07. **Status:** built on branch `docs/info-request-bridge-v2.1.0-statement`; **merge/deploy HELD.**

## The ruling (both/and, turn-aware)
- **First single-intent info_request in a thread → one open clarifying QUESTION** (Abby-style triage: *"Are you asking about this for yourself, or in general?"*). A triage/routing act, not an over-question; its answer is the signal `intent_route` uses next turn.
- **Consecutive/repeat info_request (same thread) → statement bridge** (Option i retained as the designed fallback — do not re-triage a user in lookup mode every turn).
- **Constraints that travel:** exactly one question, open, purposeful; never a second; never a closed "want to know more?"; never a professional redirect on a purely factual turn; no em dashes. `_limit_to_one_question` enforces the one-question ceiling deterministically.

## What was amended, and why it is safe
`directive_detect.py` no longer sets `directive_posture` for `primary_intent == "info_request"` (the D4 answer-first trigger, added by `abf1f8a`). **Audit 2026-07-07 (both code and Rules Service):** on an info_request turn `directive_posture=True` had **exactly one** effect — `output_gate._strip_trailing_question` — which amputated the intended clarifying question. `composer.py:880` reads the flag only for `general_chat`; **no rule JSON keys on it, no `trigger_type` reads a posture/state field, and it is never passed into any `rules_engine.evaluate()` context.** So removing the info_request trigger is surgical: its only consequence is that the clarifying question survives. Genuine delegation / question-fatigue turns still trigger `directive_posture` and still strip.

## Semantics of "repeat" — stated explicitly (Condition 2)
"Repeat" = **immediately-consecutive** info_request, detected via `prev_primary_intent` (persisted across turns via the LangGraph checkpoint, mirroring `prev_step_id`; absent from `_build_state`, written by `output_gate`). **Any intervening non-info_request turn resets `prev_primary_intent`, restoring the question-close (re-triage after a context switch).** This is a deliberate clinical-semantics choice, not an implementation accident: `info → info` = statement; `info → "for myself" detour → info` = question again. Edge case: a crisis turn bypasses `output_gate`, so it does not update `prev_primary_intent` — negligible (crisis re-routing dominates), noted for completeness.

## Supersedes the pure-statement v2.1.0 (version history honesty)
The earlier **unpromoted** v2.1.0 statement-bridge package (branch `246b88e`) was superseded **pre-promotion** by this both/and ruling. Its statement content is **retained** as the repeat-turn fallback (`L2_info_request_repeat`). Nothing was promoted from it; the pure-statement approach was the right analysis of the wrong question.

## Build mechanics (Condition 4)
- Versions: `info_request` → **v2.1.0** (question-close base); new `L2_info_request_repeat` v1.0.0 (statement variant). Composer selects `repeat` when `prev_primary_intent == "info_request"`.
- Manifest: both classified `engagement_bridge`; `classified_against_version` set to the new versions (#127 guard green).
- Tests: `test_info_request_turn_aware.py` (detector amendment + variant selection + reset) and the retained `test_info_request_bridge_survives_gate.py` (strip-scope pinned question-only, EN + `؟` — the strip still exists for genuinely-directive turns of other intents). Two existing directive tests rewritten to the amendment (rewrite-not-delete). Full suite green on touched surfaces (243 passed), `build_graph()` OK.

## Signer — RESOLVED 2026-07-07
Signer confirmed **verbatim from the primary record**: **Rohan Sarda (clinical lead)** (stated directly by the product owner, not inferred). Templates now stamped `approved_by: "Rohan Sarda (clinical lead)"`. This also confirms the earlier v2.0.0 stamp was *accidentally correct* — right name, but populated by inference at the time (the process error `feedback_primary_record_over_inference` records). The register attribution correction is therefore a **provenance confirmation, not a name change** (see the sign-off register's Corrections appendix).

## Remaining before promotion (per the standing evidence gate)
1. **PromptFoo rubric rewrite** — base cases assert the question-form close; add repeat-variant statement cases.
2. **Full-graph LLM eval** (compose → live generation → output_gate): first-turn one open clarifying question survives the gate (EN + `؟`); repeat-turn statement, zero questions; no em dashes. Attach honestly with the GPT-4o→Falcon transfer caveat.
3. **Behavioral closure** — post-deploy prod smoke transcript (fresh "what is anxiety" = surviving question-close; consecutive = statement fallback).
