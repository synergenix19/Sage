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

## Q4 — Do the matrix v5 §1a presence_only runs share this signature? (ANSWERED 2026-07-28)

Per-run mechanism is NOT recoverable from stored v5 artifacts (the full-graph
instrument persists only aggregate Counters; per-turn intent/path is fetched and
discarded, `measure_layer1_fullgraph.py:184-189,277-306`; no per-run output file
exists on disk). It IS answerable by construction, three ways:

1. **Absorption was architecturally impossible in the v5 harness:** each corpus
   utterance runs in a fresh thread as a single turn; no skill can be active.
2. **Consult was OFF:** both v5 runs record `SAGE_INFO_REQUEST_CONSULT=None` (=OFF);
   the flip landed 2026-07-23, after the v5 §1a rows.
3. **The v5 §1a corpus never tests the request behavior at all:** its five cases are
   single-turn bare-affect disclosures ("I feel a bit anxious", ...), not exercise
   requests. Their presence_only outcomes are the `general_chat` gate working on bare
   emotional words, i.e. the intent-SPOF guard BY DESIGN, in tension with §1a's
   expected flow but deliberate.

Consequences:
- **Baseline validity (measurement-validity statement for any future packet):** the
  v5 §1a "2/5 baseline" measures a different corpus (bare-affect) under a different
  mechanism regime (pre-flip, absorption-impossible) than the observed gap (explicit
  request absorbed mid-psychoed, post-flip, multi-turn). A before/after delta against
  it is uninterpretable. Any fix needs a NEW multi-turn request-conformance fixture
  family as its baseline; v5 §1a is not a comparator.
- **Two distinct classes, only one is a defect:** (i) bare-affect presence_only =
  deliberate SPOF guard, conformance-vs-spec tension to be adjudicated, not patched;
  (ii) branch-(d) absorption = the live defect this workstream addresses.
- **Readback coverage hole (systemic):** `SAGE_INFO_REQUEST_CONSULT` is not among the
  `/health/version` raw_env fields, so the v5 parity stamp could not assert it; the
  same hole enabled this memo's own Q6 parity failure (below). Remediation belongs
  with the parity incident record.

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

## Q6 — Does a medical-guard pathway fire on cardiac red-flags? (CORRECTED 2026-07-28)

**The original finding in this section was an instrument artifact and is WITHDRAWN as
a prod claim.** The first characterization run's "prod parity" flag set was
hand-derived from a memory summary of flag DELTAS and treated as the full set; it
omitted `SAGE_MEDICAL_REDFLAG_GUARD` (and `SAGE_VENTING_SUPPRESSION`,
`SAGE_ROUTE_PRECEDENCE`, `SAGE_D1_SCREEN`), all of which the authed prod serving
readback (`GET /health/version`, verified live 2026-07-28) reports as
`true`/`raw_env="true"` at serving SHA 1f687c57. Primary sources agreeing: serving
readback, Railway prod variables, matrix-v4 as-live flag record, and
`ARCHITECTURE_BOUNDARIES.md:175` ("off (test default); prod has it on"); the E1-E7
approval records ON as the intended production state.

What the probe actually demonstrated: the graph's behavior WITH THE GUARD OFF, which
is the local-test default, not prod. The observed "PMR offer served over crushing
chest pain" is therefore a statement about a non-prod configuration. A rerun of both
probe and 3-turn transcript under the corrected serving flag set is in flight; its
readout supersedes the first run's on every point of difference.

Residual REAL findings from this thread:
- **Parity incident (process):** a characterization instrument escalated a false
  BLOCKING prod-harm claim because its flag set bypassed the runner's
  derive-from-readback discipline. Recorded as its own incident:
  `2026-07-28-parity-incident-q6-artifact.md`. This is the second documented instance
  of the guard-off-by-default trap producing a false full-graph readout (first:
  `2026-07-21-d1-reflip-attempt2-halt.md`).
- **Fail-open default (design):** a clinical safety guard whose config default is
  `false` makes every naively-parameterized local instrument measure a guard-less
  system. Remediation options (readback-derived flags mandatory for instruments;
  and/or flipping the code default) belong in the incident record's follow-ups.
- **DF-2 stands as a code question** (below-threshold candidate served via
  `default_offer`) — observed under guard-off; whether any prod path can reach it
  needs the code read; reported inside the parity incident record, per review.

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
4. **Q6 disposition (corrected):** no clinical escalation; the guard is ON in prod
   (serving-readback verified). The process incident and its follow-ups live in
   `2026-07-28-parity-incident-q6-artifact.md`.

The screen-design clinical questions
(`2026-07-28-1a-screen-design-clinical-questions.md`) remain valid under every branch:
screening gates delivery wherever detection lives.
