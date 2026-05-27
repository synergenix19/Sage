# Experiments 4.5 + 4.6: RAG Pipeline Accuracy + Blended Intent Handling

> **4.4 status: COMPLETE** — 63/63 tests passing, latency p95=1.411s (KPI: <3s ✓), quality log at `docs/experiment_4_4_quality_log_2026-05-27.json` (90 turns, awaiting 3 clinician scorers). Pushed at commit `c1d3f32`.

---

## Context

V7 §16.2 Weeks 10–12 schedules 4.5 and 4.6 in parallel with 4.4. With 4.4 done, both run next.

- **4.5**: RAG pipeline accuracy — 100 queries, <5% unsupported claims
- **4.6**: Blended intent handling — 20 mixed queries, ≥80% successfully blended

**No production code changes are required for either experiment.** Both are pure test harnesses over already-complete infrastructure.

---

## Codebase State — What Already Exists

### RAG Pipeline (for 4.5)
- `src/sage_poc/nodes/tools/knowledge_lookup.py` — LLM-invoked tool, wraps `PostgresKnowledgeRepository`, returns `{passages, abstain}`, falls back to `abstain=True` when DB pool is None
- `src/sage_poc/knowledge/postgres_repository.py` — Hybrid BM25+vector via Reciprocal Rank Fusion (k=60), filters by language, KNOWLEDGE_ABSTAIN_THRESHOLD=0.0 (uncalibrated)
- `src/sage_poc/prompts/composer.py:_build_l4_knowledge_block()` — injects passage text into prompt; when `abstain=True` + no passages, injects "do not fabricate" instruction instead
- `src/sage_poc/nodes/output_gate.py` — records `knowledge_abstain` (bool) and `knowledge_passage_ids` (list) to audit headers
- Existing tests: `test_knowledge_repository.py` (mock DB: match, abstain, language filter), `test_knowledge_lookup.py` (tool behavior), `test_knowledge_retrieve_node.py` (node routing)
- **Coverage gap**: no query corpus with expected-passage mapping, no abstain-instruction-presence test, no audit metadata integration test, no evaluation log for <5% KPI measurement

### Blended Intent (for 4.6)
- `src/sage_poc/nodes/intent_route.py` — classifies `primary_intent` + `secondary_intent` from 8 categories; writes both to state
- `src/sage_poc/prompts/composer.py:_build_l2_intent_block()` (line 147) — appends `(blended with: {secondary_intent})` to L2 block when secondary is present
- `src/sage_poc/prompts/composer.py:_compute_l1_budget()` (line 119) — shrinks to base 450-word budget when `secondary_intent == "info_request"`
- Knowledge injection fires in `compose_prompt` when `primary_intent OR secondary_intent == "info_request"`
- `src/sage_poc/graph.py:_route_after_intent()` — routing follows `primary_intent` only; secondary_intent is advisory metadata, does NOT change routing edge
- Existing tests: 2 classification tests in `test_intent_route_node.py`, 2 compose tests in `test_nodes.py` (lines 730, 747), routing matrix in `test_routing.py` (no secondary_intent cases)
- **Coverage gap**: no systematic scenario matrix, no routing invariance test with secondary present, no budget-change test, no multi-turn blended continuation test

---

## Experiment 4.5: RAG Pipeline Accuracy

### KPI
- **Primary**: <5% unsupported claims across 100 evaluated queries (human-reviewed from JSON log)
- **Infrastructure gate** (deterministic): correct retrieval, correct abstain, correct prompt injection, correct audit metadata

### Query Corpus Design (`query_corpus.py`)
60 **in-corpus queries** → mock DB returns 1-3 predefined passages. Asserts: passages appear in L4 block, abstain=False, source_ids in audit.

40 **out-of-corpus queries** → mock DB returns empty. Asserts: abstain=True, "do not fabricate" instruction in L4 block.

