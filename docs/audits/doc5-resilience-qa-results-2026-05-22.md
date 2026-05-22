# Doc 5: LLM Resilience Layer — QA & Validation Results

**Date:** 2026-05-22  
**Auditor:** Claude Code (automated)  
**Branch:** master  
**Baseline:** 723 tests (Doc 4 final state)  
**Post-Doc 5 actual:** 768 tests

---

## Summary

| Phase | Checks | Status |
|---|---|---|
| 1. Structural | 9 checks | ✅ All PASS |
| 2. Functional | Full suite + per-file regressions | ✅ All PASS |
| 3. Resilience mechanisms | 6 circuit breaker + 12 error classification + 6 invoke + 3 stream + 5 fallback | ✅ All PASS |
| 4. Node integration | 5 nodes × async + resilience wiring | ✅ All PASS |
| 5. Provider independence | 3 checks | ✅ All PASS |
| 6. Observability | 4 logging/latency checks | ✅ All PASS |
| 7. Safety invariant | 3 checks (crisis detection without LLM) | ✅ **CRITICAL PASS** |
| 8. Token usage consumers | 2 checks | ✅ All PASS |
| 9. E2E graph routing | 6 categories | ✅ All PASS |
| 10. Configuration | 2 checks | ✅ All PASS |
| 11. Graceful degradation | 2 end-to-end scenarios | ✅ All PASS (1 audit script defect noted) |
| 12. Tech debt | 8 items registered | ℹ️ No action required |

**Overall verdict: SHIP-READY.** No stop-ship issues found.

---

## Phase 1 — Structural Verification

### 1.1 New File Existence

```
PASS: src/sage_poc/resilience/__init__.py
PASS: src/sage_poc/resilience/fallbacks.json
PASS: tests/test_resilience.py
```

**Result: 3/3 PASS**

### 1.2 Fallback JSON Schema Validation

```
PASS: 6 fallback entries validated, 0 missing
```

All 6 required pairs present: `(freeflow_respond, en/ar)`, `(low_confidence_respond, en/ar)`, `(default, en/ar)`. No em dashes, no malformed entries, all responses > 5 characters.

**Result: PASS**

### 1.3 No Bare LLM Calls in Node Files (AC1 — CRITICAL)

```
(no output — zero bare .ainvoke/.astream calls found)
```

Every LLM call goes through `resilient_invoke` or `resilient_stream`.

**Result: PASS — AC1 satisfied**

### 1.4 All Converted Nodes Are Async

```
PASS: intent_route_node is async
PASS: skill_select_node is async
PASS: output_gate_node is async
PASS: freeflow_respond_node is async
PASS: low_confidence_respond_node is async
```

**Result: 5/5 PASS**

### 1.5 safety_check_node Is Sync with No Resilience Dependency

```
PASS: safety_check has no resilience dependency
PASS: safety_check_node is sync (deterministic, no LLM)
```

**Result: PASS**

### 1.6 Fallback LLM Factory Functions Exist

```
PASS: Fallback factories exist
  FALLBACK_RESPONDER_MODEL = openai/gpt-4o
  FALLBACK_CLASSIFIER_MODEL = openai/gpt-4o-mini
```

**Result: PASS**

### 1.7 Async Translation Functions Exist

```
PASS: async_translate_to_arabic and async_translate_to_english exist and are async
```

**Result: PASS**

### 1.8 BGE-M3 Warmup in server.py

```
19: def _warmup_bge_m3() -> None:
20:     from sage_poc.nodes.skill_select import _ensure_semantic_ready
21:     _ensure_semantic_ready()
25: async def lifespan(app: FastAPI):
27:     await asyncio.to_thread(_warmup_bge_m3)
28:     logging.getLogger(__name__).info("[sage/startup] BGE-M3 warmup complete")
36: app = FastAPI(title="SageAI API", lifespan=lifespan)

PASS: lifespan defined and referenced (2 occurrences)
```

**Result: PASS**

### 1.9 Backward Compatibility — Re-exports

```
PASS: freeflow_respond re-exports preserved (PERSONA, compose_prompt, _sanitize_assistant_turn)
```

**Result: PASS**

---

## Phase 2 — Functional Verification

### 2.1 Full Test Suite

```
768 passed, 15 warnings in 251.43s
```

**Result: PASS — 768 ≥ 723 baseline. Zero failures. +45 new tests from Doc 5.**

### 2.2 Resilience-Specific Tests

```
40 passed, 13 warnings in 2.39s
```

