# F5 acceptance gate — pre-registration (CONDITIONAL DRAFT, registered before any F5 measurement)

**Date registered:** 2026-08-18 — **before the F5 rebuild is measured**, per the
pre-registration discipline (changing acceptance criteria after seeing F5's numbers would
be the violation this project's instruments were rebuilt to prevent).
**Status:** CONDITIONAL DRAFT. Becomes the gate of record when BOTH conditions land:
(1) Vee confirms the R3 flow property (a false-fire exits at the preliminary-question
stage); (2) the stage-2 transient-presenter fixture set is clinician-signed (sitting ask
6). Until both: **the currently in-force pre-registered gate (≥0.90 recall / ≤0.00 FP
against the governing oracle) stands unchanged.**

## The revised gate (effective on the conditions above)

- **Stage 1 (detector):** recall **≥ 0.90 against oracle v2's signed fire set
  (denominator 36)**, measured through the fixed harness only (version-stamped,
  unsigned-abort), against the v2 baseline captured on the pre-F5 detector
  (prediction-first, per R7 — never compared across oracle versions).
- **Stage 2 (preliminary-question flow):** **zero woven-SI questions reach a transient
  presenter**, asserted at CONVERSATION level on the clinician-signed transient-presenter
  fixture set — fixtures traverse the preliminary-question flow (duration / scope /
  context exclusion rules, Vee-authored Rules Service JSON) and the assertion is that no
  fixture's path ever reaches the SI probe. The current 15-lookalike list remains a
  detector-level instrument; it does not and cannot measure the relocated property.

## Instrument obligations this creates

- A stage-2 conversation-level evaluation instrument (new; built when the stage-2 flow
  exists — F6 consuming-side territory), subject to every instrument rule now standing:
  canonical home cited by SHA, serving-truth assertions, prod-parity flags via the
  register/enumerator, version-stamped fixtures, no in-process env mutation.
- The transient-presenter fixture set is **clinician-signed vocabulary under the same
  governance as the oracle** (signature block with version/date/review-by trigger per R2;
  manifest pin). Scaffold: `rules/data/safety/low_mood_3a_stage2_transients.json` (feat
  branch), TO-BE-AUTHORED at the sitting.

## Fallback branch

If Vee does not confirm the flow property: R3's fallback applies — she sets an explicit
detector-level FP tolerance, and this pre-registration is re-issued with that number in
place of the stage-2 clause before any F5 measurement.
