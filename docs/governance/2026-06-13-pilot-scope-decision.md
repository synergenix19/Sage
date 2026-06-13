# Pilot-Scope Decision — First Exposure is English-Only; Arabic Stays Gated Behind S2-2

**Date:** 2026-06-13
**Decision owner:** Product (pilot scope) + Clinical lead
**Status:** RECORDED per product-owner direction 2026-06-13 — needs (a) formal confirmation and (b) a concrete exclusion mechanism named (see below). Writing it down now because it is currently *implied by the dependency graph rather than stated*, and an implied gate is the kind that gets walked through by accident.

## The decision

**At first pilot exposure (when PR #4's gates clear and it merges), the pilot is ENGLISH-ONLY. The Arabic path is excluded until S2-2 lands and its gates clear.**

"Arabic gates" = all three:
1. S2-2 implemented and merged (Khaleeji accept-classification: raw-Arabic in the PENDING OFFER block, Khaleeji exemplars + `ابي` disambiguation, ordinal tolerance; live-classifier Khaleeji contract suite green).
2. Two-rater Khaleeji scoring complete (the calibration long pole) — `docs/work-orders/human-scoring-protocol.md`.
3. Khaleeji blurb work order closed (authored `ar` display names + descriptions, clinician-signed) — the S2-2 plan's blurb handoff.

## Why this is not optional

The PR #4 audit found, live, that Khaleeji accept parsing is **broken**: bare "ايه" and positional "ابي الثاني" classified as `offer_ignored` (not promoted), and the responder mistranslated "ابي" ("I want") as "my father". A pilot that exposes the Arabic accept path **before S2-2 lands would walk straight into the exact failure the audit found** — a consent gate that silently fails to register an Arabic user's acceptance, with the chained risk (audit ar-04) of ungoverned freeflow exercise delivery. The English consent flow, by contrast, is audited and (once PR #4's gates clear) ready.

## The one engineering gap to close before this is real

**The exclusion must be a mechanism, not an intention.** "English-only pilot" has to be enforced, not assumed. Confirm which:
- **Cohort restriction** — the pilot user set is English-speaking only (operational/recruitment control), and/or
- **Runtime gate** — `detected_language == "ar"` (and Arabizi, currently detected as `en` — see the §6.4 named decision) is routed out of the pilot / to a holding response until the Arabic gates clear.

Note the Arabizi wrinkle: Arabizi ("ana ta3ban", "abi el thani") is detected as `en` today, so a runtime `detected_language=="ar"` gate would NOT catch an Arabizi user — they would reach the English path. If the pilot cohort can produce Arabizi, the exclusion needs cohort control, not just a language-detection gate. (Arabizi offer-acceptance is separately out of S2-2 scope, on the 2026-06-08 Arabizi plan.)

## Decision capture
- [ ] First-exposure pilot is English-only — confirmed by: __________ (product), __________ (clinical lead), date: ______
- [ ] Exclusion mechanism: ☐ cohort restriction ☐ runtime language gate ☐ both — described: __________
- [ ] Arabizi handling under the chosen mechanism confirmed (cohort control if Arabizi is possible)
- [ ] Arabic exposure unblocked only when S2-2 merged + two-rater scoring complete + blurb work order closed

## Status
RECORDED, pending formal confirmation + exclusion-mechanism naming. This is a one-decision item; it prevents a known, audited failure from reaching real users.
