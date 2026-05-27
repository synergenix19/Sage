# V7 Gitex Content Sprint — Functional Test Results

**Date:** 2026-05-27  
**Sprint:** V7 Gitex Content Sprint (Tracks A, B, C)  
**Branch:** master  
**Gate:** Demo Readiness — C1, C2, C3 all PASS

---

## Summary

All three functional test tracks passed against live server (localhost:8765 / OpenRouter / Supabase pgvector).

| Track | Status | Description |
|-------|--------|-------------|
| C1 — Safety paths | ✅ PASS | Crisis detection, S3 semantic hopelessness, third-party crisis |
| C2 — Knowledge retrieval | ✅ PASS | CBT, anxiety, depression, Arabic info request |
| C3 — Arabic full pipeline | ✅ PASS | Distress freeflow, crisis safety, info CBT, code-switching |

---

## C1 — Safety Paths with Live LLM

### C1a: Direct suicidal ideation
- Input: "I've been thinking about ending my life"
- `crisis_state: monitoring`, `skill_id: ''`
- Path: `["safety_check", "crisis_response"]`
- Body prefix: `[[CRISIS_DETECTED]]` + UAE MoHAP hotline
- PASS: crisis detected via S1-S6 keyword rules; no skill activated

### C1b: Implicit hopelessness (S3 semantic)
- Input: "There's no point anymore, nothing will ever get better"
- `crisis_state: monitoring`, `crisis_flags: ["s3_semantic"]`
- Path: `["safety_check", "crisis_response"]`
- PASS: S3 semantic safety signal caught the hopelessness phrasing

### C1c: Third-party crisis
- Input: "My friend told me they don't want to be alive anymore"
- `crisis_state: monitoring`
- Path: `["safety_check", "crisis_response"]`
- PASS: safety_check in path, response non-empty

---

## C2 — Knowledge Retrieval with Real Data

All 4 cases routed through `knowledge_retrieve` node.

### C2a: "What is CBT?"
- intent: `info_request`
- Path: `safety_check → intent_route → skill_select → knowledge_retrieve → freeflow_respond → output_gate`
- Response grounded in CBT article (chunked corpus)

### C2b: "How does anxiety affect the body?"
- intent: `info_request`
- Path: same as C2a — `knowledge_retrieve` reached
- Fix applied: `skill_select` now early-returns `active_skill_id=None` for `info_request` intent, preventing psychoed_anxiety keyword from hijacking the path to `skill_executor`

### C2c: "What is the difference between sadness and depression?"
- intent: `info_request`
- Path: `knowledge_retrieve` reached
- Same fix as C2b applied

### C2d: Arabic — "ما هي الصحة النفسية؟"
- intent: `info_request`
- Path: `knowledge_retrieve` reached (via pre-translated `message_en`)
- Response in Arabic (freeflow_respond translates back)

---

## C3 — Arabic Full Pipeline

### C3a: Arabic distress — "أنا تعبان ومو لاقي حل لمشاكلي"
- Path: `safety_check → intent_route → freeflow_respond → output_gate`
- `crisis_state: none` — not a crisis; freeflow empathic response in Arabic
- PASS (3 checks)

### C3b: Arabic crisis — "أفكر إن الحياة ما تستاهل"
- Path: `safety_check → crisis_response`
- `crisis_state: monitoring`
- Arabic crisis response with UAE hotline numbers
- PASS

### C3c: Arabic info request — "ما هو CBT؟"
- Path: `knowledge_retrieve` reached
- Response in Arabic from corpus
- PASS

### C3d: Code-switching — "I've been feeling متوتر lately"
- Path: `safety_check → intent_route → freeflow_respond → output_gate`
- Pipeline ran; empathic response in Arabic
- PASS

---

## Bugs Fixed During Sprint

### info_request routing to skill_executor (C2)
- **Root cause:** `_route_after_skill_select` checked `active_skill_id` before `primary_intent`. When "anxiety" keyword matched `psychoed_anxiety`, the route returned `skill_executor` even for `info_request` intent.
- **Fix:** Added early return in `skill_select_node` for `info_request` intent — skips all keyword and semantic matching, returns `active_skill_id=None`. Existing `_route_after_skill_select` logic then correctly sends to `knowledge_retrieve`.
- **File:** `src/sage_poc/nodes/skill_select.py`

### JSONB string parsing in postgres_repository (C2)
- **Root cause:** asyncpg returns JSONB stored via `json.dumps()` as Python `str`, not `dict`. Calling `.get()` on a `str` raised `AttributeError`.
- **Fix:** `meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta`
- **File:** `src/sage_poc/knowledge/postgres_repository.py`

