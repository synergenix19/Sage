# Product-Owner Risk Acceptance: Deploy Khaleeji dialect fix with A4 §20.1 OPEN

> **Status:** RESOLVED — A4 §20.1 Dialect-QA approved by clinical lead 2026-06-16; gate CLOSED. The risk window below is no longer outstanding.
> **Date:** 2026-06-16
> **Authorized by:** Product owner / admin (synergenix), explicitly, via Claude Code session.
> **Change:** PR #32 — `feat/dialect-exemplars-offer-variation`.
>
> **Resolution (2026-06-16):** Clinical lead approved the A4 §20.1 Dialect-QA (verdict PASS, relayed via product owner). `_signed_off` filled and `status: approved` set on all three artifacts. The deploy-with-gate-open window is closed retroactively; no revert required. Record: `docs/superpowers/governance/2026-06-16-khaleeji-a4-dialect-eval.md`.

## Decision
The product owner directed an **admin-bypass merge to `master` and a production Railway
deploy** of the Khaleeji dialect fix and skill-offer variation, **despite**:

1. **A4 §20.1 Dialect-QA gate OPEN** — no native Emirati rating completed. The gate states:
   *no Arabic dialect output reaches real users until a native Emirati rater signs off.*
2. **Three artifacts still `_signed_off: ""`** (NOT clinically/linguistically signed):
   - `src/sage_poc/data/khaleeji_translation_exemplars.json`
   - `src/sage_poc/prompts/templates/L2_intents/skill_offer.json` (v0.2.0)
   - `src/sage_poc/prompts/templates/L2_intents/skill_offer_reoffer.json`
3. **PR branch protection bypassed** — `reviewDecision: REVIEW_REQUIRED`, 0 reviews; merged with `--admin`.

These artifacts are intentionally LEFT as `draft_pending_signoff`. Admin risk acceptance is
NOT clinical/linguistic sign-off; the record stays truthful.

## Risk accepted
- Uncertified Khaleeji dialect output reaches real Arabic users. Residual Syrian/Levantine
  drift or unnatural register is possible (the very bug this change targets is intermittent
  and not yet rater-verified).
- Offer-template wording (English-only offers) is live without clinical sign-off.

## Not affected
- Deterministic crisis/safety layer is unchanged.
- R1 consent offers remain English-only (`arabic_offer_excluded`); offer changes do not touch Arabic.
- Full test suite: zero regressions vs `master` baseline.

## Required follow-up (does NOT lapse with deploy)
1. **Complete A4** — native Emirati rater fills `docs/superpowers/governance/2026-06-16-khaleeji-a4-dialect-eval.md`.
2. On **PASS**: fill `_signed_off` on the three artifacts (retroactive), close A4 §20.1.
3. On **FAIL**: fold corrections into `khaleeji_translation_exemplars.json`, re-run the harness,
   redeploy — or revert (see below).
4. Monitor Arabic production sessions for dialect quality in the interim.

## Reversion path
PR #32 merged as a merge commit (atomic commits preserved). Translator change isolates to
commit `370df3b` (few-shot translator) + `5253ca6` (exemplars). Part A (Arabic) can be reverted
independently of Part B (English offer variation) if A4 fails.
