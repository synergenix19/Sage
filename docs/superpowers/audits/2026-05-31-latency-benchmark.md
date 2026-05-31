# Latency Benchmark — SageAI POC

**Date:** 2026-05-31 10:48 UTC  
**Server:** http://localhost:8765  
**Runs per scenario:** 5  
**Measurement:** TTFB = time from POST to first response byte (= total ainvoke time)  
**Note:** Streaming is word-by-word drip removed in 2026-05-28; TTFB ≈ total response time.

---

## Summary Table

| Scenario | Lang | Mean | p50 | p95 | Min | Max | Stdev | Errors |
|---|---|---|---|---|---|---|---|---|
| EN general_chat | EN | 4.8s | 2.96s | 10.96s | 2.82s | 10.96s | 3.5s | 0/5 |
| EN new_skill | EN | 3.56s | 3.36s | 4.79s | 2.99s | 4.79s | 0.71s | 0/5 |
| EN skill_cont | EN | 4.18s | 4.05s | 5.06s | 3.66s | 5.06s | 0.57s | 0/5 |
| EN info_request | EN | 5.15s | 4.06s | 10.05s | 3.58s | 10.05s | 2.75s | 0/5 |
| EN crisis | EN | 1.42s | 1.42s | 1.45s | 1.4s | 1.45s | 0.02s | 0/5 |
| EN scope_refusal | EN | 2.42s | 2.41s | 2.76s | 2.22s | 2.76s | 0.21s | 0/5 |
| EN low_conf | EN | 3.11s | 3.06s | 3.58s | 2.8s | 3.58s | 0.33s | 0/5 |
| EN post_crisis | EN | 3.08s | 3.07s | 3.76s | 2.22s | 3.76s | 0.57s | 0/5 |
| AR general_chat | AR | 4.49s | 4.45s | 4.66s | 4.37s | 4.66s | 0.12s | 0/5 |
| AR new_skill | AR | 6.07s | 6.16s | 6.81s | 5.39s | 6.81s | 0.54s | 0/5 |
| AR crisis | AR | 1.92s | 1.87s | 2.18s | 1.78s | 2.18s | 0.16s | 0/5 |
| AR code-switch | AR | 4.89s | 4.77s | 5.53s | 4.45s | 5.53s | 0.42s | 0/5 |

---

## English vs Arabic Overhead

Arabic adds two LLM translation calls (async_translate_to_english + async_translate_to_arabic).

| | EN freeflow | AR freeflow | AR overhead |
|---|---|---|---|
| Mean | 4.8s | 4.49s | +-0.31s |
| p95 | 10.96s | 4.66s | +-6.3s |

---

## Per-scenario Detail

### EN — general_chat (freeflow, no skill)
_Expects general_chat intent → no skill activation → freeflow path_
- Message: `I've been feeling a bit off lately, not sure what's going on.`

**Stats:** mean=4.8s p50=2.96s p95=10.96s min=2.82s max=10.96s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 10.96s | `safety→intent→freefl→output` | general_chat | — |
| 2 | 4.39s | `safety→intent→freefl→output` | general_chat | — |
| 3 | 2.96s | `safety→intent→freefl→output` | general_chat | — |
| 4 | 2.82s | `safety→intent→freefl→output` | general_chat | — |
| 5 | 2.89s | `safety→intent→freefl→output` | general_chat | — |

### EN — new_skill (skill select + execute)
_Specific somatic symptoms → new_skill → grounding or box_breathing likely_
- Message: `I've been having panic attacks — my heart races and I can't breathe.`

**Stats:** mean=3.56s p50=3.36s p95=4.79s min=2.99s max=4.79s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 3.36s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 2 | 3.40s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 3 | 3.25s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 4 | 4.79s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 5 | 2.99s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |

### EN — skill_continuation (warm turn, no skill_select)
_T2 in skill session — should bypass skill_select and go direct to executor_
- Message: `I can feel my feet on the floor.`
- Context setup turns: 1

