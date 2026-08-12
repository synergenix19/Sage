# EMR Phase-0 baseline — explicit-modality-request handling (distributional, pre-fix)

<!-- instrument-parity header block (signed standing rule 2026-07-28) — template artifact -->

## Provenance (instrument-parity header block)

- **Instrument:** graph_evidence.py FULL-GRAPH app.ainvoke, N independent session threads per fixture; flags derived from /health/version serving readback (refuse-on-gap, refuse-on-deploy-window); signed instrument-parity standing rule 2026-07-28
- **Generated at:** 2026-08-12T08:22:55+00:00
- **Serving readback:** https://sage-api-production-3328.up.railway.app /health/version
- **Build SHA (from readback):** `07056b3a3a6af8b52cb5cae6269ccf28bc7df941` (source: SAGE_BUILD_SHA)
- **Local tree SHA (code measured):** `b69f5b13565e344835088e6c48502211b9eaf0c5`
- **Classifier model:** `openai/gpt-4o-mini`
- **OpenRouter provider pin:** `openai`
- **Requested classifier seed:** `20260728`
- **Seed-honor signal (system_fingerprint):** `fingerprint_stable` — distinct: ['fp_c400bf5046']
- **N per fixture:** 10
- **Degraded turns (static-fallback signature general_chat@0.5):** 0
- **DB pool (KB-path serving parity):** AVAILABLE
- **Railway (desired) available:** True | **deploy-window checked:** True
- **Parity note:** readback coverage hole (1 var(s) asserted via railway, not the serving readback): SAGE_MODALITY_REQUEST_ROUTING — widen /health/version *_raw_env to close (standing-rule 3 pattern).
- **Parity note:** DELIBERATE FLAG OVERRIDE (fix-arm measurement): SAGE_MODALITY_REQUEST_ROUTING='true' — serving carries a different value; this run is a COUNTERFACTUAL arm, not a serving-parity baseline. Cite only against its paired baseline.
- **Parity note:** NOTE: LOCAL tree b69f5b13565e != SERVING build 07056b3a3a6a — flags are serving-derived but the code under measurement is the local tree; cite accordingly.
- **Parity note:** quiescence attestation: cause=item1-condition-a; deploy cycle spanned: deployment id changed 543fd26a-7d5c-424b-a1b4-922108d758c1 -> 90cd7f83-d9c1-4c59-85d8-2601db2fd444 between clean checks 2026-07-29T19:30:51+00:00 / 2026-07-29T19:51:35+00:00
- **Parity note:** quiescence refusal log: empty (no refusals recorded)

### Resolved flag set (full, with coverage source)

| var | effective value | coverage |
|---|---|---|
| `SAGE_AUDIT_CLASSIFIER_PROVENANCE` | `true` | serving_readback |
| `SAGE_CARDIAC_ESCALATION` | `true` | serving_readback |
| `SAGE_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | serving_readback |
| `SAGE_CLASSIFIER_SEED` | `20260728` | serving_readback |
| `SAGE_CONSULT_SOURCES` | `true` | serving_readback |
| `SAGE_COSINE_ABSTAIN_THRESHOLD` | `0.42` | serving_readback |
| `SAGE_CRISIS_TIERING` | `None` | serving_readback |
| `SAGE_D1_SCREEN` | `true` | serving_readback |
| `SAGE_D1_SCREEN_SHADOW` | `true` | serving_readback |
| `SAGE_D5_ACUITY_FLOOR` | `8` | serving_readback |
| `SAGE_D5_ACUITY_GATE` | `false` | serving_readback |
| `SAGE_DEREALIZATION_DETECTION` | `true` | serving_readback |
| `SAGE_FALLBACK_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | serving_readback |
| `SAGE_FALLBACK_RESPONDER_MODEL` | `openai/gpt-4o` | serving_readback |
| `SAGE_GRIEF_DEFERENCE` | `true` | serving_readback |
| `SAGE_HIGH_RISK_DETECTION` | `true` | serving_readback |
| `SAGE_HIGH_RISK_TERMINAL` | `None` | serving_readback |
| `SAGE_HR_NEUTRALITY_GATE` | `true` | serving_readback |
| `SAGE_INFO_REQUEST_CONSULT` | `true` | serving_readback |
| `SAGE_IPV_PREEMPTION` | `false` | serving_readback |
| `SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD` | `0.015` | serving_readback |
| `SAGE_MEDICAL_REDFLAG_GUARD` | `true` | serving_readback |
| `SAGE_MEDICAL_REFERRAL_TEXT` | `The symptoms you're describing can be signs of a medical emergency. ` | serving_readback |
| `SAGE_MODALITY_REQUEST_ROUTING` | `true` | deliberate_override |
| `SAGE_NATIVE_ARABIC_SHADOW` | `false` | serving_readback |
| `SAGE_OPENROUTER_PROVIDER_PIN` | `openai` | serving_readback |
| `SAGE_PANIC_GROUNDING_OVERRIDE` | `true` | serving_readback |
| `SAGE_PSYCHOED_CATEGORIES` | `` | serving_readback |
| `SAGE_PSYCHOED_PATHWAYS` | `None` | serving_readback |
| `SAGE_RESISTANCE_MODEL` | `None` | serving_readback |
| `SAGE_RESPONDER_MODEL` | `openai/gpt-4o` | serving_readback |
| `SAGE_ROUTE_PRECEDENCE` | `true` | serving_readback |
| `SAGE_SKILL_OFFER_COOLDOWN_ENABLED` | `true` | serving_readback |
| `SAGE_SKILL_OFFER_COOLDOWN_TURNS` | `2` | serving_readback |
| `SAGE_SKILL_RUNNER_UP_MARGIN` | `0.05` | serving_readback |
| `SAGE_SKILL_RUNNER_UP_MIN` | `0.50` | serving_readback |
| `SAGE_TRANSLATOR_MODEL` | `openai/gpt-4o-mini` | serving_readback |
| `SAGE_VENTING_SUPPRESSION` | `true` | serving_readback |

