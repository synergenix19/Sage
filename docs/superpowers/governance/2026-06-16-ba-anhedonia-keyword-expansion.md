# BA target_presentations expansion — activity-deficit / anhedonia

Date: 2026-06-16
Branch: `fix/ba-anhedonia-routing-2026-06-16`
Author: engineering (work session)
Status: **PENDING CLINICAL / GOVERNANCE SIGN-OFF** — committed to branch, NOT merged, NOT deployed.

## What changed
Added 12 English `target_presentations` keywords to `behavioral_activation.json` so that
activity-deficit / loss-of-interest disclosures route to Behavioral Activation at Tier 1
(deterministic keyword match), the architecture's sanctioned remedy for a missing-skill
match (§4.3 field note: "the fix for a missing skill is authoring broad `target_presentations`,
not extending Tier 2").

Keywords added:
`nothing for us to do`, `nothing else to do`, `nothing to do today`, `nothing to do anymore`,
`no activities`, `no activities that interest`, `anything that interests me`,
`interest me or excite me`, `don't feel like doing anything`, `dont feel like doing anything`,
`no hobbies`, `nothing i enjoy`.

No code changed. No `semantic_description` changed. No threshold changed.

## Why
Real test-user session `40a8ba18` (2026-06-07): user disclosed loneliness + loss of interest
("nothing for us to do", "no activities that interest me or excite me") across turns. No
existing BA keyword matched his wording, so Tier 1 never fired; Tier 2 surfaced **grounding**
(an acute-anxiety tool, score 0.4734) instead of BA. Result: generic suggestion list instead
of a structured activity plan. See RCA in conversation + replay against prod 2026-06-16.

## Why keywords, not semantic_anchors
Adding lived-experience phrasings to Tier 2 (`semantic_anchors` / `semantic_description`) is
explicitly out of bounds without a separate dual-index + its own threshold + Rule-1 approval
(`TIER2-DUALIDX` backlog, architecture doc line 1481). Tier-1 keyword authoring needs **no
recalibration**: `target_presentations` is not embedded in Tier 2 (§4.3, 2026-05-31), so
`calibrate_threshold.py` is a no-op for this change. Confirmed not run for that reason.

## Evidence / verification
- Tier-1 sim + unit tests: all 6 of his verbatim/paraphrased phrasings now route to BA.
  New tests: `test_ba_anhedonia_colloquial_routing` (6), `test_ba_idiom_not_misrouted` (3).
- False-positive guard: bare `nothing to do` was REJECTED in design because the idiom
  "it has nothing to do with my job" false-matched BA. Guard tests lock this in.
- Regression: `test_wrong_skill_routing` Tier-1 snapshot **125/125 pass** (no misrouting of
  any colloquial phrase). `test_skill_select` + `_offer` 74 pass. Schema valid.
- Substring-shadow invariant introduces **zero** new collisions (verified: identical 3
  collisions with and without this change).

## Flags for the signer
1. **Clinical sign-off required** before merge/deploy (clinical-content change). Same gate as
   prior `target_presentations` edits.
2. **Arabic parity is a follow-up, not in this change.** BA already carries Khaleeji keywords;
   dialect-accurate equivalents for the new phrasings need the Arabic clinical reviewer
   (do not invent dialect keywords without sign-off).
3. **Pre-existing, unrelated:** `test_no_new_substring_keyword_shadowing` already fails on
   master with 3 collisions (`setting limits in`, `thought records aren't helping`) from prior
   unaudited keyword edits. Not introduced here; tracked separately.
4. **Residual not covered by L1:** turns the LLM classifies `general_chat` never reach
   `skill_select`, so Tier-1 cannot help them. L1 recovers the user on his `new_skill` turn.
   Cross-turn recovery (active-issues state + suggest_skill) is a separate, sign-off-gated spec.

## Remaining gates before this reaches a user
clinical sign-off → merge to master → `railway up --service sage-api` (prod) → re-run prod
replay of session 40a8ba18 to confirm BA is offered.
