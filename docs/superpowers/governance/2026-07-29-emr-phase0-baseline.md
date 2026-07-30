# EMR Phase-0 PIPELINE SHAKEDOWN — explicit-modality-request handling (distributional, pre-fix)

> **RELABELED per PO close-read ruling (2026-07-30): this artifact is the instrument
> SHAKEDOWN, not the baseline-of-record.** The run executed with `DATABASE_URL` unset, so
> `knowledge_retrieve` abstained on every KB-path turn — a run-environment degradation the
> header did not record as a field (instrument gap, same class as `classifier_degraded`).
> Everything else about the run is template-clean (quiescence attested, 0 degraded turns,
> refusal log empty) and it proved the pipeline end-to-end. The **baseline-of-record is the
> DB-present re-run** (2026-07-30 artifact); comparisons for the EMR re-plan cite that
> artifact, never this one.

<!-- instrument-parity header block (signed standing rule 2026-07-28) — template artifact -->

## Provenance (instrument-parity header block)

- **Instrument:** graph_evidence.py FULL-GRAPH app.ainvoke, N independent session threads per fixture; flags derived from /health/version serving readback (refuse-on-gap, refuse-on-deploy-window); signed instrument-parity standing rule 2026-07-28
- **Generated at:** 2026-07-29T20:30:19+00:00
- **Serving readback:** https://sage-api-production-3328.up.railway.app /health/version
- **Build SHA (from readback):** `dec4a9e7f4de3ad4bd4c560db81f1f499c890787` (source: SAGE_BUILD_SHA)
- **Local tree SHA (code measured):** `b5ff458a212a60deab9b231a416708109e304a95`
- **Classifier model:** `openai/gpt-4o-mini`
- **OpenRouter provider pin:** `openai`
- **Requested classifier seed:** `20260728`
- **Seed-honor signal (system_fingerprint):** `fingerprint_varied_backend_mix` — distinct: ['fp_0189089ecf', 'fp_c400bf5046']
- **N per fixture:** 10
- **Degraded turns (static-fallback signature general_chat@0.5):** 0
- **Railway (desired) available:** True | **deploy-window checked:** True
- **Parity note:** readback coverage hole (18 var(s) asserted via railway, not the serving readback): SAGE_CLASSIFIER_MODEL, SAGE_D5_ACUITY_FLOOR, SAGE_D5_ACUITY_GATE, SAGE_FALLBACK_CLASSIFIER_MODEL, SAGE_FALLBACK_RESPONDER_MODEL, SAGE_HIGH_RISK_TERMINAL, SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD, SAGE_MEDICAL_REFERRAL_TEXT, SAGE_NATIVE_ARABIC_SHADOW, SAGE_PSYCHOED_CATEGORIES, SAGE_PSYCHOED_PATHWAYS, SAGE_RESISTANCE_MODEL, SAGE_RESPONDER_MODEL, SAGE_SKILL_OFFER_COOLDOWN_ENABLED, SAGE_SKILL_OFFER_COOLDOWN_TURNS, SAGE_SKILL_RUNNER_UP_MARGIN, SAGE_SKILL_RUNNER_UP_MIN, SAGE_TRANSLATOR_MODEL — widen /health/version *_raw_env to close (standing-rule 3 pattern).
- **Parity note:** NOTE: LOCAL tree b5ff458a212a != SERVING build dec4a9e7f4de — flags are serving-derived but the code under measurement is the local tree; cite accordingly.
- **Parity note:** quiescence attestation: cause=item1-condition-a; deploy cycle spanned: deployment id changed 543fd26a-7d5c-424b-a1b4-922108d758c1 -> 90cd7f83-d9c1-4c59-85d8-2601db2fd444 between clean checks 2026-07-29T19:30:51+00:00 / 2026-07-29T19:51:35+00:00
- **Parity note:** quiescence refusal log: empty (no refusals recorded)

### Resolved flag set (full, with coverage source)

