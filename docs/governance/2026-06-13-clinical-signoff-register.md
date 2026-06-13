# Clinical Sign-off Register — 2026-06-13

**Recorded by:** Engineering, operationalizing the clinical lead's approval relayed by the product owner on 2026-06-13.
**Signer of record:** `clinical_lead` (role). If the audit trail needs a named individual, substitute the name; this register and the per-artifact `approved_by` fields record the role + date.
**Scope:** the clinical decisions and draft artifacts from the PR #4 engagement effort and its safety siblings. Each was reviewed against the recorded reasoning (not a bare diff) — references below.

## What "the clinician approved" cleared, and what it did NOT

Clinician sign-off clears the **clinical** gate. It is **separate** from the **two-rater scoring** measurement gate, which is **NOT complete** (clinician sign-off only, confirmed 2026-06-13). Therefore:
- **PR #4 (engagement) is NOT merge-ready** — it still gates on the two-rater scoring (the EN offer-turn second-rater evidence + the Khaleeji calibration/scoring). See `docs/work-orders/human-scoring-protocol.md`.
- **Arabic exposure stays gated** behind S2-2 + the Khaleeji scoring + the blurb work order, per `docs/governance/2026-06-13-pilot-scope-decision.md` (English-only first exposure).
- **PR #6 and PR #8 (pre-existing safety fixes) are clinically + Rule-1 cleared** and CI-green on the unit-gate — merge-ready (the merge itself is the product owner's to trigger).

## Artifacts signed (per-artifact `approved_by` set to `clinical_lead`, status `draft-pending-review` → `approved`)

On PR #4 branch (commit `e9079ca`):
- `prompts/templates/L2_intents/skill_offer.json` — offer-turn template wording (non-coercion framing).
- `prompts/templates/L2_intents/general_chat.json` v1.3.0 — engage-then-bridge (R3); reasoning: audit S2-9a.
- `rules/data/step_policy/soft_advance_instruction.json` — R5 soft-advance + exit_ramp wording (D/S2-4); reasoning: sign-off alignment check §3 + D decision.
- `prompts/declined_skills_instruction.json` — S2-7 B2 declined-skills signal.
- `prompts/offer_descriptions.json` — **EN blurb wording approved; `ar` pending** (status `approved-en-pending-ar`). EN offer-turn QUALITY scoring is the separate, still-open two-rater gate.
- `rules/data/skill_matching/skill_matching_rules.json` — both rules; `acute_direct_entry` signed against the recorded acute-substitution reasoning (substitution over `ignore_declined`, grounding-first activation-risk pool, **dbt_tipp excluded**). Reasoning: `docs/superpowers/escalations/2026-06-13-acute-substitution-redecision.md`.

On PR #8 branch (commit `151eaa0`):
- `prompts/templates/freeflow_guardrail.json` — S2-7 B1 guardrail; **the broadened discriminator (covers guided breathing/grounding beyond strict entry_screen, because box_breathing has no entry_screen) is RATIFIED** at sign-off. Reasoning: PR #8 description + audit S2-7.

## Decisions signed that have no draft envelope (recorded here)

- **S2-10 psychotic-referral routing (PR #6)** — A1 interrupt next turn, A2 pilot gated on the deterministic routing fix (prompt-adaptation is not the gate), A3 warm-interrupt (existing `psychotic_referral.json` content already matches). Rule 1 (engineering) = the code review (done). Reasoning: `docs/superpowers/escalations/2026-06-13-psychotic-referral-reachability.md`.
- **criteria_hold_count schema extension (D/S2-4)** — approved as a step_policy signal future skill authors may use; `mood_check_in` `hold_ceiling: 2` approved. Reasoning: clinical session brief item D.
- **C1 grounding-default** — affirmed (no code change); reasoning on record.
- **C2 unsigned keyword edits** — disposition: **SIGNED** `cbt_thought_record` "thought record"/"thought records" (skill's own name), `box_breathing` "i need to breathe"/"need to breathe right now", `progressive_muscle_relaxation` "shoulders are so tight"/"shoulders are tight", AND the two previously-routed judgment calls now approved: `box_breathing` "do with my breathing" and `interpersonal_effectiveness` "setting limits in". No revert. (Supersedes the pending state in `docs/work-orders/unsigned-keyword-edits-c2.md`.)

## Remaining gates (not cleared by this sign-off)

1. **Two-rater scoring** — EN offer-turn second rater + Khaleeji calibration/scoring. Long pole; gates PR #4 + Arabic. NOT started/complete.
2. **Pilot-scope confirmation** — English-only first exposure + a concrete exclusion mechanism (`docs/governance/2026-06-13-pilot-scope-decision.md`).
3. **Merges** — the product owner triggers all merges (sole-maintainer admin-merge bypasses review; flagged each time). Order: #6/#8 → #4 (after its scoring gate + the `_route_after_intent` rebase).
4. **External pre-launch audit** — `docs/work-orders/external-pre-launch-audit.md`.

## Status
Clinical gate: CLEARED and recorded. Scoring gate: OPEN. Nothing merged by engineering.
