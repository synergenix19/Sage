# Governance: Engagement Advice Posture, Question Discipline & Anti-Generic

**Date:** 2026-06-14
**Plan:** docs/superpowers/plans/2026-06-14-engagement-advice-posture.md
**Branch:** feat/engagement-advice-posture
**Supersedes posture stopgap:** Option A (general_chat exception clause — absorbed into base posture v1.4.0)
**Control-layer change?** NO. No new intent, no routing change → no Rule-1 review on routing.
**Evidence:** Production replay 2026-06-14 (chat.biosight.ai); People/Pain/LLMs brief (MIND-SAFE,
JMIR 2025 genericness #1 frustration, Reddit over-affirmation ~60 comments).

## Provenance note
The approvals below were obtained by the product owner and relayed in-session on 2026-06-14
authorizing activation + deploy. "clinical_lead" is the role-level approver per the existing
template-metadata convention (approved_by field). Replace with individual approver names if the
audit trail requires per-person attribution.

## Sign-offs
- [x] Clinical: L2 general_chat base posture rewrite v1.4.0 (Task 6) — clinical_lead, 2026-06-14
- [x] Clinical: L0 persona v2.1.0 additive (Task 7) — clinical_lead, 2026-06-14
- [x] Clinical: general_chat_directive variant content (Task 5) — clinical_lead, 2026-06-14
- [x] Clinical: delegation phrase list precision (Task 2, D2) — clinical_lead, 2026-06-14

## Decisions (see plan §Decision Points)
- D1 question-discipline scope: FREEFLOW-ONLY (skip skill-execution turns). Approved 2026-06-14.
- D3 over-affirmation challenge: gentle, non-acute only. Approved 2026-06-14.

## Absolute Rule 1 — L0/L2 word-budget deviation
- L2 general_chat: 50 → 100 (v1.4.0, ~95w). L2 general_chat_directive: 100 (~95w, replaces base).
- L0 persona: 550 → 590 (v2.1.0, ~585w).
- Total-ceiling: L3/L4 do not fire on general_chat freeflow turns (composer.py:216/780); net new
  always-on ≈ +90w. Accepted for POC.
- [x] **Product-owner Rule-1 approval (budget deviation, compress option):** product owner, 2026-06-14

## Absolute Rule 1 — question-discipline as clinical policy in engineer code (DEVIATION)
Question-discipline (one-question threshold + crisis/monitoring/skill-step carve-outs) is hardcoded in
output_gate.py instead of the CMS Rules Service, because the cultural_output schema is
blocklist/allowlist substring→substitute only and cannot count/trim. Flagged + approved per Rule 1.
- [x] **Clinical awareness on the threshold itself** (one-question rule + crisis/monitoring +
  skill-step carve-out) — clinical_lead, 2026-06-14
- [x] **Product-owner Rule-1 approval (hardcode-for-POC)** — product owner, 2026-06-14
- **Follow-up (HARD CONDITION, not optional):** `LOCK-QDISC-22` (session task #22) — extend the Rules
  Service schema with a `structural_output` rule type so question-discipline migrates back to
  CMS-authored, clinician-tunable JSON. Named owner: ____________ (assign before closing the work).

## Deterministic (no sign-off, recorded for awareness)
- directive_posture detector (directive_detect.py): keyword + repair signal, not the classifier.
- Crisis safety: question-discipline gated on crisis_state in (None,"none") so monitoring/crisis/
  resolved turns are never question-stripped; crisis_response bypasses output_gate (graph.py:272).
  Skill-execution turns (step_instruction set) also skipped (D1 freeflow-only).
- INTENT_SYSTEM untouched (bare_emotional_words crisis-routing guard unaffected).

## Anti-generic = eval, NOT a gate
register≥4.0 + specificity_tailoring rubric dims + directive scenarios (tests/experiment_4_4),
clinician-scored. Judge-LLM, if later used to automate, must be calibrated vs human raters before
gating (see test-content-guardrails).

## Activation + deploy (Task 10)
- general_chat.json v1.4.0, L0_persona.json v2.1.0: were already approved, content updated + kept approved.
- general_chat_directive.json: flipped draft-pending-review → approved (approved_by clinical_lead,
  effective_date 2026-06-14); removed from test_clinical_governance KNOWN_LIVE_TEMPLATES (discharged).
- Deployed to Railway sage-api/production 2026-06-14 (see session record).