| var | effective value | coverage |
|---|---|---|
| `SAGE_AUDIT_CLASSIFIER_PROVENANCE` | `true` | serving_readback |
| `SAGE_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | railway_desired |
| `SAGE_CLASSIFIER_SEED` | `20260728` | serving_readback |
| `SAGE_CONSULT_SOURCES` | `true` | serving_readback |
| `SAGE_COSINE_ABSTAIN_THRESHOLD` | `0.42` | serving_readback |
| `SAGE_CRISIS_TIERING` | `None` | serving_readback |
| `SAGE_D1_SCREEN` | `true` | serving_readback |
| `SAGE_D1_SCREEN_SHADOW` | `true` | serving_readback |
| `SAGE_D5_ACUITY_FLOOR` | `8` | railway_default |
| `SAGE_D5_ACUITY_GATE` | `false` | railway_default |
| `SAGE_DEREALIZATION_DETECTION` | `None` | serving_readback |
| `SAGE_FALLBACK_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | railway_default |
| `SAGE_FALLBACK_RESPONDER_MODEL` | `openai/gpt-4o` | railway_default |
| `SAGE_HIGH_RISK_DETECTION` | `true` | serving_readback |
| `SAGE_HIGH_RISK_TERMINAL` | `None` | railway_default |
| `SAGE_HR_NEUTRALITY_GATE` | `true` | serving_readback |
| `SAGE_INFO_REQUEST_CONSULT` | `true` | serving_readback |
| `SAGE_IPV_PREEMPTION` | `false` | serving_readback |
| `SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD` | `0.015` | railway_default |
| `SAGE_MEDICAL_REDFLAG_GUARD` | `true` | serving_readback |
| `SAGE_MEDICAL_REFERRAL_TEXT` | `The symptoms you're describing can be signs of a medical emergency. ` | railway_default |
| `SAGE_NATIVE_ARABIC_SHADOW` | `false` | railway_default |
| `SAGE_OPENROUTER_PROVIDER_PIN` | `openai` | serving_readback |
| `SAGE_PANIC_GROUNDING_OVERRIDE` | `true` | serving_readback |
| `SAGE_PSYCHOED_CATEGORIES` | `` | railway_default |
| `SAGE_PSYCHOED_PATHWAYS` | `None` | railway_default |
| `SAGE_RESISTANCE_MODEL` | `None` | railway_default |
| `SAGE_RESPONDER_MODEL` | `openai/gpt-4o` | railway_desired |
| `SAGE_ROUTE_PRECEDENCE` | `true` | serving_readback |
| `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` | `true` | railway_desired |
| `SAGE_SKILL_OFFER_COOLDOWN_TURNS` | `2` | railway_default |
| `SAGE_SKILL_RUNNER_UP_MARGIN` | `0.05` | railway_default |
| `SAGE_SKILL_RUNNER_UP_MIN` | `0.50` | railway_default |
| `SAGE_TRANSLATOR_MODEL` | `openai/gpt-4o-mini` | railway_default |
| `SAGE_VENTING_SUPPRESSION` | `true` | serving_readback |

## Per-fixture outcome distributions

Offer-rate = fraction of samples whose FINAL (request) turn ends with ANY skill offered/active/completed. First-line rate = spec-conformance column: the BOT BEHAVIOUR §1a Tier-1 pair {box_breathing, grounding_5_4_3_2_1} offered, or a pair skill activated via the offer_promoted path; psychoed absorption, other-skill semantic offers, and knowledge-path responses count 0 here even when offer-rate counts them — the offer-rate/first-line DELTA is the DF-1 ordering evidence. Flip-rate = fraction of samples off the modal outcome (mechanism = final-turn intent+path signature; trajectory = full session).