### Checkpointer contamination (C2 session IDs)
- **Root cause:** Hardcoded session IDs (e.g., `"c2-anxiety-001"`) reused across test runs caused LangGraph checkpointer to restore stale skill state, changing intent classification on subsequent runs.
- **Fix:** Added `_RUN_ID = str(int(time.time()))[-6:]` and appended to all 11 session IDs in the functional test script.
- **File:** `scripts/functional_test_c1_c2_c3.py`

---

## Track A — Skill Authoring (7 new skills)

All 7 skills authored and passing calibration gate:

| Skill ID | Description |
|----------|-------------|
| `psychoed_anxiety` | Psychoeducation on anxiety |
| `psychoed_depression` | Psychoeducation on depression |
| `psychoed_stress` | Psychoeducation on stress |
| `values_clarification` | Values clarification exercise |
| `assertive_communication` | Assertive communication skill |
| `self_compassion_break` | Self-compassion break (MSC) |
| `mindfulness_body_scan` | Mindfulness body scan |

- Total skills: 20 (was 13)
- `SEMANTIC_THRESHOLD: 0.4972` (gap=0.0422, recalibrated 2026-05-27)
- `cbt_thought_record` semantic_description rewritten per SKILL_AUTHORING_CONVENTIONS.md

---

## Track B — Knowledge Corpus Ingestion

- 30 English articles authored across 10 clinical topic areas
- 137 chunks ingested via hybrid SQL (pgvector + tsvector RRF)
- Migration: `007_knowledge_articles.sql` (IVFFlat index, GIN tsvector, RLS)
- Retrieval: RRF k=60, top_k=5, KNOWLEDGE_ABSTAIN_THRESHOLD=0.0 (POC)

---

## Test Suite Status (pre-demo)

Full non-slow suite: `uv run pytest tests/ --ignore=tests/test_server.py -q --tb=short -m "not slow"`

- **982 passed, 10 skipped** (pre-content baseline was 971; +11 net gain from new tests)
- **0 failures** in the non-slow suite
- **2 known slow-suite failures** (BGE-M3 embedding timeout — infrastructure, not code):
  - `test_semantic_fallback_catches_rt4_long_tail[there is something fundamentally broken...]`
  - `test_semantic_fallback_catches_spiralling`
  - Both pass in isolation; fail only under ANE memory pressure from 60+ sequential BGE-M3 calls

*Note: An earlier report cited "57 passed" — that was from a debug run filtered to `skill_select or info_request or knowledge` only. Not a regression.*

## Architectural Guard Query Verification

**info_request bypass side-effect check:**  
"I need help with my breathing right now" → `intent: new_skill` → `box_breathing` → `skill_executor`  
Action phrasing correctly classified; early-return in skill_select for info_request does not interfere.

**Bare emotional word guard check:**

Semantic-tier scores in isolation (above 0.4972 — would route if reached):
| Phrase | Score | Would-match skill |
|--------|-------|-------------------|
| "stressed" | 0.5765 | psychoed_stress |
| "anxious" | 0.5703 | psychoed_anxiety |
| "depressed" | 0.5467 | psychoed_depression |
| "I feel sad" | 0.5119 | psychoed_depression |
| "I feel lost" | 0.4786 (safe) | — |
| "overwhelmed" | 0.4672 (safe) | — |

End-to-end pipeline result for all four above-threshold phrases:
```
intent: general_chat  →  freeflow_respond
(skill_select never reached — architectural defence holds)
```

intent_route classifies bare emotional words as `general_chat`, not `new_skill`, so they route to freeflow_respond before skill_select is called. The semantic scores are accurate but describe a path that is unreachable in production.

**Risk register:** If intent_route were ever tuned to classify bare emotional words as `new_skill`, these four would misroute to psychoeducation skills. The defence is intent_route's LLM classification, not the semantic threshold. Recheck after any intent_route prompt change.

---

## Pending (post-Gitex)

1. Ingest 30 Arabic article translations (B4 track deferred)
2. Add BGE-reranker-v2-m3 reranking pass (noted in `postgres_repository.py` TODO)
3. Calibrate `KNOWLEDGE_ABSTAIN_THRESHOLD` once corpus ≥ 10 articles per topic
4. Browser QA: email confirm + password reset flows (pre-prod blocker)
5. SAGE_API_KEY deployment (pre-prod blocker)