**Stats:** mean=4.18s p50=4.05s p95=5.06s min=3.66s max=5.06s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 5.06s | `safety→intent→skill_→freefl→output` | skill_continuation | grounding_5_4_3_2_1 |
| 2 | 3.74s | `safety→intent→skill_→freefl→output` | skill_continuation | grounding_5_4_3_2_1 |
| 3 | 4.38s | `safety→intent→skill_→freefl→output` | skill_continuation | grounding_5_4_3_2_1 |
| 4 | 4.05s | `safety→intent→skill_→freefl→output` | skill_continuation | grounding_5_4_3_2_1 |
| 5 | 3.66s | `safety→intent→skill_→freefl→output` | skill_continuation | grounding_5_4_3_2_1 |

### EN — info_request (knowledge retrieve path)
_info_request → skill_select early-return → knowledge_retrieve → freeflow_
- Message: `What is CBT and how does it work for anxiety?`

**Stats:** mean=5.15s p50=4.06s p95=10.05s min=3.58s max=10.05s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 4.06s | `safety→intent→skill_→knowle→freefl→output` | info_request | — |
| 2 | 4.38s | `safety→intent→skill_→knowle→freefl→output` | info_request | — |
| 3 | 10.05s | `safety→intent→skill_→knowle→freefl→output` | info_request | — |
| 4 | 3.70s | `safety→intent→skill_→knowle→freefl→output` | info_request | — |
| 5 | 3.58s | `safety→intent→skill_→knowle→freefl→output` | info_request | — |

### EN — crisis (safety_check → crisis_response, no LLM response)
_Fastest path: rules-based crisis_response only, no LLM response generation_
- Message: `I don't want to live anymore. I've been thinking about ending my life.`

**Stats:** mean=1.42s p50=1.42s p95=1.45s min=1.4s max=1.45s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 1.45s | `safety→crisis` |  | — |
| 2 | 1.40s | `safety→crisis` |  | — |
| 3 | 1.42s | `safety→crisis` |  | — |
| 4 | 1.43s | `safety→crisis` |  | — |
| 5 | 1.40s | `safety→crisis` |  | — |

### EN — scope_refusal (output_gate, no LLM)
_scope_refusal → output_gate only, deterministic response_
- Message: `Can you diagnose me with depression and prescribe antidepressants?`

**Stats:** mean=2.42s p50=2.41s p95=2.76s min=2.22s max=2.76s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 2.30s | `safety→intent→output` | scope_refusal | — |
| 2 | 2.43s | `safety→intent→output` | scope_refusal | — |
| 3 | 2.41s | `safety→intent→output` | scope_refusal | — |
| 4 | 2.76s | `safety→intent→output` | scope_refusal | — |
| 5 | 2.22s | `safety→intent→output` | scope_refusal | — |

### EN — low_confidence (clarification request)
_Single-word ambiguous input → low confidence → clarification_
- Message: `uhmm`

**Stats:** mean=3.11s p50=3.06s p95=3.58s min=2.8s max=3.58s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 3.29s | `safety→intent→freefl→output` | general_chat | — |
| 2 | 3.06s | `safety→intent→freefl→output` | general_chat | — |
| 3 | 3.58s | `safety→intent→freefl→output` | general_chat | — |
| 4 | 2.81s | `safety→intent→freefl→output` | general_chat | — |
| 5 | 2.80s | `safety→intent→freefl→output` | general_chat | — |

### EN — post_crisis monitoring turn (S7 fires)
_T2 after crisis: S7 fires in safety_check + post_crisis_check_in auto-select_
- Message: `I feel a little better now, thank you.`
- Context setup turns: 1

**Stats:** mean=3.08s p50=3.07s p95=3.76s min=2.22s max=3.76s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 3.76s | `safety→intent→skill_→skill_→freefl→output` | skill_continuation | post_crisis_check_in |
| 2 | 3.38s | `safety→intent→skill_→skill_→freefl→output` | exit_skill | post_crisis_check_in |
| 3 | 2.98s | `safety→intent→skill_→skill_→freefl→output` | general_chat | post_crisis_check_in |
| 4 | 3.07s | `safety→intent→crisis` | crisis | — |
| 5 | 2.22s | `safety→intent→crisis` | crisis | — |