| case | surface | n | offer-rate | first-line rate | mech flip-rate | traj flip-rate | degraded turns | modal mechanism |
|---|---|---|---|---|---|---|---|---|
| EMR-S1-000 | s1_active_skill_absorption | 10 | 0.80 | 0.00 | 0.30 | 0.40 | 0 | `skill_continuation|safety_check>intent_route>skill_executor>freeflow_respond>output_gate` |
| EMR-S2-001 | s2_cold_request | 10 | 0.20 | 0.00 | 0.30 | 0.40 | 0 | `info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate` |
| EMR-S3-002 | s3_over_pending_offer | 10 | 1.00 | 0.00 | 0.00 | 0.30 | 0 | `new_skill|safety_check>intent_route>offer_accepted>skill_select>offer_promoted>skill_executor>freeflow_respond>output_gate` |
| EMR-PARA-001 | paraphrase | 10 | 1.00 | 1.00 | 0.10 | 0.20 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-002 | paraphrase | 10 | 1.00 | 1.00 | 0.10 | 0.30 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-003 | paraphrase | 10 | 1.00 | 0.00 | 0.40 | 0.40 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-004 | paraphrase | 10 | 1.00 | 1.00 | 0.00 | 0.00 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-005 | paraphrase | 10 | 1.00 | 1.00 | 0.10 | 0.10 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-006 | paraphrase | 10 | 1.00 | 0.00 | 0.20 | 0.20 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-007 | paraphrase | 10 | 1.00 | 0.00 | 0.20 | 0.20 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-008 | paraphrase | 10 | 1.00 | 1.00 | 0.10 | 0.30 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-009 | paraphrase | 10 | 1.00 | 0.00 | 0.10 | 0.20 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-010 | paraphrase | 10 | 1.00 | 1.00 | 0.40 | 0.40 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-011 | paraphrase | 10 | 1.00 | 1.00 | 0.00 | 0.00 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-PARA-012 | paraphrase | 10 | 1.00 | 1.00 | 0.10 | 0.20 | 0 | `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate` |
| EMR-CTRL-001 | control | 10 | 1.00 | 0.00 | 0.00 | 0.20 | 0 | `info_request|safety_check>intent_route>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate` |
| EMR-CTRL-002 | control | 10 | 0.00 | 0.00 | 0.20 | 0.20 | 0 | `general_chat|safety_check>intent_route>freeflow_respond>output_gate` |
| EMR-CTRL-003 | control | 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0 | `info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate` |

### EMR-S1-000

- **spec_expectation:** final turn resolves the explicit exercise request: self_help_skill offer of box_breathing or grounding_5_4_3_2_1 (BOT BEHAVIOUR §1a step 4), after the §1a screen; the request must not be absorbed into an active/psychoed flow

- offer-rate: **0.80** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.30 | trajectory flip-rate: 0.40

Mechanism counts (final turn, intent+path signature):

- 7/10 `skill_continuation|safety_check>intent_route>skill_executor>freeflow_respond>output_gate`
- 1/10 `info_request|safety_check>intent_route>offer_ignored>skill_select>knowledge_retrieve>freeflow_respond>output_gate`
- 1/10 `skill_continuation|safety_check>intent_route>skill_executor>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `info_request|safety_check>intent_route>offer_ignored>skill_select>knowledge_retrieve>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 6/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:skill_continuation|safety_check>intent_route>skill_executor>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>directive_posture_set>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied ;; t3:info_request|safety_check>intent_route>offer_ignored>skill_select>knowledge_retrieve>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:skill_continuation|safety_check>intent_route>skill_executor>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>directive_posture_set>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate ;; t3:info_request|safety_check>intent_route>offer_ignored>skill_select>knowledge_retrieve>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:skill_continuation|safety_check>intent_route>skill_executor>freeflow_respond>output_gate`

### EMR-S2-001

- **spec_expectation:** explicit request with no active skill resolves to a first-line offer (box_breathing or grounding_5_4_3_2_1) through the consent gate; must not early-return through info_request -> KB abstain -> freeflow

- offer-rate: **0.20** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.30 | trajectory flip-rate: 0.40

Mechanism counts (final turn, intent+path signature):

- 7/10 `info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate`
- 2/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 6/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate`
- 2/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-S3-002

- **spec_expectation:** request over a pending offer resolves against the pending candidates and the binding table (requested modality in offer -> promote; else first-line re-offer, declined-filtering preserved); must not be classified offer_ignored and released

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.00 | trajectory flip-rate: 0.30