**Result: PASS — 40 tests, all green**

### 2.3 Test Count Per Category

| Category | Found | Required | Status |
|---|---|---|---|
| Total resilience tests | 40 | ≥35 | ✅ |
| fallback (JSON + loader) | 15 | ≥6 | ✅ |
| circuit breaker | 7 | ≥6 | ✅ |
| resilient_invoke | 7 | ≥6 | ✅ |
| resilient_stream | 3 | ≥3 | ✅ |
| skill_select | 3 | ≥3 | ✅ |
| intent_route | 3 | ≥3 | ✅ |
| low_confidence | 2 | ≥2 | ✅ |
| freeflow_respond | 2 | ≥2 | ✅ |
| output_gate | 3 | ≥3 | ✅ |
| translate | 4 | ≥3 | ✅ |

**Result: All categories at or above minimum**

### 2.4 Previously Passing Test Files — No Regressions

| File | Result |
|---|---|
| tests/test_nodes.py | 165 passed |
| tests/test_freeflow_respond.py | 11 passed |
| tests/test_rules_integration.py | 53 passed |
| tests/test_prompts_composer.py | 50 passed |
| tests/test_graph.py | 74 passed |

**Result: PASS — zero regressions across all high-risk files**

---

## Phase 3 — Resilience Mechanism Correctness

### 3.1 Fallback Response Loader

```
PASS: freeflow_respond/en = "I'm here with you. I need a brief moment to collect my thoug..."
PASS: freeflow_respond/ar = "أنا معاك. أحتاج لحظة أجمع أفكاري، تقدر تعطيني شوي وقت؟ اللي ..."
PASS: Unknown node/en falls back to default: "I'm here with you. Please give me just a moment...."
PASS: Unknown node/ar falls back to default: "أنا معاك. أعطني لحظة من فضلك...."
PASS: Unknown node/fr falls back to default/en: "I'm here with you. Please give me just a moment...."
```

4-tier lookup chain confirmed: exact → node/en → default/lang → default/en.

**Result: 5/5 PASS**

### 3.2 Circuit Breaker State Machine

```
PASS: Circuit starts closed
PASS: 4 failures does not trip
PASS: 5 failures trips circuit
PASS: Success resets circuit
PASS: Auto-reset after 60.0s cooldown
PASS: Circuit breakers are independent per endpoint
```

**Result: 6/6 PASS**

### 3.3 Error Classification

| Error | Retryable | Result |
|---|---|---|
| asyncio.TimeoutError | Yes | ✅ PASS |
| TimeoutError (builtin) | Yes | ✅ PASS |
| OSError | Yes | ✅ PASS |
| HTTP 429 | Yes | ✅ PASS |
| HTTP 502 | Yes | ✅ PASS |
| HTTP 503 | Yes | ✅ PASS |
| HTTP 504 | Yes | ✅ PASS |
| HTTP 400 | No | ✅ PASS |
| HTTP 401 | No | ✅ PASS |
| HTTP 404 | No | ✅ PASS |
| ValueError | No | ✅ PASS |
| KeyError | No | ✅ PASS |

Protocol-based classification confirmed — no provider-specific error types.

**Result: 12/12 PASS**

### 3.4–3.9 resilient_invoke — Individual Tests

```
test_resilient_invoke_success                                   PASSED
test_resilient_invoke_timeout_returns_fallback                  PASSED
test_resilient_invoke_retries_then_succeeds                     PASSED
test_resilient_invoke_non_retryable_skips_retries               PASSED
test_resilient_invoke_circuit_open_skips_llm                    PASSED
test_resilient_invoke_uses_fallback_llm_after_all_retries       PASSED
6 passed
```

**Result: 6/6 PASS**

### 3.10–3.12 resilient_stream — Individual Tests

```
test_resilient_stream_success                                           PASSED
test_resilient_stream_timeout_before_first_chunk_yields_fallback        PASSED
test_resilient_stream_non_retryable_yields_fallback                     PASSED
3 passed
```

**Result: 3/3 PASS**

---

## Phase 4 — Node Integration Verification

### 4.1 intent_route — Resilience Wired

```
test_intent_route_is_async                          PASSED
test_intent_route_fallback_routes_to_general_chat   PASSED
test_intent_route_parses_valid_json_response        PASSED
3 passed
```

**Result: PASS**

### 4.2 intent_route — Fallback Produces Valid Routing

```
PASS: Fallback text (non-JSON) routes safely to general_chat with default values
  primary_intent = general_chat
  intent_confidence = 0.5
  emotional_intensity = 5 (default)
```

