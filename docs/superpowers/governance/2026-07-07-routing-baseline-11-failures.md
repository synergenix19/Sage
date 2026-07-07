# Routing baseline: ~11 failures at the threshold margin (2026-07-07)

**Class:** Lane 1 (Safety/ML routing), not Lane 2. Surfaced during a Lane 2 skill-registration attempt but independent of it.

## Finding
`test_wrong_skill_routing::test_full_routing` has **~11 failing cases on trunk** (master, pre-existing — reproduced on a clean worktree; the new `mindfulness_meditation` skill is NOT a candidate, so it is not the cause). Every failing phrase scores in the **0.45–0.48 band** against `SEMANTIC_THRESHOLD=0.4593` (`nodes/skill_select.py`). This is the **S-4 known limitation (rule-matching sensitivity)** now visible as red tests on the trunk.

## Failing cases (expected skill → phrase)
- `mi_readiness_ruler` → "I have really mixed feelings about getting help, I don't know where I stand"
- `mi_readiness_ruler` → "Part of me wants to get better and part of me doesn't see the point"
- `mood_check_in` → "I need to get clear on my emotional state before we do anything else"
- `mood_check_in` → "I feel like something is off but I can't identify what it is"
- `problem_solving_therapy` → "I've been stuck on this issue for weeks and need a clear process"
- `problem_solving_therapy` → "I keep hitting the same dead ends with this situation and I can't find a solution"
- `problem_solving_therapy` → "I want to think through all my options in a structured way"
- `worry_time` → "My brain keeps cycling through worst-case scenarios about things I can't control"
- `financial_anxiety` → "I can't stop mentally calculating whether my money will last the month"
- `interpersonal_effectiveness` → "I always give everything in relationships and I never get what I need back"

## Skill-vs-spec evaluation (BOT BEHAVIOUR = source of truth for which skills to offer)
- **`mi_readiness_ruler` — NOT in the spec.** No MI / readiness-ruler skill; the lone "motivational" mention (spec line 454) is a *problem-solving guard*, not a skill. It is in the collision zone with the incoming `mindfulness_meditation` AND owns 2 of the failing cases. **Primary deprecation candidate** — but deprecation removes a therapeutic capability, so it is a **clinical + product decision**, routed there (do not deprecate unilaterally).
- **`interpersonal_effectiveness` — named skill not in spec** ("interpersonal" 0 mentions); its function is covered by `assertive_communication` (spec: "Assertive Communication" / "Boundary Setting", 33 mentions). **Secondary redundancy/deprecation candidate**, clinician+product call.
- **`mood_check_in`, `problem_solving_therapy`, `self_compassion_break`, `worry_time`, `financial_anxiety` — all IN the spec.** Keep. Their failures are the threshold-margin/rule-sensitivity issue, not "wrong skill exists."

## Consequence for MM registration (prerequisite ordering)
**Fixing this baseline is a PREREQUISITE to registering `mindfulness_meditation`, not a casualty of it.** Recalibrating `SEMANTIC_THRESHOLD` against a fragile baseline bakes the fragility in, and MM's semantic neighborhood ("sitting with feelings", "observing thoughts") lands exactly on this 0.45–0.48 band. Sequence: stabilize the baseline (and resolve the mi_readiness_ruler/interpersonal_effectiveness deprecation question) → then register MM with a full-registry before/after routing comparison.

## Relevance to Gap #65
The marginal 0.45–0.48 band is exactly where the "semantic-tier vs threshold-tuning" question in Gap #65 lives. The failing-phrase list is attached to the Gap #65 decision package as empirical evidence (`2026-07-05-gap65-detection-tier-decision.md`).