Mechanism counts (final turn, intent+path signature):

- 10/10 `new_skill|safety_check>intent_route>offer_accepted>skill_select>offer_promoted>skill_executor>freeflow_respond>output_gate`

Trajectory frequencies (full session):

- 7/10 `t1:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>offer_accepted>skill_select>offer_promoted>skill_executor>freeflow_respond>output_gate`
- 3/10 `t1:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied ;; t2:new_skill|safety_check>intent_route>offer_accepted>skill_select>offer_promoted>skill_executor>freeflow_respond>output_gate`

### EMR-PARA-001

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.10 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 9/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>question_discipline_applied ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`

### EMR-PARA-002

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.10 | trajectory flip-rate: 0.30

Mechanism counts (final turn, intent+path signature):

- 9/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 7/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>question_discipline_applied ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-PARA-003

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.40 | trajectory flip-rate: 0.40

Mechanism counts (final turn, intent+path signature):

- 6/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 4/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 6/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 4/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-PARA-004

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.00 | trajectory flip-rate: 0.00

Mechanism counts (final turn, intent+path signature):

- 10/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`

Trajectory frequencies (full session):

- 10/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`

### EMR-PARA-005

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.10 | trajectory flip-rate: 0.10

Mechanism counts (final turn, intent+path signature):

- 9/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 9/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-PARA-006

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.20 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 8/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_passthrough`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_passthrough`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-PARA-007

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.20 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 8/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 2/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 2/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-PARA-008

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.10 | trajectory flip-rate: 0.30

Mechanism counts (final turn, intent+path signature):

- 9/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied`

Trajectory frequencies (full session):

- 7/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 2/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied`

### EMR-PARA-009

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.10 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 9/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>question_discipline_applied ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied`

### EMR-PARA-010

- **spec_expectation:** explicit modality request naming breathing -> binding-table candidate honouring the named modality (box_breathing family) through consent gate

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.40 | trajectory flip-rate: 0.40

Mechanism counts (final turn, intent+path signature):

- 6/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 4/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 6/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 4/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-PARA-011

- **spec_expectation:** explicit modality request naming grounding -> binding-table candidate honouring the named modality (grounding_5_4_3_2_1 family) through consent gate

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.00 | trajectory flip-rate: 0.00

Mechanism counts (final turn, intent+path signature):

- 10/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`

Trajectory frequencies (full session):

- 10/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`

### EMR-PARA-012

- **spec_expectation:** explicit modality request -> first-line offer through consent gate (binding table), not freeflow/psychoed-only

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.10 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 9/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-CTRL-001

- **spec_expectation:** curiosity ask is NOT an explicit modality request: psychoeducation/freeflow response acceptable; no forced skill delivery; any future detector must NOT set the flag here

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.00 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 10/10 `info_request|safety_check>intent_route>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_passthrough ;; t2:info_request|safety_check>intent_route>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:info_request|safety_check>intent_route>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate`

### EMR-CTRL-002

- **spec_expectation:** bare affect is general_chat/freeflow exploration first (intent prompt: brief opening disclosure without symptoms/duration/frequency); no skill offer required; any future detector must NOT set the flag here

- offer-rate: **0.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.20 | trajectory flip-rate: 0.20

Mechanism counts (final turn, intent+path signature):

- 8/10 `general_chat|safety_check>intent_route>freeflow_respond>output_gate`
- 2/10 `general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 8/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate`
- 2/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-CTRL-003

- **spec_expectation:** genuine info ask still reaches the info/knowledge path and is answered with the helpline (single-source CRISIS_RESOURCES copy); must NOT be treated as a modality request; positive-path guard for re-plan Phase 2 surface 2

- offer-rate: **0.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **0.00** over n=10
- mechanism flip-rate: 0.00 | trajectory flip-rate: 0.00

Mechanism counts (final turn, intent+path signature):

- 10/10 `info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate`

Trajectory frequencies (full session):

- 10/10 `t1:info_request|safety_check>intent_route>skill_select>knowledge_retrieve>freeflow_respond>output_gate`