When `resilient_invoke` returns warm fallback text (non-JSON), the node correctly defaults to `general_chat` with safe numeric defaults. No crash, no invalid routing.

**Result: PASS — most important intent_route resilience check**

### 4.3 skill_select — Embedding Timeout

```
test_skill_select_node_is_async                                     PASSED
test_skill_select_embedding_timeout_falls_to_freeflow               PASSED
test_skill_select_keyword_tier_unaffected_by_timeout_patch          PASSED
3 passed
```

**Result: PASS**

### 4.4 skill_select — Keyword Matching Independent of Embedding

```
PASS: Keyword matching works even when embedding times out
  Message: "I can't sleep at night" → skill: sleep_hygiene (via keyword tier)
  Embedding timeout: irrelevant — keyword fires first
```

**Result: PASS**

### 4.5 low_confidence_respond — Resilience Wired

```
test_low_confidence_respond_collects_stream         PASSED
test_low_confidence_respond_fallback_text_returned  PASSED
2 passed
```

**Result: PASS**

### 4.6 freeflow_respond — Resilience Wired

```
test_freeflow_respond_calls_resilient_invoke            PASSED
test_freeflow_respond_fallback_returned_on_llm_failure  PASSED
2 passed
```

**Result: PASS**

### 4.7 output_gate — Async Translation Wired

```
test_output_gate_is_async               PASSED
test_output_gate_arabic_uses_async_translate    PASSED
test_output_gate_english_no_translation         PASSED
3 passed
```

**Result: PASS**

### 4.8 Async Translation — Timeout Returns Original

```
test_async_translate_to_arabic_success                  PASSED
test_async_translate_to_arabic_timeout_returns_original PASSED
test_async_translate_to_english_timeout_returns_original PASSED
(+ 1 additional translate test)
4 passed
```

**Result: PASS**

---

## Phase 5 — Provider Independence Verification

### 5.1 Resilience Wrapper Accepts Any LLM Client

```
PASS: resilient_invoke works with arbitrary LLM client (provider-independent)
  Tested with fake_llm (model='custom/falcon-34b', base='https://falcon.local')
```

**Result: PASS**

### 5.2 No Provider-Specific Imports in Resilience Module

```
(no output)
PASS: No provider-specific imports
```

The resilience module imports only `httpx` (for HTTP status code classification), `asyncio`, `json`, `logging`, `random`, `time`, and `pathlib`.

**Result: PASS**

### 5.3 Error Classification Uses No Provider-Specific Error Types

```
PASS: Error classification is protocol-based only
```

**Result: PASS**

---

## Phase 6 — Observability and Logging Verification

### 6.1 Structured Log Events

```
Total logger calls: 14 (≥8 required ✅)

Events present:
  "circuit_breaker_reset"
  "circuit_breaker_short_circuit"
  "circuit_breaker_tripped"
  "llm_call"
  "llm_call_failed"
  "llm_call_retrying"
  "llm_invoke_fallback_failed"
  "llm_stream_failed"
  "llm_stream_fallback_failed"
  "llm_stream_retrying"
```

**Note:** `embedding_timeout` event is logged in `skill_select.py` (not in resilience `__init__.py`). All other expected events present in resilience module.

**Result: PASS — 10 distinct events, 14 logger calls**

### 6.2 Latency Tracking

```
166: start = time.monotonic()
188:     latency_ms = int((time.monotonic() - start) * 1000)
258: start = time.monotonic()
277:     latency_ms = int((time.monotonic() - start) * 1000)

PASS: Latency tracked (6 occurrences)
```

**Result: PASS**

### 6.3 Fallback Usage Logged and Trackable

```
3 occurrences of "fallback_used" in structured log output
PASS: Fallback usage logged in at least 2 events
```

**Result: PASS**

### 6.4 Embedding Timeout Logged

```
100: '{"event": "embedding_timeout", "skill_select_tier": "keyword_only", ...'
109: "embedding_timeout": True,

PASS: Embedding timeout logged (2 occurrences)
```

**Result: PASS**

---

## Phase 7 — Safety Invariant Verification (CRITICAL)

### 7.1 Crisis Detection Works During Total LLM Outage

```
PASS: Crisis detected with flags ['si_explicit'] — no LLM needed
  Input: "I want to kill myself"
  is_safe: False
  crisis_flags: ['si_explicit']
```

**Result: ✅ CRITICAL PASS — crisis detection is fully deterministic and LLM-independent**