Corpus covers: CBT/DBT/MI/BA/sleep/grounding modalities (psychoeducation queries), medication questions (scope — expect abstain), grief/trauma questions, crisis-adjacent but not harm (anxiety, panic), Arabic-language queries (6 cases), nonsense/adversarial queries (4 cases).

### Harness Structure
```
tests/experiment_4_5/
  __init__.py
  conftest.py                    — mock DB pool factory, passage builder, state builder
  query_corpus.py                — 100 query dicts: {id, query, expect_abstain, expected_source_ids, language}
  test_retrieval_accuracy.py     — mock DB: in-corpus → passages returned; out-of-corpus → abstain
  test_grounding_prompt.py       — L4 block contains passage text; abstain block has "do not fabricate"
  test_audit_metadata.py         — knowledge_abstain + knowledge_passage_ids written by output_gate
  generate_rag_evaluation_log.py — standalone: 100 queries → real LLM responses → JSON for review
```

### Key Tests
**`test_retrieval_accuracy.py`**:
- Parametrized over all 60 in-corpus queries: mock DB returns passages → `result.abstain is False` and passage text present
- Parametrized over all 40 out-of-corpus queries: mock DB returns [] → `result.abstain is True`
- Language filter: Arabic query passes `language="ar"` to DB call
- Threshold: `rrf_score <= 0.0` rows are filtered out

**`test_grounding_prompt.py`**:
- When `knowledge_passages` in state + `abstain=False`: L4 block contains `[1]` citation format
- When `abstain=True` + no passages: L4 block contains "do not fabricate"
- When `abstain=False` + passages: L4 block does NOT contain "do not fabricate"
- `compose_prompt()` injects knowledge when `primary_intent="info_request"` OR `secondary_intent="info_request"`

**`test_audit_metadata.py`**:
- `output_gate_node` writes `knowledge_abstain=True` when state has `knowledge_abstain=True`
- `output_gate_node` writes `knowledge_passage_ids` when state has passages
- Empty passage list → `knowledge_passage_ids=[]` in audit

**`generate_rag_evaluation_log.py`** (`@pytest.mark.slow` excluded):
- Runs all 100 queries through full node chain (knowledge_retrieve or freeflow with knowledge_lookup)
- Saves `{query_id, query, passages_retrieved, abstain, llm_response, unsupported_claim: null}` per entry
- Reviewers fill `unsupported_claim: true/false` per entry; <5% true = KPI pass

---

## Experiment 4.6: Blended Intent Handling

### KPI
- **Primary**: ≥80% of 20 scenarios "successfully blended" — primary intent correctly routed AND secondary intent visible in response (requires LLM evaluation log for human review)
- **Infrastructure gate** (deterministic): classification, prompt injection, routing invariance, budget calculation

### Scenario Design (`scenarios.py`)
20 scenarios spanning key combinations:

| ID | Primary | Secondary | Expected route | Test focus |
|----|---------|-----------|---------------|------------|
| B01-B04 | skill_continuation | info_request | skill_executor | Most common blend: skill + factual question |
| B05-B07 | new_skill | info_request | skill_select | Symptom + factual question |
| B08-B09 | new_skill | general_chat | skill_select | Distress + contextual affect |
| B10-B11 | general_chat | info_request | freeflow | Casual + factual (no skill) |
| B12-B13 | info_request | general_chat | skill_select | Factual primary + emotional context |
| B14-B15 | skill_continuation | exit_skill | skill_executor | Ambivalent mid-skill (primary wins) |
| B16 | crisis | general_chat | crisis | Crisis overrides everything |
| B17 | crisis | info_request | crisis | Crisis overrides everything |
| B18 | exit_skill | info_request | skill_executor (active) / freeflow (no skill) | Exit with information need |
| B19-B20 | scope_refusal | info_request | gate | Boundary violation; secondary ignored |

