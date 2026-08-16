# EMR Phase 3 — distributional deltas report (2026-08-12)

Three measurement arms, all N=10 per fixture, all through the parity instrument
(quiescence attested, DB pool AVAILABLE, provenance ON, 0 degraded turns in every
citable arm):

1. **Baseline-of-record** (`2026-07-31-emr-phase0-baseline.md`, PR#401): flag OFF,
   serving parity.
2. **Fix-arm, main family** (`2026-08-12-emr-phase3-fix-arm.md`): the single deliberate
   delta `SAGE_MODALITY_REQUEST_ROUTING=true`, stamped `deliberate_override` with the
   post-export self-check.
3. **Loop-closure extension family** (`2026-08-12-emr-phase3-screen-completion.md`,
   fixture family `emr_screen_completion_family.json`): sessions that continue past the
   screen with naturalistic answers. NOT a baseline comparator (different turn
   structure); cited only for the post-screen leg.

## The defect metric: request-drop rate

The plan's defect class is "active or passive dropping of a user's explicit request."
Under the SIGNED screening rules (Vee 2026-07-29 items 1-3, adopted-sentence pin
2026-08-11), the conformant response to an unscreened request is the SCREEN, so
offer-rate on the request turn is no longer the conformance metric — request-drop rate is.

| surface | baseline (OFF) | fix-arm (ON) |
|---|---|---|
| S1 active-skill absorption | 10/10 absorbed into psychoed exploration step | **0/10 dropped** — 10/10 exit-with-rehand (`modality_request_routed:executor`) then screen |
| S2 info_request KB fall-through | 8/10 fell to KB/freeflow (offer 0.20) | **0/10 dropped** — 10/10 screen-first |
| S3 request over pending offer | modal `offer_accepted` (flip-prone, first-line 0.00) | **0/10 dropped** — 10/10 deterministic `offer_released_modality_request` (released ≠ declined) then screen |
| PARA family (12 fixtures) | 12/12 offered UNSCREENED (first-line only 7/12) — nonconformant under the signed screen rules | 12/12 screen-first, 0 unscreened offers |

**Drop rate on the three defect surfaces: baseline ~28/30 dropped or nonconformant;
fix-arm 0/30.**

## Loop closure (extension family, the post-screen leg)

| case | offer-rate | first-line rate | note |
|---|---|---|---|
| SC-001 cold request → answer | 1.00 | 1.00 | screen → acute answer → first-line pair offered |
| SC-002 mid-psychoed request → answer | 1.00 | 1.00 | rehand → screen → answer → offer |
| SC-003 chronic answer | 1.00 | 1.00 | cleared WITH `modality_request_referral_context` in the modal path (the signed "alongside" reading, measured) |

First-line rate 1.00 across all 30 samples: **DF-1 is closed on the request path — the
binding table owns ordering, and it serves the section-1a Tier-1 pair every time.**
Mechanism-flip rates (0.30-0.50) are intent-LABEL variance with IDENTICAL behavioral
terminals (first-line 1.00 proves it) — the deterministic detector neutralizing the
Node-2 bistability, visible in data.

## Conformance neutrality (non-request categories)

CTRL-001 (genuine info ask), CTRL-002 (benign chat), CTRL-003 (info ask, KB): modal
paths IDENTICAL to baseline under the fix-arm, 0 degraded. No modality marker appears on
any control sample. The mechanism touches request turns only.

## The campaign's instrument ledger (four defects caught pre-flip, all fixed + merged)

1. Override never reached the process env (artifact claimed ON, run was OFF) → both
   maps patched + post-export refusal self-check (#430).
2. Lexicon recall: 9/12 naturalistic paraphrases missed → +12 entries from measured
   misses, 15/15 family recall, cap 32→48, latency re-asserted (#430).
3. D1 crossed-wires + missing resumption leg (screen answer had no delivery path) →
   preserve-not-force on the shared terminal; `modality_screen_pending` hold with
   delivery/continuation/abandonment semantics (#431).
4. Instrument per-turn resets diverged from serving (stale `screen_question_text`
   nulled a fresh offer — impossible in prod) → `run_fixture` now builds every turn
   through the REAL `server_helpers._build_state` (single-sourced, #432).

Also caught mid-campaign: the shared-key credit exhaustion (402) that degraded prod —
resolved by top-up; the deterministic crisis path held throughout (probed live).
Runbook note: evidence runs should move to a separate OpenRouter key/limit.

## Measurement boundary, stated

Single-window measurement (window-bounded verification rule): these arms establish the
mechanism's behavior under the current pins in one window. Any SERVED claim after a
future flip requires its own live verification; the regime-aware smoke pattern is the
standing vehicle. N=10 per fixture; the trajectory-flip readout doubles as the
distributional-stability record.

## Flip readiness

Everything engineering-side is merged and dark. The governed flip requires, in order:
1. **Vee's lexicon sign-off** (the one open clinical touchpoint): request lexicon (44
   entries incl. the recall extension), screen supplied-detection markers, binding
   table rows. All draft-pending-review in
   `skill_request_phrases.json` / `modality_screen.json`.
2. Register PR (`SAGE_MODALITY_REQUEST_ROUTING` → `"true"` with her signature_ref) +
   `apply_prod_flags.py --apply` under the deploy discipline.
3. Post-flip live verification (regime-aware assertions + the request-family live
   probes), two windows for the served-stability claim.