### 7.2 Clinical Flags Work During Total LLM Outage

```
PASS: Clinical flag substance_use detected — no LLM needed
  Input: "I have been drinking a lot lately"
  clinical_flags: ['substance_use']
```

**Result: PASS**

### 7.3 safety_check_node Has No LLM Dependency

```
(no output)
PASS: safety_check has zero LLM coupling
```

No `resilience`, `resilient_invoke`, `resilient_stream`, `ainvoke`, `astream`, `get_responder`, or `get_classifier` references.

**Result: PASS**

---

## Phase 8 — Token Usage Consumer Verification

### 8.1 server.py Handles Empty token_usage

```
154:    "token_usage": {},          ← initial state default
214:    "X-Sage-Token-Usage": json.dumps(result.get("token_usage") or {})   ← safe consumer

PASS: Empty token_usage serializes safely to: {}
```

`freeflow_respond` returns `token_usage: {}`. Server uses `or {}` guard — safe for all paths.

**Result: PASS**

### 8.2 Frontend Token Usage Consumers

```
(no output — no frontend consumers found in ../cdaps/web/)
```

No frontend code consumes `token_usage` sub-fields. Safe.

**Result: PASS — no consumers to break**

---

## Phase 9 — E2E Graph Routing Verification

### 9.1 Full Graph Tests

```
tests/test_graph.py: 74 passed in 216.36s
```

All live API tests pass with real OpenRouter calls.

**Result: PASS**

### 9.2 Crisis Routing End-to-End

```
test_crisis_response_en_no_em_dash              PASSED
test_crisis_response_ar_no_em_dash              PASSED
test_intent_route_panic_somatic_returns_new_skill_not_crisis   PASSED
test_s7_not_called_when_crisis_state_is_none    PASSED
test_s7_called_when_crisis_state_is_monitoring  PASSED
test_safety_check_returns_crisis_state_unchanged PASSED
20 passed (crisis-related)
```

**Result: PASS**

### 9.3 Skill Routing End-to-End

```
test_sleep_hygiene_skill_schema_is_valid                PASSED
test_grounding_skill_advances_through_all_5_steps       PASSED
test_intent_system_requires_specific_symptoms_for_new_skill     PASSED
test_intent_route_specific_symptom_returns_new_skill    PASSED
test_intent_route_blended_specific_plus_affect_returns_new_skill PASSED
test_intent_route_panic_somatic_returns_new_skill_not_crisis     PASSED
18 passed (skill-related)
```

**Result: PASS**

### 9.4 Clinical Flag Routing

```
test_clinical_flag_substance_use        PASSED
test_clinical_flag_trauma               PASSED
test_clinical_flag_medication           PASSED
test_no_clinical_flags_for_general_message      PASSED
test_compose_prompt_clinical_flag_injects_adaptation    PASSED
5 passed
```

**Result: PASS**

### 9.5 Rules Service Integration

```
53 passed in 5.39s
```

**Result: PASS**

### 9.6 Prompt Template System

```
78 passed (test_prompts_composer + test_prompts_loader + test_prompts_tokens)
```

**Result: PASS**

---

## Phase 10 — Configuration Verification

### 10.1 All Resilience Constants Match Plan Spec

```
LLM_TIMEOUT_SECONDS = 30.0       ✅
LLM_MAX_RETRIES = 2               ✅
LLM_BACKOFF_BASE = 1.0            ✅
LLM_BACKOFF_MAX = 8.0             ✅
EMBEDDING_TIMEOUT_SECONDS = 10.0  ✅
CIRCUIT_BREAKER_THRESHOLD = 5     ✅
CIRCUIT_BREAKER_RESET_SECONDS = 60.0  ✅

PASS: All constants match expected defaults
```

**Result: PASS**

### 10.2 Fallback Models Are Env-Var Configurable

```
12: FALLBACK_RESPONDER_MODEL = os.getenv("SAGE_FALLBACK_RESPONDER_MODEL", "openai/gpt-4o")
13: FALLBACK_CLASSIFIER_MODEL = os.getenv("SAGE_FALLBACK_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
```

Both use `os.getenv()` with sensible defaults.

**Result: PASS**

---

## Phase 11 — Graceful Degradation Scenario Tests

### 11.1 Total LLM Outage Scenario

```
PASS: Step 1 — Safety check works without LLM
PASS: Step 2 — Intent route degrades to general_chat
PASS: Step 3 — Freeflow returns warm fallback text

PASS: Total LLM outage scenario — system degrades gracefully:
  Safety: deterministic (works)
  Intent: defaults to general_chat (works)
  Response: warm fallback text (works)
  User experience: sees a warm holding message, not an error
```

