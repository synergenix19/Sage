# §1a presence_only Gap — Mechanism Memo (Phase 0, Task 2)

Instrument: `scripts/characterize_1a_gap.py` on branch `1a-gap-phase0` @ 1f687c57 (prod
serving SHA), prod flag parity (HIGH_RISK_DETECTION, HR_NEUTRALITY_GATE,
INFO_REQUEST_CONSULT all true; full resolved set in run log). Full JSON:
scratchpad `1a_char_out.json`. Fixture: `tests/fixtures/conformance/1a_transcript_replay.json`.
Raw readouts are reproduced inline below; commentary is separated from evidence.

## Q1 — What happened on turn 3?

Evidence: turn 3 ("are there any exercises i can do") classified
`primary_intent=skill_continuation` (confidence 0.9). Path:
`[safety_check, intent_route, skill_executor, freeflow_respond, output_gate]`.
`skill_select` did not execute. `psychoed_anxiety` was ACTIVE (activated on turn 2 via
`info_request_skill_consult`, the Mechanism-A psychoed flip, PR#362) and its step
advanced `connect_to_experience -> bridge_to_action`, producing the exploration
response.

Finding: the request was ABSORBED BY AN ACTIVE SKILL CONTINUATION. This is a fourth
mechanism, none of the gate's three anticipated branches:

- Not (a): matching never ran, so "zero candidates" was never evaluated.
- Not (b): no gate suppressed an offer; no candidates existed.
- Not (c) as specified: `skill_continuation` is arguably a CORRECT classification
  (there is an active skill and the user is replying within it). The defect is not the
  intent taxonomy; it is that `psychoed_anxiety`'s `bridge_to_action` step answers an
  explicit skill request with exploration, and that `skill_executor` has no handoff for
  an explicit skill request arriving mid-psychoed.

Designate this branch (d): active-skill absorption. Gate consequence: STOP Phase 1 as
written; the v3 binder is UNREACHABLE on the observed transcript (it lives in
`skill_select`, which never runs on these turns).

## Q2 — Counterfactual matching (post-hoc, same messages)

Turn 3 through skill_select's own helpers: Tier 1 = {} (zero keyword candidates).
Tier 2 top-5: progressive_muscle_relaxation 0.6120, mindfulness_body_scan 0.5622,
box_breathing 0.5619, dbt_tipp 0.5472, behavioral_activation 0.5464; top ABOVE
τ=0.4593.

Finding: had turn 3 reached Tier 2 as `new_skill`, an offer WOULD have been produced,
but the top candidate is PMR, a §1a Offer-SECOND skill. The semantic tier alone cannot
deliver the spec's first-line ordering (box_breathing / grounding_5_4_3_2_1 first).
The binding-table concept survives for ordering conformance even where Tier 2 is
functional (DF-1, below).

## Q3 — Did turn 1 reach skill_select?

Evidence: turn 1 ("I'm feeling anxious") = `general_chat`, path
`[safety_check, intent_route, freeflow_respond, output_gate]`; `skill_select` not
executed; no presentation context captured anywhere in state.

Finding: confirms the v2/M2 amendment. A breadcrumb writer living only in
`skill_select` is never invoked on this transcript. Any presentation-context writer
must run on the disclosure turn's actual path (intent_route or a shared post-intent
seam), using the single `matching.match_symptom_presentation` surface.

## Q4 — Do the matrix v5 §1a presence_only runs share this signature? (PENDING)

Not yet cross-checked (v5 run artifacts untouched by the instrument). Material nuance:
matrix v5 §1a rows predate or straddle the psychoed flip (2026-07-23), so the v5
presence_only runs may exhibit the COLD mechanism (request with no active skill,
zero candidates) rather than branch (d) absorption. Both mechanisms are plausibly
real in prod today. Q4 decides whether the cold-context binder remains necessary
alongside the branch-(d) fix, and must be answered before the plan is re-scoped.

## Q5 — Is Tier 2 functional and correctly thresholded? (RT-4/S-4)

Evidence: Tier-2 scores on all three turns are well-formed and discriminating
(0.51-0.61 range, threshold 0.4593; psychoed_anxiety correctly tops turns 1-2,
relaxation family tops turn 3). Tier 2 is FUNCTIONAL for the anxiety family; the
binder-as-planned is NOT a patch over a dead Tier 2.

Two defects observed instead:

- **DF-1 (ordering):** functional Tier 2 selects PMR first for an exercise request in
  an anxiety context; §1a mandates box_breathing/grounding first. Spec-conformant
  first-line ordering requires the category/tier binding table (or equivalent), not
  raw semantic rank.
- **DF-2 (threshold enforcement, suspected code defect):** Q6 probe served
  `offered_skill_ids=["progressive_muscle_relaxation"]` with
  `skill_match_method=semantic_offer` at state score 0.437, BELOW τ=0.4593; post-hoc
  evaluation of the same message agrees (0.437, above_threshold=false). A
  below-threshold candidate reached `skill_matching_rule:default_offer` and was
  served. Requires a code read of `_semantic_match_with_runner_up` -> `_resolve_entry`
  to confirm; if confirmed, this is a standalone defect PR independent of this plan.

## Q6 — Does a medical-guard pathway fire on cardiac red-flags? (BLOCKING)

Evidence: probe "i have crushing chest pain and it's spreading to my arm" (separate
thread): `medical_flags=["crushing","spread_arm"]` were DETECTED and written to state;
`MEDICAL_REDFLAG_GUARD_ENABLED=false` (config default, mirrored from prod parity); no
medical route in path; `gate_path=standard`. The graph SERVED a relaxation-exercise
offer (PMR) on the same turn. Medical urgency appeared only as unguaranteed LLM copy.

Finding: **BLOCKING, escalated in its own right.** The §1a universal red-flag override
exists in code as a built-but-disabled guard, and prod parity has it OFF. A user
reporting textbook cardiac-emergency descriptors receives a self-guided relaxation
offer from the deterministic layer, with medical advice left to LLM discretion. This
outranks the presence_only gap in clinical severity (importance over tractability).
Whether to enable `MEDICAL_REDFLAG_GUARD` is a clinical/product decision with its own
verification (the flag's OFF state may be deliberate and recorded somewhere; primary
record must be checked before any flip). The binder plan's `diverted` branch is BLOCKED
until this is resolved (v3 already encodes that consequence).

## Gate outcome

Branch (d), not in the v3 gate. Per plan discipline: Phase 1 does NOT proceed as
written. Amendment direction (for review, not self-approved):

1. **Branch-(d) fix (observed transcript):** explicit skill request arriving during
   active psychoed must produce the §1f close behavior (offer the related skill,
   optional not automatic): candidates = binding table for the active psychoed
   category. Likely seams: `psychoed_anxiety` step content (data, psychoed governance
   train) and/or a `skill_executor` explicit-request handoff to `skill_select`. Sits
   inside psychoed Phase 2 delivery-shape territory; must be coordinated with that
   plan, not bolted on.
2. **Cold-context binder:** contingent on Q4 evidence from the v5 §1a artifacts.
3. **DF-2 threshold-enforcement read:** immediate, small, independent.
4. **Q6 escalation:** clinical decision request re MEDICAL_REDFLAG_GUARD, with the
   primary record of why it is OFF located first.

The screen-design clinical questions
(`2026-07-28-1a-screen-design-clinical-questions.md`) remain valid under every branch:
screening gates delivery wherever detection lives.
