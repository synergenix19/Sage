# Ticket: audit directive_posture firing on all info_request turns

**Opened:** 2026-07-07 · **Priority:** low (does not block the v2.1.0 bridge fix) · **Type:** diagnostic / design audit

## Why this is separate from the bridge fix
The v2.1.0 statement-bridge reword makes the `_strip_trailing_question` amputation **harmless** to info_request — but it does not explain, or address, *why* an advice-discipline posture fires on a pure factual question like "what is anxiety" in the first place. `directive_detect.py:84-85` sets `directive_posture = True` for **every** `info_request` turn (the deliberate "D4 answer-first" trigger, commit `abf1f8a`). The bridge reword sidesteps the one visible consequence; this ticket tracks the rest.

## Scope
1. **Full effect footprint.** Enumerate everything `directive_posture == True` does on an info_request turn beyond `_strip_trailing_question` (composer variant selection — believed general_chat-only at `composer.py:880`; any other node/rule keyed on the flag; audit/telemetry semantics). Confirm none of those effects are unintended on factual turns.
2. **Breadth of the trigger.** Is "**all** info_request → directive_posture" too broad? A pure psychoeducation question ("what is anxiety") is not the advice-delegation / question-fatigue pattern D4 was built for. Assess whether the trigger should be narrowed (e.g. only advice-seeking info_requests) or whether answer-first is genuinely correct for all info_requests.
3. **Naming/telemetry.** `directive_posture_set` + `question_discipline_applied` appearing in the node path of a benign factual turn is confusing to anyone reading prod traces; consider clearer signals.

## Non-goals
- No change to the D4 carve-out or ticket #22 LOCK-QDISC-22 without policy-owner sign-off.
- Blocked-by: nothing. Blocks: nothing (the bridge fix is independent).

## Origin
Surfaced during the info_request v2.0.0 → prod behavioral trace (bridge amputated by output_gate). See `2026-07-07-info_request-bridge-d4-reconciliation-ratification.md` and memory `project_info_request_engagement_gap.md`.