**Result: PASS — all 3 degradation steps validated**

### 11.2 Embedding-Only Outage Scenario

**Audit script defect noted:** The original audit message `"My mind keeps spiraling with negative thoughts"` keyword-matches `cbt_thought_record` (keyword tier fires before embedding tier is reached). This is correct implementation behavior — keyword matching is intentionally prioritized over semantic matching for speed and reliability.

Test was re-run with a non-keyword message to validate the embedding timeout path:

```
Input: "Everything just feels so heavy and I do not know why"
  → keyword tier: no match
  → semantic tier: asyncio.wait_for raises TimeoutError
  → result: active_skill_id=None, embedding_timeout=True

PASS: Embedding timeout — falls through to freeflow, no skill activated
  User experience: gets freeflow response instead of skill-guided response
  Safety: unaffected (safety_check ran before skill_select)
```

**Result: PASS — embedding timeout path confirmed working. Audit script defect does not indicate an implementation bug.**

---

## Phase 12 — Tech Debt Register

| # | Item | Severity | Notes |
|---|---|---|---|
| TD-1 | Arabic fallback responses are in MSA, not Khaleeji dialect | MEDIUM | Flag for clinician review before launch; JSON editable without code changes |
| TD-2 | `token_usage` returns `{}` — no per-call token tracking | LOW | Deliberate POC trade-off; full tracking requires accessing response object fields |
| TD-3 | Circuit breaker state is in-process dict — lost on restart | LOW | Acceptable for single-process POC; Full Build uses Redis or equivalent |
| TD-4 | Circuit breaker has no HALF-OPEN state (simplified counter) | LOW | Full Build refinement |
| TD-5 | Fallback model uses same OpenRouter base URL — not true provider diversity | MEDIUM | For real resilience, fallback should use a different provider/endpoint entirely |
| TD-6 | No load testing to validate circuit breaker thresholds | LOW | Thresholds are configurable; tune based on production traffic |
| TD-7 | `resilient_stream` first-chunk timeout could miss slow-but-producing streams | LOW | Edge case; first token arriving means stream is alive |
| TD-8 | Backoff jitter uses `random.uniform` (not cryptographically secure) | LOW | Jitter is for timing, not security; acceptable |

---

## Execution Summary

| Phase | Checks | Stop-ship? | Result |
|---|---|---|---|
| 1. Structural | 9 | YES | ✅ All PASS |
| 2. Functional | 768 total tests + regression files | YES | ✅ All PASS |
| 3. Resilience mechanisms | 32 checks | YES | ✅ All PASS |
| 4. Node integration | 16 node tests + 2 functional | YES | ✅ All PASS |
| 5. Provider independence | 3 checks | YES | ✅ All PASS |
| 6. Observability | 4 checks | YES for presence | ✅ All PASS |
| 7. Safety invariant | 3 checks | **CRITICAL** | ✅ **All PASS** |
| 8. Token usage consumers | 2 checks | YES if consumers break | ✅ All PASS |
| 9. E2E graph routing | 6 categories | YES | ✅ All PASS |
| 10. Configuration | 2 checks | YES | ✅ All PASS |
| 11. Graceful degradation | 2 scenarios | YES | ✅ All PASS |
| 12. Tech debt | 8 items | NO | ℹ️ Registered |

**Total individual checks executed: 116+**  
**Failures: 0**  
**Stop-ship issues: 0**  
**Test suite: 768 passed, 0 failed**

---

## Verdict

**Doc 5 LLM Resilience Layer is complete and correct.**

The implementation satisfies all acceptance criteria:

- AC1: Zero bare `.ainvoke`/`.astream` calls in any node — all LLM calls routed through wrappers ✅  
- AC6: Circuit breaker constants present and correct (threshold=5, reset=60s) ✅  
- AC7: BGE-M3 embedding wrapped with `asyncio.to_thread` + `EMBEDDING_TIMEOUT_SECONDS` ✅  
- AC8: 14 logger calls in resilience module (≥8 required) ✅  
- Safety invariant: `safety_check_node` is sync, deterministic, and has zero LLM/resilience dependency ✅  
- Graceful degradation: all three degradation paths (safety → intent → response) produce a usable user experience even during total LLM outage ✅  

The one open pre-launch action from this audit is **TD-1**: MSA Arabic fallback responses require Khaleeji dialect review before production.
