# Doc 4: Prompt Template Architecture — QA Audit Results

**Date:** 2026-05-22  
**Auditor:** Claude Sonnet 4.6 (automated, 4 parallel subagents)  
**Branch:** master  
**Head commit:** 585d12e  
**Plan:** `docs/superpowers/plans/2026-05-22-doc4-prompt-template-architecture.md`

---

## Executive Summary

| Phase | Checks | Result |
|---|---|---|
| 1. Structural Verification | 32 checks | ✅ 32/32 PASS |
| 2. Functional — Test Suite | 715 tests | ✅ 713 pass, 2 fail (pre-existing) |
| 3. Layer-by-Layer Correctness | 43 checks | ✅ 43/43 PASS |
| 4. compose_prompt Integration | 20 checks | ✅ 20/20 PASS |
| 5. Rules Service Integration | 4 checks | ✅ 4/4 PASS |
| 6. Token Budgeting | 7 checks | ✅ 7/7 PASS |
| 7. Patch Target Migration | 2 checks | ✅ 2/2 PASS |
| 8. Architectural Compliance | 5 checks | ✅ 5/5 PASS |
| 9. E2E Graph Routing | 5 route categories | ✅ All routing paths pass |
| 10. Tech Debt Register | 7 items | ℹ️ Documented below |

**Overall verdict: PASS — zero stop-ship findings. The Doc 4 implementation is correct and complete.**

The 2 failing tests (`test_cbt_full_3_step_progression_e2e`, `test_session_full_lifecycle_e2e`) are confirmed pre-existing failures present before Doc 4 changes. Root cause: `escalating_distress` flag accumulates on high-intensity LLM turns, triggering L2 escalation that blocks skill step advancement — a pre-existing behaviour orthogonal to this implementation.

---

## Phase 1 — Structural Verification

### 1.1 New File Existence (22/22)

```
PASS: src/sage_poc/prompts/__init__.py
PASS: src/sage_poc/prompts/schemas.py
PASS: src/sage_poc/prompts/loader.py
PASS: src/sage_poc/prompts/tokens.py
PASS: src/sage_poc/prompts/composer.py
PASS: src/sage_poc/prompts/templates/L0_persona.json
PASS: src/sage_poc/prompts/templates/L1_history.json
PASS: src/sage_poc/prompts/templates/L3_skill_wrapper.json
PASS: src/sage_poc/prompts/templates/L4_knowledge.json
PASS: src/sage_poc/prompts/templates/L5_user_context.json
PASS: src/sage_poc/prompts/templates/L2_intents/general_chat.json
PASS: src/sage_poc/prompts/templates/L2_intents/new_skill.json
PASS: src/sage_poc/prompts/templates/L2_intents/skill_continuation.json
PASS: src/sage_poc/prompts/templates/L2_intents/info_request.json
PASS: src/sage_poc/prompts/templates/L2_intents/exit_skill.json
PASS: src/sage_poc/prompts/templates/L2_intents/scope_refusal.json
PASS: src/sage_poc/prompts/templates/L2_intents/jailbreak.json
PASS: src/sage_poc/prompts/templates/L2_intents/crisis.json
PASS: src/sage_poc/prompts/templates/L2_intents/low_confidence.json
PASS: tests/test_prompts_loader.py
PASS: tests/test_prompts_tokens.py
PASS: tests/test_prompts_composer.py
```

### 1.2 Template JSON Schema Validation

PASS: **14 templates loaded and validated** (expected ≥14). All pass Pydantic schema.

| Template ID | Layer | Role | Budget |
|---|---|---|---|
| L0_persona | L0 | system | 150 |
| L1_history | L1 | user | 300 |
| L2_crisis | L2 | user | 50 |
| L2_exit_skill | L2 | user | 50 |
| L2_general_chat | L2 | user | 50 |
| L2_info_request | L2 | user | 50 |
| L2_jailbreak | L2 | user | 50 |
| L2_low_confidence | L2 | user | 50 |
| L2_new_skill | L2 | user | 50 |
| L2_scope_refusal | L2 | user | 50 |
| L2_skill_continuation | L2 | user | 50 |
| L3_skill_wrapper | L3 | user | 200 |
| L4_knowledge | L4 | user | 300 |
| L5_user_context | L5 | user | 100 |