### Harness Structure
```
tests/experiment_4_6/
  __init__.py
  conftest.py                          — state builders, mock LLM with parameterized JSON responses
  scenarios.py                         — 20 scenario dicts
  test_blended_classification.py       — intent_route parses secondary_intent for each scenario
  test_prompt_injection.py             — L2 block contains "(blended with: X)"; knowledge injected
  test_routing_invariance.py           — secondary_intent doesn't change routing edge
  test_budget_calculation.py           — L1 budget = 450 (not 600) when secondary=info_request
  generate_blended_evaluation_log.py   — standalone: 20 scenarios → real LLM → JSON for review
```

### Key Tests
**`test_blended_classification.py`**:
- Parametrized over all 20 scenarios: mock LLM returns `{primary, secondary, ...}` → assert both written to state
- Null secondary: `secondary_intent=null` in LLM output → `state["secondary_intent"] is None`
- Malformed JSON: falls back to `secondary_intent=None`

**`test_prompt_injection.py`**:
- When `secondary_intent="info_request"`: L2 block contains `"blended with: info_request"`
- When `secondary_intent=None`: L2 block does NOT contain "blended with"
- When `secondary_intent="info_request"` + knowledge passages in state: passages injected
- When `secondary_intent="general_chat"` (non-info): knowledge NOT injected from secondary

**`test_routing_invariance.py`**:
- Parametrized over all 20 scenarios: `secondary_intent` set in state, routing follows `primary_intent` only
- Crisis with secondary: routing = "crisis" regardless of secondary
- scope_refusal with secondary: routing = "gate" regardless of secondary

**`test_budget_calculation.py`**:
- `secondary_intent="info_request"` → `_compute_l1_budget` = 450 (base)
- `secondary_intent="general_chat"` + no skill, no primary info → budget = 600 (flex)
- `primary_intent="info_request"` alone → budget = 450 (base)

---

## Files to Create

**No production code changes.**

Created:
- `tests/experiment_4_5/__init__.py`, `conftest.py`, `query_corpus.py`
- `tests/experiment_4_5/test_retrieval_accuracy.py`, `test_grounding_prompt.py`, `test_audit_metadata.py`
- `tests/experiment_4_5/generate_rag_evaluation_log.py`
- `tests/experiment_4_6/__init__.py`, `conftest.py`, `scenarios.py`
- `tests/experiment_4_6/test_blended_classification.py`, `test_prompt_injection.py`, `test_routing_invariance.py`, `test_budget_calculation.py`
- `tests/experiment_4_6/generate_blended_evaluation_log.py`

---

## Verification

```bash
# Fast suite — both experiments
python -m pytest tests/experiment_4_5/ tests/experiment_4_6/ -m "not slow" -v

# Full regression check
python -m pytest tests/ -m "not slow" --ignore=tests/experiment_4_4/test_latency.py --ignore=tests/experiment_4_5/generate_rag_evaluation_log.py -q

# Evaluation logs (requires API key + live DB for 4.5)
python tests/experiment_4_5/generate_rag_evaluation_log.py --dry-run   # test harness
python tests/experiment_4_6/generate_blended_evaluation_log.py         # blended scenarios
```

---

## Known Limitations

1. **4.5 retrieval quality** — `KNOWLEDGE_ABSTAIN_THRESHOLD=0.0` means all non-zero RRF rows pass. Calibration with `scripts/calibrate_retrieval_threshold.py` is pre-production work, not in scope for this harness.
2. **4.5 <5% KPI** — cannot be automated deterministically; requires human-reviewed evaluation log. LLM-as-judge is an acceptable alternative if three clinical reviewers are unavailable.
3. **4.6 ≥80% KPI** — "successfully blended" requires evaluating whether the LLM response visibly addresses both intents. The evaluation log provides the raw material; scoring is manual or LLM-judged.
4. **4.6 secondary intent routing** — secondary_intent is advisory metadata, not a routing signal. No code changes needed; this is an architectural decision documented in V7.