## Per-fixture outcome distributions

Offer-rate = fraction of samples whose FINAL (request) turn ends with ANY skill offered/active/completed. First-line rate = spec-conformance column: the BOT BEHAVIOUR §1a Tier-1 pair {box_breathing, grounding_5_4_3_2_1} offered, or a pair skill activated via the offer_promoted path; psychoed absorption, other-skill semantic offers, and knowledge-path responses count 0 here even when offer-rate counts them — the offer-rate/first-line DELTA is the DF-1 ordering evidence. Flip-rate = fraction of samples off the modal outcome (mechanism = final-turn intent+path signature; trajectory = full session).

| case | surface | n | offer-rate | first-line rate | mech flip-rate | traj flip-rate | degraded turns | modal mechanism |
|---|---|---|---|---|---|---|---|---|
| EMR-SC-001 | s2_cold_request_screen_completed | 10 | 1.00 | 1.00 | 0.50 | 0.50 | 0 | `general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten` |
| EMR-SC-002 | s1_absorption_screen_completed | 10 | 1.00 | 1.00 | 0.50 | 0.60 | 0 | `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate` |
| EMR-SC-003 | chronic_screen_completed_referral_alongside | 10 | 1.00 | 1.00 | 0.30 | 0.30 | 0 | `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate` |

### EMR-SC-001

- **spec_expectation:** turn 1 serves the screen question (duration); turn 2 supplies onset+duration (acute) -> cleared -> first-line pair offered (box_breathing, grounding_5_4_3_2_1)

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.50 | trajectory flip-rate: 0.50

Mechanism counts (final turn, intent+path signature):

- 5/10 `general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 4/10 `general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten>question_discipline_applied`

Trajectory frequencies (full session):

- 5/10 `t1:info_request|safety_check>intent_route>modality_request_detected>skill_select>modality_request_screen_pending>screen_response ;; t2:general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 4/10 `t1:info_request|safety_check>intent_route>modality_request_detected>skill_select>modality_request_screen_pending>screen_response ;; t2:general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:info_request|safety_check>intent_route>modality_request_detected>skill_select>modality_request_screen_pending>screen_response ;; t2:general_chat|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten>question_discipline_applied`

### EMR-SC-002

- **spec_expectation:** turn 3 exits psychoed (rehand) and serves the screen; turn 4 supplies onset+duration (acute) -> cleared -> first-line pair offered

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.50 | trajectory flip-rate: 0.60

Mechanism counts (final turn, intent+path signature):

- 5/10 `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate`
- 5/10 `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

Trajectory frequencies (full session):

- 4/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:skill_continuation|safety_check>intent_route>modality_request_detected>skill_executor>modality_request_routed:executor>skill_select>modality_request_screen_pending>screen_response ;; t4:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate`
- 2/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:skill_continuation|safety_check>intent_route>modality_request_detected>skill_executor>modality_request_routed:executor>skill_select>modality_request_screen_pending>screen_response ;; t4:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 2/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:new_skill|safety_check>intent_route>modality_request_detected>skill_executor>modality_request_routed:executor>skill_select>modality_request_screen_pending>screen_response ;; t4:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t2:info_request|safety_check>intent_route>directive_posture_set>skill_select>knowledge_retrieve_cards>skill_executor>freeflow_respond>output_gate ;; t3:skill_continuation|safety_check>intent_route>modality_request_detected>skill_executor>modality_request_routed:executor>skill_select>modality_request_screen_pending>screen_response ;; t4:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate`
- 1/10 `t1:general_chat|safety_check>intent_route>freeflow_respond>output_gate ;; t2:new_skill|safety_check>intent_route>directive_posture_set>skill_select>skill_matching_rule:default_offer>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten ;; t3:info_request|safety_check>intent_route>modality_request_detected>modality_request_routed:offer_reply>offer_released_modality_request>skill_select>modality_request_screen_pending>screen_response ;; t4:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`

### EMR-SC-003

- **spec_expectation:** turn 1 screens; turn 2 supplies chronic duration + onset -> cleared WITH referral_alongside -> first-line offer with modality_request_referral_context marker

- offer-rate: **1.00** | first-line offer-rate (§1a Tier-1 pair, spec-conformant): **1.00** over n=10
- mechanism flip-rate: 0.30 | trajectory flip-rate: 0.30

Mechanism counts (final turn, intent+path signature):

- 7/10 `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate`
- 2/10 `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied`

Trajectory frequencies (full session):

- 7/10 `t1:new_skill|safety_check>intent_route>modality_request_detected>skill_select>modality_request_screen_pending>screen_response ;; t2:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate`
- 2/10 `t1:new_skill|safety_check>intent_route>modality_request_detected>skill_select>modality_request_screen_pending>screen_response ;; t2:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate>output_gate_opener_rewritten`
- 1/10 `t1:new_skill|safety_check>intent_route>modality_request_detected>skill_select>modality_request_screen_pending>screen_response ;; t2:new_skill|safety_check>intent_route>skill_select>modality_request_routed:select>modality_request_referral_context>skill_offer_made>freeflow_respond>output_gate>question_discipline_applied`