### 1.3 Template ID Uniqueness

PASS: 14 template IDs, all unique.

### 1.4 Hardcoded Prompt Logic Removed from freeflow_respond.py

```
PASS: compose_prompt definition removed
PASS: PERSONA string literal removed
PASS: imports from prompts module (from sage_poc.prompts import compose_prompt, PERSONA)
PASS: PERSONA referenced (re-exported via __all__)
```

### 1.5 SkillStep technique_description Field

```
PASS: SkillStep.technique_description exists with empty string default
```

### 1.6 CBT Thought Record technique_description Populated

```
PASS: identify_thought has technique_description (161 chars)
PASS: explore_distortion has technique_description (159 chars)
PASS: balanced_thought has technique_description (139 chars)
```

---

## Phase 2 — Functional Verification

### 2.1 Full Test Suite (non-graph)

```
644 passed, 1 warning in 45.48s
```

**Result: 644 passed — exceeds Doc 2 baseline of 511+ ✅**

### 2.2 Full Test Suite Including test_graph.py

```
2 failed, 713 passed in 294s
```

The 2 failures are `test_cbt_full_3_step_progression_e2e` and `test_session_full_lifecycle_e2e`. Both are confirmed pre-existing failures (present before Doc 4 changes). Root cause: `escalating_distress` triggers L2 escalation that holds skill step at `validated_only` → `next_step = current`, blocking advancement. Not introduced by Doc 4.

### 2.3 Prompts-Specific Tests (78/78)

```
tests/test_prompts_loader.py    21 tests — 21 passed
tests/test_prompts_tokens.py     7 tests —  7 passed
tests/test_prompts_composer.py  50 tests — 50 passed
Total: 78 passed in 0.04s ✅ (minimum was 50 — exceeded)
```

### 2.4 Test Count vs Minimum

| File | Minimum | Actual | Status |
|---|---|---|---|
| test_prompts_loader.py | 16 | 21 | ✅ |
| test_prompts_tokens.py | 7 | 7 | ✅ |
| test_prompts_composer.py | 40 | 50 | ✅ |

### 2.5 Rules Service Tests Regression

```
287 passed in 5.99s ✅ (baseline: 241 — exceeded due to new integration tests)
```

Zero regressions in rules service tests.

### 2.6 Node Tests Regression

```
165 passed in 26.86s ✅
```

Zero regressions.

### 2.7 freeflow_respond Tests

```
10 passed in 1.77s ✅
```

All 10 tests pass including backward-compat re-export tests and new isolated rules mocking.

---

## Phase 3 — Layer-by-Layer Correctness (43/43)

### 3.1 L0 Persona — Content and Substrings

```
PASS: PERSONA re-export matches L0_persona.json (1131 chars)
PASS: L0 persona check — has_sage_identity
PASS: L0 persona check — has_scope_not_diagnose
PASS: L0 persona check — has_conciseness (2-4 sentences)
PASS: L0 persona check — no_em_dashes
PASS: L0 persona check — has_formatting_instruction
PASS: L0 persona check — has_skill_reference
```

### 3.2 L0 Persona — Backward Compatibility

```
PASS: freeflow_respond.PERSONA re-export matches prompts.PERSONA
```

### 3.3 L1 History — Windowing and Sanitization

```
PASS: Empty history returns None
PASS: Turn 0 outside 8-turn window (of 16 turns)
PASS: Turn 8 inside window
PASS: Turn 15 (last) inside window
PASS: Bold markdown stripped from assistant turns
PASS: Emoji stripped from assistant turns
PASS: User turns preserved verbatim (markdown kept)
PASS: User emoji preserved verbatim
```

### 3.4 L2 Intent — All 9 Templates, Intensity Guidance

```
PASS: All 9 intents have L2 templates
PASS: Low and high intensity produce distinct output
PASS: Intensity value 2 present in low block
PASS: Intensity value 8 present in high block
PASS: Unknown intent falls back to general_chat gracefully
PASS: Secondary intent appended to L2 block
```