### AR — general_chat (freeflow + translate in + translate out)
_+1 LLM call vs EN: async_translate_to_english (in) + async_translate_to_arabic (out)_
- Message: `أنا حاسس بضغط من الشغل`

**Stats:** mean=4.49s p50=4.45s p95=4.66s min=4.37s max=4.66s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 4.66s | `safety→intent→freefl→output` | general_chat | — |
| 2 | 4.37s | `safety→intent→freefl→output` | general_chat | — |
| 3 | 4.54s | `safety→intent→freefl→output` | general_chat | — |
| 4 | 4.45s | `safety→intent→freefl→output` | general_chat | — |
| 5 | 4.43s | `safety→intent→freefl→output` | general_chat | — |

### AR — new_skill (translate + skill activate)
_Arabic somatic symptoms → skill activation → output translated to Khaleeji_
- Message: `قلبي يدق بسرعة وما أقدر أتنفس بشكل صحيح`

**Stats:** mean=6.07s p50=6.16s p95=6.81s min=5.39s max=6.81s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 6.81s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 2 | 6.26s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 3 | 5.73s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 4 | 5.39s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |
| 5 | 6.16s | `safety→intent→skill_→skill_→freefl→output` | new_skill | grounding_5_4_3_2_1 |

### AR — crisis (translate in + rules-based response in AR)
_Arabic crisis: translate in → S1/S3 detect → crisis_response in Arabic (CC-AR-001)_
- Message: `أبي أموت، ما أقدر أكمل`

**Stats:** mean=1.92s p50=1.87s p95=2.18s min=1.78s max=2.18s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 1.94s | `safety→crisis` |  | — |
| 2 | 1.78s | `safety→crisis` |  | — |
| 3 | 2.18s | `safety→crisis` |  | — |
| 4 | 1.87s | `safety→crisis` |  | — |
| 5 | 1.84s | `safety→crisis` |  | — |

### AR — code-switching (EN+AR mixed)
_Mixed EN+AR → code_switching=True → CU-CS-001 fires → mirror bilingual register_
- Message: `I'm really تعبان these days, لا أعرف what to do`

**Stats:** mean=4.89s p50=4.77s p95=5.53s min=4.45s max=5.53s

| Run | TTFB | Path | Intent | Skill |
|---|---|---|---|---|
| 1 | 5.53s | `safety→intent→freefl→output` | general_chat | — |
| 2 | 4.65s | `safety→intent→freefl→output` | general_chat | — |
| 3 | 4.45s | `safety→intent→freefl→output` | general_chat | — |
| 4 | 5.02s | `safety→intent→freefl→output` | general_chat | — |
| 5 | 4.77s | `safety→intent→freefl→output` | general_chat | — |

---

## Known Latency Drivers

| Driver | Scope | Estimated cost |
|---|---|---|
| LLM response (intent_route) | Every turn | 400–800ms (gpt-4o-mini) |
| LLM response (freeflow_respond) | Non-crisis turns | 1–3s (gpt-4o) |
| S3 BGE-M3 semantic check | Every turn | 200–500ms (warm model) |
| async_translate_to_english | Arabic input | ~800ms (gpt-4o-mini) |
| async_translate_to_arabic | Arabic output | ~800ms (gpt-4o-mini) |
| LangGraph AsyncPostgresSaver | Every turn (with DATABASE_URL) | 400–800ms |
| Session summary (turn % 10) | Turn 10, 20, 30... | +500ms–1.5s |
| LLM criteria eval (4 skills only) | Certain skill steps | +400ms |
| LLM resistance scoring | Skill turns with resistance rules | +400ms |
| Prior context pgvector retrieval | Every turn with user_id | ~100–300ms |

**Option B (real streaming):** Replacing `graph.ainvoke()` with `graph.astream(stream_mode=['messages','values'])` 
would surface first LLM tokens as generated, reducing TTFB to ~400ms (first intent_route token). 
This is the only path to the v7 KPI of <3s p95. Deferred post-POC.