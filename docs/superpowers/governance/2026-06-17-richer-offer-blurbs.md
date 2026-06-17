# Richer skill-offer blurbs — informed choice

Date: 2026-06-17
Branch: `feat/richer-offer-blurbs-2026-06-17`
Status: **clinician-approved approach (relayed via product owner)** — committed to branch, ship pending.

## What changed
All 25 `description.en` blurbs in `offer_descriptions.json` rewritten from a single clause to a
fuller one-line summary: **what it is + what you actually do + what it helps with + duration**.
`offer_descriptions.json` `_meta` bumped 0.2.0 -> 0.3.0.

Example (behavioral_activation):
- before: "picking one small doable activity to lift the week, planned together in about ten minutes"
- after: "picking one small, doable activity and planning together when and how you will do it, to
  gently rebuild momentum and lift your mood when everything feels flat, about ten minutes"

## Why
Users who do not want to commit to a multi-turn skill still need enough to make an informed
choice without starting it. A bare clause names the skill but not what you do or what you get.
Informed consent needs both *voluntary* (already handled: non-coercive offer framing) and
*informed* (this change). Product decision 2026-06-17.

## Scope decision
- **Intensity gating: deferred** (product call 2026-06-17). Richer blurbs ship for all intensities
  for now. The acute-distress trim and a user-controlled "tell me more" expansion remain open
  follow-ups, not in this change.
- No code change. Offer rendering, selection, and the consent model are untouched.

## Verification
- TDD: substance floor added to `test_engagement_templates.py` (blurb length 110-320; was a single
  `<=160` cap). Watched it fail RED on the terse blurbs (box_breathing 106 chars), then GREEN after
  the rewrite. New blurbs measure 163-196 chars.
- Em-dash ban already enforced by the same test (line 85); all new blurbs use commas.
- 56 offer/engagement/governance tests pass (`test_engagement_templates`, `test_offer_variation`,
  `test_skill_select_offer`, `test_clinical_governance`, `test_output_gate_offer_voiding`,
  `test_server_offer_voiding`, `test_declined_skills_signal`).
- Worst-case 2-option offer rendered and reviewed: informative, still one scannable line per option.

## Flags for the signer
1. **Wording is engineering-authored under the approved approach.** Clinician approved the approach
   (richer blurbs); final per-blurb wording is open to clinical tweak. v0.2.0 EN wording carried a
   2026-06-13 clinician content approval; this rewrites it.
2. **Arabic parity unchanged** — all `ar` fields remain null (output_gate translates EN at runtime).
   Verbatim Khaleeji blurbs still pending the Arabic clinical reviewer (S2-2).
3. **Separate open gate, not closed here:** two-rater EN offer-turn QUALITY scoring (noted in
   `_meta._signed_off`) is still outstanding.

## Remaining gates before a user sees this
clinical wording confirmation -> merge to master -> `railway up --service sage-api` (prod).