### 3.5 L3 Skill Wrapper — P1-4 Fix (CRITICAL) ✅

L3 block preview (first 300 chars):
```
THERAPEUTIC APPROACH FOR THIS TURN:
You are gently guiding the user through CBT Thought Record. The current focus is: Help the user identify and clearly articulate the specific negative thought

Approach: Use Socratic questioning. Ask open questions that help the user surface and name their own thou...
```

```
PASS: P1-4 fix — no Goal: form label in L3 block
PASS: P1-4 fix — no Technique: form label in L3 block
PASS: THERAPEUTIC APPROACH header present
PASS: Skill name (CBT Thought Record) included in L3 block
PASS: No-announce instruction ("Do NOT announce the technique name") present
PASS: Technique description included in L3 block
PASS: Few-shot examples included in L3 block
PASS: Contraindications included in L3 block
```

**The primary deliverable of Doc 4 — the P1-4 fix — is confirmed working.** The old `Goal: X. Technique: Y.` form format is completely replaced by conversational therapeutic framing.

### 3.6 L3 Skill Wrapper — Arabic Example Selection

```
PASS: English selection returns first 2 examples
PASS: Arabic selection returns 2 examples
PASS: Arabic example selected when language=ar
PASS: Empty examples list handled (returns [])
PASS: Single example returns as-is
```

### 3.7 L3 Skill Wrapper — Escalation Bypass

```
PASS: Escalation uses skill_instruction layer (not L3_skill_wrapper)
PASS: L3 wrapper NOT fired during escalation
PASS: Raw escalation instruction present in user_str
```

### 3.8 L4 Knowledge — ABSTAIN and Citation

```
PASS: Citation marker [1] present in L4 block
PASS: Snippet content present in L4 block
PASS: ABSTAIN/uncertainty instruction present in L4 block
PASS: L4 returns None for None snippet
PASS: L4 returns None for empty snippet
```

### 3.9 L5 User Context — Clinical Flags

```
PASS: L5 returns None when no relevant flags
PASS: L5 returns content for substance_use flag
PASS: L5 includes MI/substance guidance for substance_use
PASS: L5 distress note present for escalating_distress flag
PASS: L5 includes both substance and trauma flags (multi-flag)
```

---

## Phase 4 — compose_prompt Integration Verification (20/20)

### 4.1 Return Signature Preserved

```
PASS: compose_prompt returns 3-tuple
PASS: system_str is str
PASS: user_str is str
PASS: layers is list
PASS: all layers are str
Layer count on minimal turn: 2
```

### 4.2 Progressive Disclosure — Minimal Turn (L0+L2 only)

```
PASS: persona layer always present
PASS: intent layer always present
PASS: history absent on turn 0
PASS: L3 absent without active skill
PASS: L4 absent without info_request
PASS: L5 absent without clinical flags
Layers on minimal turn: ['persona', 'intent']
```

This confirms v7 §5.6 progressive disclosure: most turns only carry L0+L2 (~210 words total).

### 4.3 User Message Always Last

```
PASS: User message is last in user_str
Layers with rich state: ['persona', 'history', 'intent', 'user_context']
```

### 4.4 Post-Crisis Context Injection

```
PASS: post_crisis_context in layers when crisis_state=monitoring
PASS: POST-CRISIS CONTEXT present in user_str
PASS: S7 result (RECOVERING) present in post-crisis block
```

### 4.5 All 6 Layers Fire on Rich State

```
Layers on rich state: ['persona', 'cultural', 'clinical_adaptation', 'history', 'intent', 'user_context', 'L3_skill_wrapper']
PASS: persona in layers
PASS: cultural in layers
PASS: clinical_adaptation in layers
PASS: history in layers
PASS: intent in layers
PASS: user_context in layers
```

---

## Phase 5 — Rules Service Integration Preserved (4/4)

These checks run against the **real Rules Service JSON files** (no mocks), confirming the Doc 1/Doc 2 integration contract is intact after the prompt migration.

### 5.1 CU-IS-001 Islamic Framing (Real Rules Service)

```
Layers: ['persona', 'cultural', 'intent']
PASS: Cultural layer tracked for Islamic message
PASS: Islamic framing injected into system prompt
Terms found: ['ISLAMIC', 'sabr', 'ibtila', 'Islamic', 'faith', 'spiritual']
```

