# L2 Engagement Batch — Clinical Sign-off Register — 2026-07-07

**Recorded by:** Engineering, operationalizing the clinical lead's approval relayed by the product owner on 2026-07-07.
**Signer of record:** Rohan Sarda (clinical lead). Recorded in each artifact's `approved_by` + `_signed_off` fields.
**Session artifact:** `2026-07-07-l2-engagement-review-packet.md`. Deviation register: `2026-07-07-l2-engagement-deviation-register.md`. Eval: `2026-07-07-l2-engagement-promptfoo-results.md` (4/5, list-compat ACCEPT).

## Decisions ratified

- **Bridge rule (a\*)** — deterministic single conditional-invitation close, affect-neutral by phrasing, no runtime detection. (b) and (c) rejected per the packet.
- **List-compat: ACCEPT** — a symptom list may open without a one-sentence prose lead-in; the PromptFoo case is rewritten to encode this (bridge + affect-neutrality still asserted). The lead-with-prose (L4) concern is DEFERRED to the Falcon-34B re-run, not closed.
- **PI-SI-001: single-rule ordered-contract form** (the two-rule split was offered and declined).
- **Deviation register:** L2 per-intent budget amendment (item 1) and intent-taxonomy note (item 2) ratified; `l3_owned` posture (skill_continuation) ratified.

## Artifacts promoted (approved_by = "Rohan Sarda (clinical lead)", status → approved, effective_date 2026-07-07)

| Artifact | From → To | Notes |
|---|---|---|
| `L2_intents/info_request.json` | v1.0.0 → **v2.0.0** | rule (a\*); budget 50→160 (rides amendment) |
| `L2_intents/new_skill.json` | v1.0.0 → **v1.1.0** | conditional-invitation; budget 50→100 |
| `L2_intents/exit_skill.json` | v1.0.0 → **v1.1.0** | conditional-invitation; budget 50→80 |
| `L2_intents/low_confidence.json` | v1.0.0 → **v1.1.0** | content RATIFICATION of PR #124 frozen text (byte-identical); 2-sentence cap is safety-coupled |
| `rules/data/prompt_injection/secondary_intent.json` (PI-SI-001) | v1.0.0 → **v2.0.0** | generic DBT → v7 §5.6.1 ordered contract, grounding/ABSTAIN-aware; `active: true` |

## What this sign-off clears — and what it does NOT

CLEARS: the clinical content gate for the five artifacts above + the register ratification.

DOES NOT CLEAR (unchanged from the packet): PR #124 engineering review; the overflow/L1-budget defect #125 (coupled to the budget amendment); merge authority for #128; and deploy authority. Merge #128 and the production deploy remain the product owner's explicit triggers; deploys are manual.

## Manifest guard obligation — discharged in this commit

Per merged PR #127, promotion re-confirmed each template's engagement posture and bumped `classified_against_version` in `prompts/l2_engagement_manifest.json` (info_request→2.0.0, new_skill→1.1.0, exit_skill→1.1.0, low_confidence→1.1.0), so the version-drift guard stays green.

## Merge-order note (low_confidence ↔ PR #124)

`low_confidence.json` content here is byte-identical to PR #124's frozen text. Recommended order: merge **#124 first** (the composer-migration mechanism), then this batch — then the low_confidence diff is version/approval-only and merges cleanly. #124's node + composer changes are NOT in this batch and remain required.
