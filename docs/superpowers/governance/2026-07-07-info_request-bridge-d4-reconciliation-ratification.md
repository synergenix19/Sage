# info_request Bridge ↔ D4 Reconciliation — Clinical Ratification Request — 2026-07-07

**For:** clinical lead (policy owner of D4). **Type:** ratify an *interpretation*, not merely approve wording.
**Prepared by:** engineering. **Companion:** draft `2026-07-07-info_request-v2.1.0-statement-bridge-draft.json`; guard test `tests/test_info_request_bridge_survives_gate.py` (green); research brief `mental_health_llm_research_report`.

## What happened
`info_request` v2.0.0 (approved 2026-07-07) added a closing "bridge" to keep the conversation going. In prod it never appeared: the bridge is rendered by GPT-4o as a **question**, and the governed **D4 answer-first** policy (`directive_posture` fires on every info_request turn → `output_gate._strip_trailing_question`; commit `abf1f8a`, carve-out ticket **#22 LOCK-QDISC-22**) **strips trailing questions**. So the bridge was generated, then amputated. The isolated prompt-eval could not see this (it never ran `output_gate`); the behavioral smoke test did.

## The proposed reconciliation
Reword the bridge from an *invitation* (question-prone) to a **warm continuation statement** (no `?`). A statement bridge passes through `_strip_trailing_question` untouched, keeps the conversation going ("question or not"), and requires **no gate change and no D4 re-litigation**. Guarded by the test above (statement survives; question stripped; strip scope pinned question-only; EN + Arabic `؟`).

## ⚠️ The decision only you can make — which reading of D4 was signed?
The reconciliation *honors* D4 under one reading and *circumvents* it under another. This is a policy-intent call, not an engineering one:

| Reading | D4's purpose | Mechanism | Verdict on a statement bridge |
|---|---|---|---|
| **A** | "Answer-first: don't meet an info-seeker with more questions." | Stripping questions is the *means*. | **Honors D4** — a statement offer is not a question; the intent is preserved. Approve v2.1.0. |
| **B** | "No engagement hooks after a directive answer at all." | Questions were the *observed vector*; the goal was no continuation hook. | **Circumvents D4** — a statement hook is exactly what D4 meant to prevent. Then v2.0.0's bridge itself was the error, and info_request should end on substance with no bridge. |

**Please ratify A or B.** Under A, v2.1.0 promotes as drafted. Under B, we drop the info_request bridge and record that the v2.0.0 approval was made without visibility of D4.

## Research grounding (supports that continuation ≠ a question)
- The #1 documented user frustration is **genericness / dead-ending**, not missing questions (JMIR 2025: *"so generic I just existed in this space for 5 minutes"*). A statement bridge fixes that.
- MIND-SAFE conversation-style guidance is *"one question at a time, never stack"* and *"open before closed"* — i.e. **do not over-question**; it never mandates ending on a question.
- A statement offer also avoids two other flagged frustrations: **over-affirmation/over-questioning** and **premature redirection to professional help**.
- (Boit & Patil, JMIR Mental Health Nov 2025; Luo et al., Digital Health Jul 2025; APA 2025 — per the attached brief.)

## What your sign-off does
Ratifies reading A or B; on A, sets `approved_by` on v2.1.0 (version bump 2.0.0→2.1.0), which triggers the manifest re-confirm (#127 guard) and the PromptFoo rubric update (invitation → statement/offer form, re-run). Does not touch the D4 carve-out or ticket #22. The separate directive-detect over-fire audit is tracked independently (ticket `2026-07-07-directive-posture-infofire-audit.md`).