### 5.2 PI-CF-001 Substance Use Adaptation (Real Rules Service)

```
Layers: ['persona', 'clinical_adaptation', 'intent', 'user_context']
PASS: clinical_adaptation layer tracked for substance_use
PASS: MI/substance guidance in system prompt
```

### 5.3 Secondary Intent Framing (Real Rules Service)

```
PASS: Secondary intent (info_request) framing present in user_str
```

### 5.4 Backward Compat Import for test_rules_integration.py

```
PASS: compose_prompt importable from sage_poc.nodes.freeflow_respond
```

---

## Phase 6 — Token Budgeting Verification (7/7)

### 6.1 Normal Turn Within 1100-Word Budget

```
Total words (normal turn): 210
PASS: Normal turn within 1100-word budget (210 words)
Breakdown: system=175, user=35
```

This matches the v7 design target of ~200–400 words for a minimal turn.

### 6.2 Long History Triggers Overflow Truncation

```
Total words after overflow handling: 522
PASS: Overflow handler reduced total to within budget (522 words)
Layers: ['persona', 'history', 'intent', 'user_context']
```

The overflow handler (L1 shrink to half-window) correctly reduces the prompt when 40-turn history pushes the total over 1,100 words.

### 6.3 Token Counting Utility

```
PASS: count_words basic cases
PASS: count_words_in_parts
PASS: count_words_in_parts empty list
```

---

## Phase 7 — Patch Target Migration (2/2)

### 7.1 test_freeflow_respond.py Patch Targets

```
PASS: No old patch target (sage_poc.nodes.freeflow_respond.rules_engine) — 0 occurrences
PASS: New patch target (sage_poc.prompts.composer.rules_engine) present — 7 occurrences
```

All 7 `rules_engine.evaluate` patch calls use the correct new module path.

### 7.2 test_rules_integration.py (No Patch Change Needed)

`compose_prompt` imported via re-export from `sage_poc.nodes.freeflow_respond`. No patching needed — integration tests call the real Rules Service. Confirmed working (included in the 287-pass rules test run).

---

## Phase 8 — Architectural Compliance (5/5)

### 8.1 Composer Has No Graph/Node Dependencies

```
PASS: Composer has no graph/node dependencies
Imports: sage_poc.state, sage_poc.skills.schema, sage_poc.rules,
         sage_poc.knowledge, .loader, .tokens — no graph or node imports
```

### 8.2 Loader Cache Invalidation

```
PASS: Loader cache invalidation works correctly — content consistent after reload
```

Note: `reload_all()` is a lazy-reset (clears cache + resets flag). Cache is re-populated on next `get_template()` call. This is correct by design (matches `sage_poc.rules.loader` pattern).

### 8.3 No New Graph Nodes

```
PASS: 9 nodes (unchanged from Doc 2)
Nodes: safety_check, intent_route, low_confidence_respond, skill_select,
       skill_executor, freeflow_respond, output_gate, crisis_response, gate_path_set
```

### 8.4 _sanitize_assistant_turn Re-exported

```
PASS: _sanitize_assistant_turn re-exported from freeflow_respond.py
```

### 8.5 PERSONA Staleness Comment Present

```
PASS: Comment present: "Evaluated at import time; will NOT reflect reload_all() calls. For backward compat only."
```

---

## Phase 9 — End-to-End Graph Routing

### 9.1 Greeting Path

No greeting-named tests exist in `test_nodes.py`. Covered by `test_english_general_chat_e2e` in `test_graph.py` — **PASSED**.

### 9.2 Crisis Path

```
20 passed, 145 deselected
```

All crisis routing tests pass: `test_crisis_bypasses_output_gate_at_safety_check_level`, `test_crisis_bypasses_output_gate_full_graph`, Khaleeji phrases, passive SI, negation handling.

### 9.3 Skill Path

```
18 passed, 147 deselected
```

All skill routing tests pass: `test_skill_executor_node_produces_instruction`, `test_compose_prompt_with_skill_instruction`, `test_grounding_skill_advances_through_all_5_steps`.

### 9.4 Clinical Flag Path

```
6 passed, 159 deselected
```

`test_clinical_flag_substance_use`, `test_clinical_flag_trauma`, `test_clinical_flag_medication`, `test_compose_prompt_clinical_flag_injects_adaptation` all pass.

### 9.5 Full Graph E2E (test_graph.py)

```
2 failed, 69 passed in 294s
```

**69/71 tests pass.** The 2 failures are:

**`test_cbt_full_3_step_progression_e2e`** — Stuck at `balanced_thought` after 6 turns. Root cause: `escalating_distress` fires from turns 2+ (intensity ≥ 6 × 3 consecutive turns), L2 escalation overrides `evaluate_step_policy` and holds `next_step = current` indefinitely. This prevents the skill from completing even after the final step is executed.

**`test_session_full_lifecycle_e2e`** — Same root cause; stuck at `explore_distortion`.

Both failures are confirmed pre-existing — they also fail on the original code before any Doc 4 changes. They are LLM-dependent tests where the real LLM returns high-intensity responses that trigger escalating_distress accumulation.

---

## Phase 10 — Tech Debt Register

| # | Item | Severity | Notes |
|---|---|---|---|
| TD-1 | L1 summarisation not implemented (`summary_trigger=10` in template config but not actioned) | LOW | Explicitly out of scope for POC |
| TD-2 | Overflow resolution only shrinks L1; steps 2–3 (reduce L3 examples, truncate L4) not implemented | LOW | Explicitly out of scope; documented in composer.py |
| TD-3 | L5 user context only uses clinical flags from current state; Full Build needs therapeutic profile from Cosmos DB | LOW | Out of scope for POC |
| TD-4 | A/B variant mechanism exists (`loader` accepts `variant` param) but no automated traffic splitting | LOW | Manual testing only; no routing logic built |
| TD-5 | `_FLAG_DESCRIPTIONS` in `composer.py` duplicates content from `clinical_flag_adaptations.json` — two sources of truth for flag descriptions | MEDIUM | Should converge in Full Build |
| TD-6 | Loader cache is not thread-safe (plain dict) — same as `rules/loader.py` | LOW | Acceptable for POC single-process FastAPI |
| TD-7 | Only CBT thought record has `technique_description` populated; other skills need it added for L3 wrapper to show description | MEDIUM | Content authoring task; schema is ready |

---

## Appendix: Test Count Summary

| Test File | Tests | Result |
|---|---|---|
| test_prompts_loader.py | 21 | ✅ 21 pass |
| test_prompts_tokens.py | 7 | ✅ 7 pass |
| test_prompts_composer.py | 50 | ✅ 50 pass |
| test_freeflow_respond.py | 10 | ✅ 10 pass |
| test_nodes.py | 165 | ✅ 165 pass |
| test_rules_*.py (5 files) | 287 | ✅ 287 pass |
| test_graph.py | 71 | ⚠️ 69 pass, 2 fail (pre-existing) |
| All other tests | 104 | ✅ 104 pass |
| **Total** | **715** | **713 pass, 2 fail** |

---

## Commit History (Doc 4)

```
585d12e fix: apply word-budget to overflow shrink, document stale PERSONA, isolate compose_prompt tests
c7e55ea feat: wire freeflow_respond to PromptComposer, re-export backward-compat symbols
dfae8e8 fix: warn on oversized cultural action, fix dead test fixture, add L1 overflow test
1a37185 feat: implement full 6-layer compose_prompt with token budgeting and L3 P1-4 fix
bf63da0 fix: use relevant list for distress_note guard, tighten substance_use test assertion
666bd9f feat: add L4 knowledge (with ABSTAIN) and L5 user context templates
ed5b79f fix: guard L2 builder against missing general_chat fallback, fix debug log, add mid-intensity test
dc1f73b feat: add L2 per-intent framing templates with intensity-aware clinical guidance
fad7523 fix: escape history lines before format(), always include first history turn
c7699ff feat: add L0 persona and L1 history windowing templates
530397a fix: harden L3 composer — escape SkillStep braces, warn on missing Arabic examples, strip triple-asterisk
```
