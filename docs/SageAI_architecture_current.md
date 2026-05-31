# SageAI Architecture — Current State

**Document type:** Living codebase reference  
**Last updated:** 2026-05-30  
**Supersedes:** `SageAI_v7_FINAL_COMPLETE.docx` and `docs/v7.1-post-crisis-state-addendum.md` for all code-level claims  
**Ground truth path:** `sage-poc/`

---

## 1. Overview

SageAI is a bilingual (Arabic/English) therapeutic wellness companion built on LangGraph. It routes each user turn through a deterministic 9-node graph, selecting from 20 structured therapeutic skills or falling back to evidence-informed freeflow conversation. Crisis detection, clinical flag tracking, and post-crisis state management run on every turn ahead of any response generation.

### 1.1 What changed from v7 FINAL / v7.1 addendum

The v7 FINAL document and v7.1 addendum described a 8-node graph with 13 skills, a stateless architecture, and several features as planned but not implemented. The following is a summary of what has changed since those documents were written, to orient readers who know the prior spec.

| Area | v7 FINAL / v7.1 | Current (2026-05-30) |
|---|---|---|
| Graph nodes | 8 nodes | **9 nodes** — `knowledge_retrieve` added |
| Skill count | 13 | **20** (7 new in Gitex sprint: psychoed_anxiety/depression/stress, values_clarification, assertive_communication, self_compassion_break, mindfulness_body_scan) |
| Safety layer | S1 lexicon only (S3 planned) | **S1 + S3 OR-fusion live** (`S3_THRESHOLD=0.8059`, 48-phrase corpus) |
| Crisis state | Bool flag `crisis_occurred_this_session` (v7); replaced by `crisis_state` enum (v7.1) | **v7.1 state machine live** + S7 classifier live (`post_crisis_classifier.py`) |
| Session persistence | Stateless — history rebuilt from client payload each turn | **Stateful** — `AsyncPostgresSaver` LangGraph checkpointer; `DATABASE_URL` required |
| Memory layer | Not implemented | **Live** — therapeutic profiles, pgvector session summaries, clinician review queue |
| LLM instances | Per-request factories | **Singletons** via `@lru_cache` (`llm.py`) |
| Resilience | No timeout or fallback | **Resilience layer live** — timeout (30s), retry (2x), circuit breaker (5 failures), `fallbacks.json` |
| Prompt architecture | Prompts hardcoded in nodes | **JSON templates** (`prompts/templates/`) composed per-turn |
| Cultural output | Rules checked post-generation | **Live** — cultural output validation in `output_gate`, identity substitution with restricted PDPL audit table |
| Criteria evaluation | Word-count only | **LLM evaluator** for 4 skills (`criteria_eval.py`), word-count for all others |
| Clinical flags | Crisis flags only | **Extended** — clinical_flags (4 categories), new_clinical_flags_turn, third_party_crisis, cross-session persistence via flag_lifecycle_config.json |
| Schema conformance | Not tracked | **Registry live** (`skills/conformance.py`, `GET /health/schema-conformance`) |
| Ferry fields in API | Present | **Removed** — all cross-turn state comes from LangGraph checkpoint |
| Audit trail | Frontend-written to Supabase | **Server-side** in `output_gate` and `crisis_response`, before response exits graph |
| Banned opener | Not implemented | **Live** — 6 patterns, 1 retry, vetted fallback substitution |

The v7.1 addendum (`docs/v7.1-post-crisis-state-addendum.md`) remains accurate for the post-crisis state machine design, S7 classification labels, and the `post_crisis_check_in` skill. This document supersedes it for implementation details (node wiring, state fields, routing conditions).

---

## 2. Graph Topology

### 2.1 Node Catalogue and Design Notes

The graph has 9 nodes. They are not structurally uniform — understanding what makes each one distinct matters when debugging, adding behaviour, or reading traces.

| Node | Implementation | Role |
|---|---|---|
| `safety_check` | `nodes/safety_check.py` | Detect language, translate, S1+S3 crisis detection, S7 post-crisis classifier, clinical flag accumulation, trajectory updates |
| `intent_route` | `nodes/intent_route.py` | LLM classifier (8 intent categories), emotional intensity, engagement scoring |
| `skill_select` | `nodes/skill_select.py` | Tier 1 keyword match → Tier 2 BGE-M3 semantic match; post-crisis auto-select; info_request early-return |
| `knowledge_retrieve` | `nodes/knowledge_retrieve.py` | RAG retrieval via `PostgresKnowledgeRepository`, fires on `info_request` when no active skill |
| `skill_executor` | `nodes/skill_executor.py` | Step execution, step_policy evaluation, LLM criteria eval, escalation detection, resistance scoring |
| `freeflow_respond` | `nodes/freeflow_respond.py` | 6-layer prompt composition, LLM response with optional `knowledge_lookup` tool loop, prior context retrieval |
| `output_gate` | `nodes/output_gate.py` | Cultural output validation, identity substitution, banned opener retry, format check, Arabic translation, audit |
| `crisis_response` | `graph.py` (inline `_crisis_response_node`) | Deterministic rule-based crisis protocol, sets `crisis_state="monitoring"`, bypasses output_gate |
| `low_confidence_respond` | `nodes/low_confidence_respond.py` | Clarification request when `intent_confidence < 0.6` |

**What makes each node distinctive:**

**`safety_check` — always fires, highest responsibility.** Every single user turn passes through this node first. It does the most work before any LLM call: language detection, async translation, S1 lexicon evaluation, S3 semantic scoring (BGE-M3, in a thread), S7 post-crisis classification (LLM call if crisis_state=="monitoring"), trajectory updates, clinical flag accumulation. Adding behaviour here has turn-one cost on every request.

**`intent_route` — LLM-based, single point of failure.** Uses the classifier LLM to assign one of 8 intents. It is the sole gate that prevents bare emotional words ("I'm stressed", "I feel depressed") from scoring above `SEMANTIC_THRESHOLD` and triggering psychoeducation skills. If the general_chat definition in `INTENT_SYSTEM` is edited, the bare-emotional-word guard test must be re-run before deployment.

**`skill_select` — two-tier, no LLM.** Keyword matching (Tier 1) is synchronous and deterministic. Semantic matching (Tier 2) runs BGE-M3 in a thread with a 10s timeout. Neither tier makes an LLM call. Three distinct early-return paths: info_request bypass (before any matching), post-crisis auto-select (skips keyword/semantic), and normal two-tier matching.

**`knowledge_retrieve` — pure data retrieval, no LLM.** The only node that makes no LLM call and no embedding model call of its own (the pgvector search uses pre-computed embeddings stored in the database). It is also the only node that depends on a live DB pool to function — if the pool is unavailable, it returns `knowledge_abstain=True` immediately without failing. Distinguished from the `knowledge_lookup` tool inside `freeflow_respond`: `knowledge_retrieve` fires on the `info_request → skill_select` path; `knowledge_lookup` fires mid-response when the LLM decides to call a tool.

**`skill_executor` — step state machine with embedded sub-calls.** Unlike the other nodes, `skill_executor` calls `criteria_eval.evaluate_completion_criteria()` internally — but this is a module call, not a graph node transition. `criteria_eval` does not appear in the node path or in LangGraph's graph definition. `skill_executor` is also the only node that can route directly to `crisis_response` (re-escalation detected inside a skill session).

**`freeflow_respond` — main LLM response path.** The most complex prompt composition: 6 layers (L0–L5), prior context retrieval, optional tool loop. All non-skill, non-knowledge, non-crisis responses flow through here. `knowledge_retrieve` always feeds into `freeflow_respond` as well (Node 4 produces passages; Node 6 generates the response from them).

**`output_gate` — NOT a response generator.** This is a transformation and audit node. It does not call the LLM for content. It validates, substitutes, translates, and logs. Every non-crisis response flows through it. It is the only node that writes the LangGraph checkpoint `last_turn_at` timestamp, persists session summaries, and fires the clinician review queue. It can route back to `freeflow_respond` exactly once (for a banned opener retry).

**`crisis_response` — the exception to every rule.** This is the only node defined inline in `graph.py` rather than in the `nodes/` directory. It behaves differently from all other nodes in four ways: (1) it routes directly to `END`, bypassing `output_gate` entirely; (2) it calls `write_session_audit` directly via `asyncio.create_task` (other nodes rely on output_gate to do this); (3) it sets `last_turn_at` directly (normally output_gate's responsibility); (4) it is the only node that transitions `crisis_state` from `"none"` or `"resolved"` to `"monitoring"`. Its response is purely deterministic — the crisis hotline text comes from a rules engine `crisis_content` evaluation with a hard-coded fallback, never from an LLM. `crisis_state → "resolved"` can also be set by `skill_executor` (on `post_crisis_check_in` L1 exit or skill completion); `crisis_response` only sets it to `"monitoring"`.

**`low_confidence_respond` — the lightest node.** Generates a single clarification request using `get_responder()` + `resilient_stream` with a simple hardcoded `_SYSTEM` prompt ("ask ONE gentle, open-ended clarifying question, maximum 2 sentences"). It does NOT use the 6-layer prompt composition system — no L0-L5 template, no history, no clinical context. It routes directly to `output_gate` for validation and audit, same as `freeflow_respond`.

### 2.2 `criteria_eval` — called inside skill_executor, not a graph node

`nodes/criteria_eval.py` evaluates whether a user's response meets a step's `completion_criteria`. It is called by `skill_executor` after `evaluate_step_policy()` returns the `_criteria_blocked` sentinel. It makes an LLM call (classifier model) for the 4 `_LLM_CRITERIA_SKILLS`; it uses a word-count heuristic for all others.

`criteria_eval` does **not** appear as a node in `build_graph()`, does **not** appear in `state["path"]`, and does **not** transition state in LangGraph. It is a function called inside a node — more like a helper called by `intent_route_node` than a separate routing step. This is intentional: criteria evaluation is an implementation detail of step advancement, not a routing decision visible to the graph.

### 2.2 Routing Graph

```
safety_check
  ├── safe  → intent_route
  └── crisis → crisis_response → END

intent_route
  ├── skill_select  → (see below)
  ├── skill_executor → (skill continuation)
  ├── freeflow_respond
  ├── crisis_response → END
  ├── low_confidence_respond → output_gate → END
  └── gate (scope_refusal / jailbreak) → output_gate → END

skill_select
  ├── skill_executor
  ├── knowledge_retrieve → freeflow_respond → output_gate
  └── freeflow_respond → output_gate

skill_executor
  ├── crisis_response → END  (re-escalation within monitoring)
  └── freeflow_respond → output_gate

output_gate
  ├── freeflow_respond  (banned opener retry, at most 1 retry)
  └── END
```

**Note:** `criteria_eval` (`nodes/criteria_eval.py`) is a module called within `skill_executor` — it is not a graph node and does not appear in the node path.

### 2.3 Key Routing Rules

| Condition | Route taken |
|---|---|
| S1 or S3 fires (is_safe=False) | `crisis_response` regardless of crisis_state |
| `crisis_state == "monitoring"` AND `s7_result == "NEW_CRISIS"` | `crisis_response` |
| `crisis_state == "monitoring"` AND safe | `intent_route` → forced to `skill_select` (bypasses confidence gate) |
| `intent_confidence < 0.6` (not monitoring) | `low_confidence_respond` |
| `primary_intent == "info_request"` | `skill_select` → immediate early-return → `knowledge_retrieve` |
| `primary_intent == "exit_skill"` AND active skill | `skill_executor` (runs L1 exit protocol) |
| `primary_intent == "scope_refusal"` or `"jailbreak"` | `output_gate` (deterministic response, no LLM) |
| Banned opener detected (first occurrence) | `output_gate` → retry → `freeflow_respond` |
| Banned opener persists after retry | Vetted fallback substituted; `output_gate_fallback_substituted` appended to path |

---

## 3. Safety Layer

### 3.1 S1 — Rules-Engine Lexicon

`safety_check_node` calls `rules_engine.evaluate("safety", {text_en, text_ar, language})`. Rule categories under `rules/data/safety/`:

- `crisis_keywords.json` — direct crisis keyword matching
- `passive_si_patterns.json` — passive suicidal ideation phrases (SK-EN-002, v1.1.1 as of 2026-05-27; includes bare "no future for me")
- `clinical_flag_patterns.json` — substance_use, trauma_indicator, eating_concern, medication_mention
- `false_positive_exclusions.json` — idiomatic phrases to suppress (e.g. "dying of laughter", heat idioms)

Rules engine context keys are `text_en`, `text_ar`, `language` — **not** `message`.

Action types in the results:
- `crisis_flag` → appended to `crisis_flags`
- `clinical_flag` → appended to `clinical_flags`
- `third_party_crisis` → sets `third_party_crisis=True`; suppresses `crisis_flags` (third-party concern is not an active self-harm signal)
- `crisis_suppress` → prevents S3 from adding `s3_semantic` to crisis_flags for this phrase

### 3.2 S3 — BGE-M3 Semantic Crisis Detection

`safety/s3_semantic.py`. Runs every turn, after S1. OR-fusion: S1 OR S3 catching → `crisis_response`.

- Model: BAAI/bge-m3 (shared instance with `skill_select` and `memory/embedding.py`)
- Corpus: 48 phrases in `safety/crisis_phrases.json`
- Threshold: `S3_THRESHOLD = 0.8059` (calibrated 2026-05-26, gap=0.3234)
- Timeout: 5.0s via `asyncio.wait_for`; timeout or exception → score 0.0, S1 result only (fail-open)
- Coverage: English only. TODO: bilingual (Arabic text path not yet implemented).
- When S3 score ≥ threshold: adds `"s3_semantic"` to `crisis_flags` unless a `crisis_suppress` action fired for this message.
- S3 shares the BGE-M3 instance loaded by `skill_select._ensure_semantic_ready()`. No second model load.

**S2 (MARBERT classifier) is not implemented.** The architecture comment in `safety_check.py` documents this gap and the intended implementation path.

### 3.3 S7 — Post-Crisis Classifier

`nodes/post_crisis_classifier.py`. Fires only when `crisis_state == "monitoring"`.

Two-tier architecture:
1. Keyword tier: `_STILL_DISTRESSED_KEYWORDS` checked first (conservative), then `_RECOVERY_KEYWORDS`. Keywords exclude phrases that overlap with S1–S6 crisis lexicon.
2. LLM tier: single-message evaluation (no conversation history), uses `resilient_invoke`.

Labels: `RECOVERING | STILL_DISTRESSED | UNCLEAR | NEW_CRISIS`

`NEW_CRISIS` → `_route_after_safety` routes to `crisis_response` even when `is_safe=True`.

### 3.4 Clinical Flags

Set in `safety_check_node`. Carried forward across turns as a set union (flags do not reset unless explicitly cleared). Cross-session eligible flags are persisted via `output_gate` → `memory/postgres_repository.write_persisted_clinical_flags`. At turn start, persisted flags are seeded from `therapeutic_profile.persisted_clinical_flags`.

Clinical flag categories detected by `clinical_flag_patterns.json`:
- `substance_use`, `trauma_indicator`, `eating_concern`, `medication_mention`, `domestic_situation`

Computed flag: `escalating_distress` — set when the last 3 turns of `distress_trajectory` are all ≥ 6, unless an active skill is running AND current engagement ≥ 5 (therapeutically expected high intensity during skill work does not trigger this flag).

Within-session behaviour: once a flag is set, it does not clear for the rest of the session (`flag_immutable_within_session: true` in `flag_lifecycle_config.json`).

Cross-session persistence: the infrastructure is built but currently **disabled** — all 5 flag types are set to `false` in `flag_lifecycle_config.json`. No clinical flags currently carry across sessions. Enabling requires flipping values in the config. See §9.4 for full detail.

Which flags persist cross-session is controlled by `rules/data/flag_lifecycle_config.json` (`cross_session_persistence` dict).

### 3.5 Post-Crisis State Machine

```
"none"  →[crisis_response fires]→  "monitoring"
"monitoring"  →[post_crisis_check_in skill_complete=True OR L1 exit fires]→  "resolved"
```

Step IDs for `post_crisis_check_in`: `acknowledge_and_check` → `bridge_or_close` (confirmed from skill JSON).

In `"monitoring"` state:
- S7 runs on every turn
- `skill_select_node` auto-selects `post_crisis_check_in` (bypasses keyword and semantic matching)
- `_route_after_intent` forces to `skill_select` regardless of confidence
- `crisis_occurred` session flag stays active (L5 heightened-sensitivity injection)
- `re_escalation_within_monitoring` set to True if `_crisis_response_node` fires again while already monitoring

In `"resolved"` state:
- S7 does not fire
- Normal skill matching resumes
- L5 `crisis_occurred` injection stays on for the session duration

Staleness reset: after a 4-hour gap (`_SKILL_STALE_HOURS`), `crisis_state` is reset to `"none"` at session resume (state machine position is not preserved across long gaps; `clinical_flags` are NOT cleared).

---

## 4. Intent Classification

`nodes/intent_route.py`. Uses `get_classifier()` LLM with `resilient_invoke` + `get_fallback_classifier()`.

**Intent categories:**

| Intent | Description |
|---|---|
| `skill_continuation` | Responding to an active skill step |
| `new_skill` | Specific symptom/pattern with enough context for a structured technique |
| `general_chat` | Greeting, small talk, brief general affect without specific symptoms |
| `crisis` | Explicit harm language that safety_check may have missed |
| `info_request` | Factual question about mental health |
| `exit_skill` | Explicit request to stop current skill |
| `scope_refusal` | Diagnosis, medication, or clinical assessment requests |
| `jailbreak` | Attempts to override persona or elicit prohibited outputs |

Also returns: `secondary_intent` (blended intent), `emotional_intensity` (1–10), `engagement` (1–10), `intent_confidence` (0.0–1.0).

**SPOF warning:** The `general_chat` definition is the sole gate preventing bare emotional words ("stressed", "anxious", "depressed", "I feel sad") from reaching `skill_select`, where they score above `SEMANTIC_THRESHOLD` and activate psychoeducation skills. Verified scores (2026-05-27): stressed=0.5765, anxious=0.5703, depressed=0.5467. Guard test: `uv run pytest tests/test_nodes.py -k "bare_emotional_words" -m "slow"`.

---

## 5. Skill System

### 5.1 Registry

`skill_ids.py`. **20 skills as of 2026-05-27:**

```
cbt_thought_record       grounding_5_4_3_2_1      sleep_hygiene
post_crisis_check_in     box_breathing             mood_check_in
behavioral_activation    worry_time                mi_readiness_ruler
stop_technique           progressive_muscle_relaxation  safe_place_visualization
dbt_tipp                 psychoed_anxiety          psychoed_depression
psychoed_stress          values_clarification      assertive_communication
self_compassion_break    mindfulness_body_scan
```

`post_crisis_check_in` is exclusively auto-selected via `post_crisis_auto_select`; it has empty `target_presentations` and empty `semantic_description`.

### 5.2 Matching

`nodes/skill_select.py`. Two-tier:

**Tier 1 — Keyword:** Iterates `skill.target_presentations` in registry order. First match wins. Synchronous, deterministic. Returns `skill_match_method="keyword"`.

**Tier 2 — Semantic (BGE-M3):** Cosine similarity of user message against all skills' `semantic_description` embeddings. Run in thread with 10s timeout (`EMBEDDING_TIMEOUT_SECONDS`). Threshold: `SEMANTIC_THRESHOLD = 0.459`. Returns `skill_match_method="semantic"` and `semantic_score`.

Recalibrate after any `semantic_description` edit: `uv run python scripts/calibrate_threshold.py`.

### 5.3 Skill Schema

`skills/schema.py`. Pydantic models: `Skill`, `SkillStep`, `StepPolicyRule`, `StepPolicyCondition`.

**Skill-level fields:**

| Field | Used at runtime? | How |
|---|---|---|
| `skill_id` | Yes | Registry key, routing |
| `skill_name` | Yes | Injected into L3 prompt |
| `skill_type` | STORED_ONLY | Validated, not used in routing |
| `evidence_base` | STORED_ONLY | Validated, not injected |
| `self_evolution` | STORED_ONLY | Always "manual_only" |
| `target_presentations` | Yes | Tier 1 keyword matching |
| `semantic_description` | Yes | Tier 2 BGE-M3 embedding |
| `steps` | Yes | Step instruction execution |
| `step_policy` | Yes | Dynamic step branching, escalation |
| `escalation_matrix.L1` | Yes | L1 exit step instruction |
| `escalation_matrix.L2–L4` | STORED_ONLY | Validated, not read at runtime |
| `cultural_overrides` | Yes | Injected into L3 system prompt (200-word budget) |

**SkillStep fields:**

| Field | Used at runtime? | How |
|---|---|---|
| `step_id` | Yes | Navigation |
| `goal` | Yes | L3 `{step_goal}` |
| `technique` | Yes | L3 `{technique_name}` |
| `technique_description` | Yes | L3 `{technique_description}` (optional) |
| `tone` | Yes | L3 `{tone_instruction}` |
| `examples` | Yes | L3 `{few_shot_block}`, up to 2; Arabic example prioritised for `lang=ar` |
| `contraindications` | Yes | L3 `{contraindication_block}` |
| `completion_criteria` | PARTIAL | LLM evaluator reads this for `_LLM_CRITERIA_SKILLS`; word-count heuristic used for all others |

**`_LLM_CRITERIA_SKILLS`:** `post_crisis_check_in`, `cbt_thought_record`, `behavioral_activation`, `assertive_communication`.

**StepPolicyRule fields:** `condition` (signal, operator, value, step, for_turns), `action`, `instruction`, `next_step_id`.

### 5.4 Schema Conformance Registry

`skills/conformance.py`. Declares which fields are USED / PARTIAL / STORED_ONLY. Logged at startup. Accessible at `GET /health/schema-conformance`. Summary as of 2026-05-30: 7 USED, 1 PARTIAL, 6 STORED_ONLY, 14 total.

---

## 6. Knowledge Retrieval (Node: `knowledge_retrieve`)

`nodes/knowledge_retrieve.py`. Fires when `primary_intent == "info_request"` and `active_skill_id is None`.

**Two separate knowledge paths — don't confuse them:**

| Path | Trigger | Node | State fields set |
|---|---|---|---|
| Node path | `info_request` intent, no active skill → `skill_select` → `knowledge_retrieve` | `knowledge_retrieve` (graph node) | `knowledge_passages`, `knowledge_abstain`, `knowledge_source="node_6"` |
| Tool path | LLM in `freeflow_respond` calls `knowledge_lookup` tool mid-response | Inside `freeflow_respond` (not a node transition) | Passages injected into L4 block inline; `knowledge_source` reflects the tool call |

Both use `PostgresKnowledgeRepository` and the same pgvector index. The difference is _when_ retrieval fires: the node path fires before any response generation (the passages are available to the LLM when it writes its response); the tool path fires when the LLM decides mid-response that it needs more information.

Uses `PostgresKnowledgeRepository` (asyncpg pool). `retrieve(query, language="en", top_k=5)`. Returns `knowledge_passages` (list of `{text, source_id, citation, relevance_score}`) and `knowledge_abstain` flag.

**Hybrid retrieval — Reciprocal Rank Fusion (RRF):**
1. Vector search: BGE-M3 embedding of query, cosine distance (`<=>` operator, pgvector), top `top_k * 4` results
2. Full-text search: PostgreSQL `ts_rank_cd(chunk_tsv, plainto_tsquery('english', query))`, top `top_k * 4` results
3. RRF fusion: `score = 1/(k + vec_rank) + 1/(k + txt_rank)`, `k=60` (standard literature default)
4. Final: top `top_k` (default: 5) by RRF score

`KNOWLEDGE_ABSTAIN_THRESHOLD = 0.0` — passages with `rrf_score <= 0` are excluded; abstain when no passages remain. TODO (pre-production): BGE-reranker-v2-m3 reranking pass after RRF.

**Corpus:** `data/knowledge_corpus/en/` contains 30 source article JSON files. Each article has `article_id, language, title, source_url, citation, content, is_crisis_content` fields. Chunks are created during ingestion (not stored in the source files). The Gitex sprint audit (2026-05-27) reported 137 chunks ingested into the `knowledge_articles` Postgres table.

After `knowledge_retrieve`, routing always goes to `freeflow_respond`, which uses the passages in the L4 knowledge block of the prompt.

---

## 7. Freeflow Response & Prompt Composition

`nodes/freeflow_respond.py`, `prompts/composer.py`.

### 7.1 Six Prompt Layers

`compose_prompt()` returns `(system_str, user_str, prompt_layers)`. System role and user role are assembled separately.

**System role** (in order):
- **L0** (`L0_persona.json`): Sage persona — always included
- **Global cultural rules** (`rules/data/cultural/`): Rules engine injection, capped at 250 words, priority-sorted
- **Skill cultural_overrides**: `SKILL-SPECIFIC CULTURAL CONTEXT` block — only when `active_skill_id` set AND the skill has non-empty `cultural_overrides`. Cap: 200 words. If the block exceeds 200 words, it is **skipped entirely** (not truncated) and a warning is logged.
- **Prompt injection / clinical adaptation**: Rules engine from `rules/data/prompt_injection/`, labelled "SUPPORT ADAPTATIONS"

**User role** (in order):
- **L1** (`L1_history.json`): Last 8 turns (default; `tmpl.window_size or 8`), word-budget constrained (450w with active skill/knowledge, 600w freeflow; reduced by cultural_override word count)
- **L2** (`L2_intents/`): Intent-specific framing — always included
- **L5** (`L5_user_context.json`): Clinical flags + cross-session therapeutic profile summary
- Inline injections: `third_party_crisis` block, `post_crisis_context` block (includes `s7_result`), `stale_skill_context` block
- **L3** (`L3_skill_wrapper.json`): Full templated skill step block when `executed_step_id` matches a step; falls back to plain `SKILL INSTRUCTION:` on escalation or rule override (layer tag: `"L3_skill_wrapper"` vs `"skill_instruction"` vs `"skill_instruction_override"`)
- **L4** (`L4_knowledge.json`): Knowledge passages (when `knowledge_passages` non-empty or `knowledge_abstain=True`)
- `USER:` message — always last; `[CORRECTION]:` block appended when `banned_opener_correction` is set

**Total word budget**: 1100 words. When exceeded, L1 history is shrunk to half-window first.

Templates live in `prompts/templates/`. Loaded via `prompts/loader.py`, composed per-turn by `prompts/composer.py`.

### 7.2 Prior Context Retrieval (deterministic, not LLM-bound)

`freeflow_respond._get_prior_context()` calls `check_user_history.retrieve_prior_context()` directly — this is **not** an LLM-bound tool. It always fires when `user_id` is present (architecture deviation from v7 §6.5.3, which defined it as an optional tool call; deterministic pre-retrieval is safer in a clinical system).

- Embeds the current message with BGE-M3, searches `PostgresMemoryRepository.search_session_summaries` for relevant prior sessions
- Similarity threshold: `_SIMILARITY_THRESHOLD = 0.4774` (calibrated 2026-05-24, gap=0.0331)
- Excludes crisis summaries (`exclude_safety_levels=["crisis"]`)
- Caps returned text at 800 chars
- Returns up to 3 prior sessions; each prefixed: "In an earlier conversation, you mentioned"
- Appended to system_str after `compose_prompt`, tagged as `"prior_session_context"` in prompt_layers

### 7.3 LLM Tool Loop

`_invoke_with_tool_loop` binds LLM tools at invocation time (not graph construction), runs up to `MAX_ITERATIONS = 5` cycles. If the loop exhausts iterations without a text response, it falls back to `resilient_invoke` on the original 2-message prompt.

Three tools are bound conditionally:

| Tool | File | Condition | Description |
|---|---|---|---|
| `knowledge_lookup` | `nodes/tools/knowledge_lookup.py` | Always bound | LLM-invoked RAG query against knowledge corpus mid-response |
| `flag_for_review` | `nodes/tools/flag_for_review.py` | user_id + session_id + DB pool present | LLM flags session for clinician review queue |
| `record_observation` | `nodes/tools/record_observation.py` | user_id + session_id + DB pool present | LLM records a structured clinical observation to profile |

`knowledge_source` is set to `"tool_lookup"` in state when `knowledge_lookup` fires (distinguishing from the `"node_6"` path).

### 7.4 LLM

`get_responder()` (primary) + `get_fallback_responder()` (fallback) via `resilient_invoke`.

---

## 8. Output Gate

`nodes/output_gate.py`.

### 8.1 Cultural Output Validation

`rules_engine.evaluate("cultural_output", {response_text, message_en, clinical_flags})`. Rule categories: `family_framing.json`, `general_cultural.json`, `religious_mirroring.json`, `substance_language.json`, `wellness_identity.json`.

Identity substitution (CUO-ID-001): if a `substitute` action fires, the full original response text is written to the restricted `identity_substitution_audit` Postgres table (RLS: DPO + clinician_admin only). The main audit log records only `sha256[:16]` of the original. `identity_substitution_rule_id` and `original_response_hash` returned in state.

### 8.2 Banned Opener Detection

Six patterns detected via regex at start of response (case-insensitive):
- "it sounds like", "that sounds (tough/hard/...)", "it seems like"
- "i can hear (that/how/the)", "i can see (that/how)", "it looks like"

First detection: routes back to `freeflow_respond` for one retry with correction instruction.
After retry: substitutes `_VETTED_FALLBACK_RESPONSE`. Path gets `output_gate_fallback_substituted` marker.

### 8.3 Format Violations

Detected (logged, not blocked): em dash (—), bold markdown (**text**), emoji (Unicode blocks U+1F300–U+1F9FF, U+2600–U+27BF, U+1FA00–U+1FAFF).

### 8.4 Translation

If `detected_language == "ar"`: `async_translate_to_arabic(response_en)` via `get_translator()` LLM.

### 8.5 Audit Outputs (All Fire Asynchronously via `asyncio.create_task`)

All audit writes are fire-and-forget (`asyncio.create_task`) — they do not block the response from being returned to the caller. Failures are logged as warnings; they do not affect the user-facing response.

**Two separate audit stores:**

| Write | Destination | Credentials | Description |
|---|---|---|---|
| `write_session_audit(...)` | Supabase REST API (`/rest/v1/session_audit`) | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Per-turn audit row; upsert with merge-duplicates so retry and fallback paths overwrite with the complete path |
| `write_identity_substitution_audit(...)` | Supabase REST API (`/rest/v1/identity_substitution_audit`) | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Full original response text for PDPL right-to-challenge; RLS permits DPO and clinician_admin only |
| `PostgresNotifier.notify_review_required(...)` | asyncpg pool → `clinician_review_queue` + `pg_notify` | `DATABASE_URL` | Real-time clinician alert when crisis_flags or clinical_flags are non-empty |
| Session summary persist | asyncpg pool → `session_summaries` with pgvector embedding | `DATABASE_URL` | Every 10th turn (`turn_count % 10 == 0`) |

**Supabase is the POC audit store** (temporary). Production will move to secure cloud infrastructure. If `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` are unset, `write_session_audit` and `write_identity_substitution_audit` return silently — no error, no write.

`crisis_response` also calls `write_session_audit` directly; output_gate is bypassed for crisis turns.

---

## 9. Memory and Persistence

SageAI has two kinds of memory: **short-term** (within a session, carried turn-to-turn via LangGraph checkpointing) and **long-term** (across sessions, in two separate Postgres stores). The system is also deliberately selective about what it remembers and how it recalls it.

---

### 9.1 Short-term Memory — LangGraph Checkpoint

`memory/checkpointer.py`, wired in `server.py` as `AsyncPostgresSaver` (LangGraph's `langgraph.checkpoint.postgres.aio`).

**Mechanism:** Session state is keyed by `thread_id = session_id`. After every turn, LangGraph writes the full `SageState` to a Postgres checkpoint. On the next turn, it loads it back before the graph runs. `_build_state()` only sets per-turn input signals; everything else comes from the checkpoint.

**What short-term memory holds:**

| Field | What it tracks |
|---|---|
| `conversation_history` | Full turn-by-turn dialogue (last 8 turns in prompt; older turns in summary block) |
| `conversation_summary` | LLM-generated rolling summary — generated at every 10th turn, carries forward. 2–3 sentences: life situation, emotional themes, daily routines, commitments made |
| `active_skill_id` / `active_step_id` | Which technique is in progress and which step is next |
| `executed_step_id` / `prev_step_id` | Step executed this turn / prior turn (continuation detection) |
| `crisis_state` | State machine position: "none" / "monitoring" / "resolved" |
| `clinical_flags` | Accumulated clinical flags for this session. Immutable within session (`flag_immutable_within_session: true`) — once set, never cleared until session ends |
| `distress_trajectory` | Rolling window of last 4 `emotional_intensity` scores |
| `engagement_trajectory` | Rolling window of last 4 `engagement` scores |
| `resistance_history` | Rolling 3-turn buffer of resistance scores |
| `stale_skill_id` | Technique parked after a 4h+ session gap; triggers re-entry prompt on return |
| `last_turn_at` | UTC ISO timestamp of last completed turn (used for gap detection) |
| `turn_count` | Turn counter (triggers session summary at `% 10`) |

**Fallback:** When `DATABASE_URL` is unset, `build_graph(checkpointer=None)` runs the graph stateless — none of the above persists between requests. A startup warning is emitted.

**Infrastructure:** `server.py` bootstraps two separate pools:
- `saver_pool` (psycopg `AsyncConnectionPool`) — for `AsyncPostgresSaver` (LangGraph checkpointing)
- `asyncpg_pool` (`asyncpg`) — for `PostgresMemoryRepository` (all other memory operations)

---

### 9.2 Long-term Memory — Therapeutic Profile

Table: `public.user_therapeutic_profiles`. One row per user.

**What it holds:**

| Column | Type | Description |
|---|---|---|
| `effective_techniques` | text[] | Technique names the user said helped |
| `ineffective_techniques` | text[] | Approaches the user resisted or said didn't work |
| `distortion_patterns` | text[] | Cognitive distortion patterns observed |
| `disclosed_concerns` | text[] | Life areas / concerns the user mentioned |
| `communication_style` | text | One sentence on how this user communicates |
| `cultural_preferences` | JSONB | `{religious_framing: bool, family_context: bool, gender_address: str\|null}` |
| `mood_trajectory` | JSONB | `[{session: N, mood_score: N}]`, last 20 entries |
| `total_skills_completed` | int | Cumulative count of skills fully completed |
| `session_count` | int | Number of sessions extracted so far |
| `last_extraction_turn` | int | Turn number of last extraction (prevents re-processing the same turns) |
| `observations` | JSONB | Structured clinical observations (from `record_observation` LLM tool) |
| `persisted_clinical_flags` | JSONB | Clinical flags eligible for cross-session persistence (see §9.4) |
| `last_updated_at` | timestamp | Auto-set on every upsert |

**Two write paths — both write to the same profile row:**

#### Write Path 1 — Post-session batch extraction (`POST /extract-profile`)

Called by Next.js after a session ends. Internally:
1. Fetches the LangGraph checkpoint to get `conversation_history` and `turn_count`
2. Guards: skips if fewer than 5 new turns since `last_extraction_turn`
3. Passes the delta turns (since last extraction) to `profile_extractor.extract_session_profile()`
4. Classifier LLM reads the conversation with this exact instruction: *"Extract only what was explicitly stated."* Returns JSON with these 8 keys:

| Key | Type | What the LLM extracts |
|---|---|---|
| `effective_techniques` | list[str] | Technique names the user said helped |
| `ineffective_techniques` | list[str] | Techniques the user resisted or said didn't work |
| `distortion_patterns` | list[str] | Cognitive distortion patterns observed |
| `disclosed_concerns` | list[str] | Life areas or concerns the user mentioned |
| `communication_style` | str | One sentence on how this user communicates |
| `cultural_preferences` | object | `{religious_framing: bool, family_context: bool, gender_address: str\|null}` |
| `mood_score` | int (1–5) | End-of-session mood estimate (1=very low, 5=good) |
| `skills_completed` | int | Count of skills fully completed in this excerpt |

5. Merges with existing profile: technique lists are set-union, mood_trajectory appends (capped at 20), session_count increments, communication_style and cultural_preferences overwrite
6. Writes via `upsert_therapeutic_profile(user_id, merged_profile, session_id)`

#### Write Path 2 — In-session real-time observations (`record_observation` tool)

`nodes/tools/record_observation.py`. An LLM-callable tool available to `freeflow_respond` on every turn (when `user_id`, `session_id`, and DB pool are present). The LLM calls it the moment it notices something worth persisting — capturing events a post-session extractor would miss because they're momentary.

The LLM provides:

| Parameter | Values | Meaning |
|---|---|---|
| `observation` | str (1–2 sentences) | Factual description of what was observed |
| `observation_type` | `insight` / `progress` / `agency` / `context_update` / `concern` | Category |
| `confidence` | `high` / `medium` / `low` | How certain the LLM is |

Observation types:
- `insight` — user identified their own cognitive distortion without prompting
- `progress` — a technique worked or mood shifted
- `agency` — user set a goal or took initiative
- `context_update` — a life circumstance changed
- `concern` — something the LLM noticed that warrants attention

Stored in `observations` (JSONB array, capped at last 50), with `recorded_at` UTC timestamp. Writes directly to the profile row via `upsert_therapeutic_profile` mid-session — the updated observations are immediately available on the next turn's profile load.

**Low-confidence observations additionally trigger clinician review** (`confidence == "low"` → `notify_review_required` with `source="llm_flag_for_review"`).

**PDPL audit trail:** Every `upsert_therapeutic_profile` call (both paths) first inserts a full JSONB snapshot into `public.therapeutic_profile_history` tagged with `session_id` and `extraction_source='llm_extraction'`. Every profile change is reversible and attributable.

#### What is NOT currently injected into the prompt

`_build_cross_session_block` (in `prompts/composer.py`) reads these fields from the profile:
`effective_techniques`, `ineffective_techniques`, `distortion_patterns`, `disclosed_concerns`, `communication_style`, `cultural_preferences` (religious_framing, family_context).

It does **not** read `observations`. Observations are stored in the DB and visible in the profile row, but the LLM does not see its own past observations in future sessions. This is a known gap — the injection path is not yet built.

**How it's used at runtime:**
- Profile loaded fresh from DB in `server.py` at the start of every `/chat` request
- Injected into the L5 prompt block via `_build_cross_session_block` and `_build_l5_user_context_block` — effective/ineffective techniques framed as "Techniques that have helped" / "Approaches to avoid", distortion patterns as "Common thought patterns", concerns as "Life areas shared", communication style, religious and family context preferences
- Read by `safety_check_node` to seed `clinical_flags` from `profile.persisted_clinical_flags` at turn start

---

### 9.3 Long-term Memory — Session Summaries

Table: `public.session_summaries`. One row per session (UNIQUE on `session_id`).

**What it holds:**

| Column | Type | Description |
|---|---|---|
| `session_id` | UUID | Unique per session |
| `user_id` | UUID | Owner |
| `summary_text` | text | 2–3 sentence LLM summary of the session |
| `embedding` | vector(1024) | BGE-M3 embedding of summary_text, L2-normalised |
| `safety_level` | text | "normal" / "clinical" / "crisis" |
| `skills_used` | text[] | Skill IDs active during this session |
| `mood_score` | float | End-of-session mood estimate (1–5) |
| `created_at` | timestamp | |

**How summaries are generated:**

`prompts/summarizer.summarise_history()` using the classifier LLM. Prompt instructs extraction of: (1) key life situation described, (2) main emotional themes, (3) anything shared about daily life/routines, (4) commitments/next steps the assistant offered. Explicitly told: be factual, no advice, no identifying details (no names/phone numbers).

Fires in `output_gate._persist_session_summary()` at every `turn_count % 10 == 0`. Written via DELETE + INSERT (UNIQUE constraint on `session_id` prevents duplicates; earlier writes for the same session are replaced).

**How they're retrieved:**

`check_user_history.retrieve_prior_context()` — called deterministically by `freeflow_respond` every turn when `user_id` is present. NOT an LLM-bound tool (architecture deviation from v7 §6.5.3; deterministic pre-retrieval avoids the risk of the LLM skipping the context in a clinical setting).

Retrieval parameters:
- Cosine similarity via pgvector (`1 - (embedding <=> query_embedding)`)
- BGE-M3 embeds the current user message as the query
- **Crisis summaries excluded** (`exclude_safety_levels=["crisis"]`): sessions that ended in crisis are never surfaced as casual recall
- Similarity threshold: `0.4774` (calibrated 2026-05-24, gap=0.0331)
- Top-k: 3 prior sessions
- Max 800 characters returned
- Each result prefixed: "In an earlier conversation, you mentioned..."

---

### 9.4 Clinical Flag Cross-Session Persistence — Infrastructure Ready, Currently Disabled

**What the design intends:** Clinical flags like `substance_use` or `trauma_indicator` detected in one session should persist to the next so the system doesn't lose that clinical context. `domestic_situation` is intentionally excluded (it's a situational safety concern, not a longitudinal clinical signal that should colour future sessions without re-disclosure).

**What the code actually does today:**

`flag_lifecycle_config.json` is the switch:
```json
{
  "cross_session_persistence": {
    "substance_use": false,
    "trauma_indicator": false,
    "eating_concern": false,
    "medication_mention": false,
    "domestic_situation": false
  },
  "flag_immutable_within_session": true
}
```

All 5 are set to `false`. `output_gate._write_persisted_clinical_flags()` filters to only flags where `_CROSS_SESSION_FLAGS.get(flag, False)` is True — which is currently nothing. Nothing is written to `persisted_clinical_flags`. Nothing carries across sessions.

The infrastructure is complete: the column exists (`migration 001`), the read/write methods exist, `safety_check_node` seeds flags from the profile at turn start. Enabling cross-session persistence for any flag is a one-line config change per flag type.

**What is active today:** `flag_immutable_within_session: true` — once a clinical flag fires within a session, it persists for the rest of that session. It just doesn't cross to the next one.

---

### 9.5 Clinician Review Queue

`memory/notification.PostgresNotifier`. Table: `public.clinician_review_queue`.

Three distinct triggers write to this queue:

**Trigger 1 — Deterministic rules (`output_gate`):** Fires when `crisis_flags` or `clinical_flags` are non-empty after a turn. Source: `"layer1_safety"`. Severity: `"high"` (crisis) or `"medium"` (clinical-only).

**Trigger 2 — LLM tool (`flag_for_review`):** `nodes/tools/flag_for_review.py`. A tool available to `freeflow_respond` when the LLM perceives cumulative distress, implicit hopelessness, or ambiguous risk that Layer 1 didn't catch. Source: `"llm_flag_for_review"`. The LLM provides:

| Parameter | Values | Meaning |
|---|---|---|
| `reason` | str | What the LLM noticed (e.g. "cumulative hopelessness over 3 turns") |
| `severity` | `low` / `medium` / `high` | Urgency: low = daily batch, medium/high = within 4 hours |
| `turn_context` | str (optional) | 1–2 sentence excerpt showing the pattern |
| `evidence_turns` | list[int] (optional) | Turn numbers that support the concern |

**Trigger 3 — Low-confidence observations (`record_observation` tool):** When `record_observation` is called with `confidence="low"`, it additionally fires `notify_review_required` alongside writing to the profile.

All three writes go to the same `clinician_review_queue` table via `PostgresNotifier` (asyncpg pool) + `pg_notify('clinician_review', payload)`. ON CONFLICT on `session_id` appends to `flags_timeline` rather than overwriting — clinicians see how flags evolved across the session (added `migration 002`).

---

### 9.6 Database Tables Summary

| Table | Store | Written by | Read by |
|---|---|---|---|
| LangGraph checkpoint (4 tables) | Postgres (psycopg pool) | LangGraph `AsyncPostgresSaver` | `AsyncPostgresSaver` |
| `user_therapeutic_profiles` | Postgres (asyncpg pool) | `POST /extract-profile` | `server.py` at every `/chat` turn |
| `therapeutic_profile_history` | Postgres (asyncpg pool) | `upsert_therapeutic_profile` | DPO / clinician audit only |
| `session_summaries` | Postgres (asyncpg pool) | `output_gate` (every 10th turn) | `freeflow_respond` (prior context) |
| `clinician_review_queue` | Postgres (asyncpg pool) | `output_gate` (flag detection) | Clinician dashboard (pg_notify) |
| `session_audit` | Supabase REST (POC) | `output_gate` + `crisis_response` | Clinical audit, PDPL compliance |
| `identity_substitution_audit` | Supabase REST (POC) | `output_gate` (CUO-ID-001 only) | DPO + clinician_admin (RLS restricted) |

---

## 10. LLM Provider and Resilience

### 10.1 LLM Singletons

`llm.py`. All LLM instances are `@lru_cache` singletons. Provider: OpenRouter (`https://openrouter.ai/api/v1`) via `langchain_openai.ChatOpenAI`.

| Function | Default model | Temperature | Max tokens |
|---|---|---|---|
| `get_classifier()` | `openai/gpt-4o-mini` | 0 | 512 |
| `get_responder()` | `openai/gpt-4o` | 0.7 | 1024 |
| `get_translator()` | `openai/gpt-4o-mini` | 0 | 1024 |
| `get_fallback_responder()` | `openai/gpt-4o` | 0.7 | 1024 |
| `get_fallback_classifier()` | `openai/gpt-4o-mini` | 0 | 512 |

All models are overridable via env vars (`SAGE_CLASSIFIER_MODEL`, `SAGE_RESPONDER_MODEL`, `SAGE_TRANSLATOR_MODEL`, etc.).

`reset_singletons()` clears the cache. Use in test teardown to prevent mock leakage.

### 10.2 Resilience Layer

`resilience/__init__.py`. `resilient_invoke()` wraps every LLM call.

| Parameter | Value |
|---|---|
| `LLM_TIMEOUT_SECONDS` | 30.0 |
| `LLM_MAX_RETRIES` | 2 |
| `EMBEDDING_TIMEOUT_SECONDS` | 10.0 |
| `CIRCUIT_BREAKER_THRESHOLD` | 5 consecutive failures |
| `CIRCUIT_BREAKER_RESET_SECONDS` | 60.0 |
| Backoff | Exponential with ±20% jitter, capped at 8s |
| Retryable codes | HTTP 429, 502, 503, 504; `ConnectError`; `TimeoutError` |

Failure path: primary model fails → `fallback_llm` (if provided) → `get_fallback_response(node, language)` from `resilience/fallbacks.json`. Never raises.

`resilient_stream()` wraps `astream()` with the same timeout/retry/circuit-breaker logic. First-chunk timeout is enforced; subsequent chunks are bounded by the caller's outer graph timeout.

---

## 11. API Surface

`server.py`. FastAPI application.

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/chat` | HMAC `X-Sage-Api-Key` | Main chat turn |
| `POST` | `/extract-profile` | HMAC | Extract therapeutic profile from session history (LLM) |
| `POST` | `/name-session` | HMAC | Generate session name from first message (LLM) |
| `GET` | `/health/schema-conformance` | None | Schema conformance report |

### `/chat` Request

```json
{
  "messages": [{"role": "user", "content": "..."}],
  "session_id": "uuid",
  "user_id": "uuid | null"
}
```

No ferry fields — all cross-turn state comes from the LangGraph checkpoint.

### `/chat` Response

Streaming (`text/plain; charset=utf-8`). Body: `[[CRISIS_DETECTED]]\n` prefix (when `is_safe=False`) + word-by-word response. Response headers carry metadata:

`X-Sage-Node-Path`, `X-Sage-Model`, `X-Sage-Skill-Id`, `X-Sage-Step-Id`, `X-Sage-Active-Step-Id`, `X-Sage-Gate-Path`, `X-Sage-Crisis-Flags`, `X-Sage-Clinical-Flags`, `X-Sage-Emotional-Intensity`, `X-Sage-Crisis-State`, `X-Sage-Distress-Trajectory`, `X-Sage-Engagement-Trajectory`, `X-Sage-Conversation-Summary`, `X-Sage-Intent`, `X-Sage-Secondary-Intent`, `X-Sage-Semantic-Score`, `X-Sage-Prompt-Layers`, `X-Sage-Token-Usage`, `X-Sage-Turn-Number`.

### Authentication

HMAC constant-time comparison (`hmac.compare_digest`) against `SAGE_API_KEY` env var. If `SAGE_API_KEY` is unset, all requests pass through (dev mode).

### CORS

Origins from `CORS_ALLOWED_ORIGINS` env var (comma-separated). Default: `http://localhost:3000`. POST only.

---

## 12. SageState Fields

Full `TypedDict` definition in `state.py`.

**Per-turn input (set by `_build_state`, reset each turn):**
`raw_message`, `message_en`, `detected_language`, `is_safe`, `crisis_flags`, `third_party_crisis`, `primary_intent`, `secondary_intent`, `intent_confidence`, `emotional_intensity`, `engagement`, `executed_step_id`, `step_instruction`, `rule_fired`, `escalation_triggered`, `gate_path`, `response_en`, `response`, `path`, `code_switching`, `s7_result`, `s7_method`, `skill_match_method`, `semantic_score`, `prompt_layers`, `token_usage`, `cultural_output_violations`, `new_clinical_flags_turn`, `resistance_score`, `knowledge_source`, `knowledge_abstain`, `knowledge_passages`, `session_id`, `user_id`, `banned_opener_retry_count`, `banned_opener_correction`, `banned_opener_fallback_used`

**Persistent via checkpoint (NOT set by `_build_state`):**
`conversation_history`, `crisis_state`, `active_skill_id`, `active_step_id`, `clinical_flags`, `distress_trajectory`, `engagement_trajectory`, `conversation_summary`, `turn_count`, `therapeutic_profile`, `resistance_history`, `prev_step_id`, `stale_skill_id`, `last_turn_at`, `re_escalation_within_monitoring`

**Written by nodes, returned in final result:**
`identity_substitution_rule_id`, `original_response_hash`, `original_response_text`, `banned_opener_violation`, `s7_result`, `s7_method`, `turn_number`

---

## 13. Configuration and Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | Postgres DSN. Required for checkpointing and memory. If unset, runs stateless. |
| `SAGE_API_KEY` | — | HMAC key for API auth. If unset, auth is bypassed. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins. |
| `OPENROUTER_API_KEY` | — | OpenRouter API key. Required for all LLM calls. |
| `SAGE_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | Model for intent_route, safety S7, criteria_eval |
| `SAGE_RESPONDER_MODEL` | `openai/gpt-4o` | Model for freeflow_respond, skill step responses |
| `SAGE_TRANSLATOR_MODEL` | `openai/gpt-4o-mini` | Model for Arabic ↔ English translation |
| `SAGE_FALLBACK_RESPONDER_MODEL` | `openai/gpt-4o` | Fallback responder |
| `SAGE_FALLBACK_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | Fallback classifier |
| `SAGE_AUDIT_LOG` | `true` | Enable structured audit log in output_gate and crisis_response |
| `SAGE_WARMUP_BGE` | `1` | Set to `0` to skip BGE-M3 warmup at startup |
| `SUPABASE_URL` | — | Supabase project URL. Required for `write_session_audit` and `write_identity_substitution_audit`. POC audit store — temporary; production will use secure cloud infrastructure. |
| `SUPABASE_SERVICE_KEY` | — | Supabase service role key. Required alongside `SUPABASE_URL`. Both must be set for audit writes to fire. |

---

## 14. Database Migrations

Three SQL migration files in `migrations/`:

| File | Change |
|---|---|
| `001_add_persisted_clinical_flags.sql` | Adds `persisted_clinical_flags` column to `user_therapeutic_profiles` |
| `002_add_flags_timeline.sql` | Adds `flags_timeline` column to `clinician_review_queue` |
| `003_add_re_escalation_within_monitoring.sql` | Schema change for re-escalation tracking |

All three must be applied before Gitex demo.

---

## 15. Calibration Reference

| Threshold | Value | Calibration date | Script | Notes |
|---|---|---|---|---|
| `SEMANTIC_THRESHOLD` | 0.459 | 2026-05-27 (post audit-fix) | `scripts/calibrate_threshold.py` | Gap=0.0533 (cross-cluster). Re-run after any `semantic_description` edit. |
| `S3_THRESHOLD` | 0.8059 | 2026-05-26 | `scripts/calibrate_s3_threshold.py` | Gap=0.3234. Re-run after any `crisis_phrases.json` edit. |

---

## 16. Signal System — How Sage Reads the Room and Adapts

Three separate signals measure how the user is doing turn-by-turn. They are computed by different nodes, stored in state, and feed into multiple layers of the response. This section describes the full chain from measurement to effect.

---

### 16.1 The Three Signals

#### Emotional Intensity (1–10)

**Where measured:** `intent_route_node` (LLM classifier, every turn).
- 1 = calm
- 10 = extremely distressed

**How tracked:** `safety_check_node` appends the prior turn's score to `distress_trajectory` (rolling 4-turn window). Intensity is one turn lagged in the trajectory because `safety_check` runs before `intent_route`.

**Escalation trigger:** If the last 3 of 4 trajectory values are all ≥ 6, the `escalating_distress` clinical flag is set. Suppressed when a skill is active AND `engagement ≥ 5` (high intensity during active therapeutic work is clinically expected and should not trigger a distress alert).

#### Engagement (1–10)

**Where measured:** `intent_route_node` (LLM classifier, every turn, same call as intensity).
- 1 = one-word or dismissive
- 10 = elaborating, open, reflective

**How tracked:** `safety_check_node` appends to `engagement_trajectory` (rolling 4-turn window).

**Escalation trigger:** If the last 3 of 4 trajectory values are all ≤ 4, `engagement_declining` is True — this also sets the `escalating_distress` flag via the same path as high sustained intensity. Both sustained high distress and sustained low engagement produce the same flag name: they are treated as equivalent clinical signals.

#### Resistance (1–10)

**Where measured:** `skill_executor_node` only, when the active skill has resistance-based step_policy rules AND Phase 1 (deterministic rules) did not fire. Evaluated by the classifier LLM using a dedicated prompt.

- 1 = full engagement, cooperative
- 10 = complete refusal, active disengagement

**Prompt instruction:** *"Consider: reluctance, deflection, topic-changing, one-word replies, expressions of futility, or explicit refusal. In a Gulf Arab context, indirect refusal (e.g., changing subject, short answers, invoking busyness) carries equal weight to direct refusal."*

**How tracked:** `resistance_history` — rolling 3-turn buffer (capped at last 3 scores). This is the only signal that is NOT evaluated on every turn; it only runs when a skill is active and has resistance rules.

---

### 16.2 How the Signals Shape Responses

#### Effect 1 — L2 Intent Framing: intensity → guidance tier

`compose_prompt` computes `_intensity_guidance(intensity)` and injects it as `{intensity_guidance}` into L2 templates. Three tiers, with exact text:

| Intensity | Tier label | Text injected |
|---|---|---|
| 1–3 | Low | "The user's distress is mild. A lighter touch is appropriate." |
| 4–6 | Mid | "The user is moderately engaged. Be present and attentive." |
| 7–10 | High | "The user is significantly distressed. Name the specific thing they said, directly. Ask one focused question about it. Do NOT paraphrase or reflect back what they said. Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener. Do NOT offer guidance yet." |

**Which L2 intents receive this guidance block** (the others only get the raw `{intensity}/10` number):

| Intent | Gets guidance block? |
|---|---|
| `general_chat` | Yes |
| `info_request` | Yes |
| `new_skill` | Yes |
| `skill_continuation` | Yes |
| `crisis` | No — intensity shown as number only |
| `exit_skill` | No |
| `jailbreak` | No |
| `scope_refusal` | No |
| `low_confidence` | No |

The high-intensity guidance (tier 7–10) explicitly bans "It sounds like", "That sounds", "It seems like", and any reflective paraphrase opener — the same phrases that `output_gate` catches mechanically via regex. The L2 instruction is the primary enforcement; the output_gate banned opener check is a safety net if the LLM ignores it.

#### Effect 2 — L5 User Context: both intensity AND engagement shown as numbers

L5_user_context template content (v2.0.0):
```
CONTEXT ABOUT THIS USER: {flags_summary} Current emotional state: intensity {intensity}/10, engagement {engagement}/10.{distress_note}{cross_session_profile}
```

The LLM sees both signals as explicit numbers in every turn where L5 fires (i.e. when clinical flags or therapeutic profile data are present). When `escalating_distress` is in `clinical_flags`, `{distress_note}` appends: *"Distress has been elevated for multiple turns."*

#### Effect 3 — Step Policy: signals gate skill advancement

`skill_executor` enforces these step_policy thresholds (every skill must define all of them per authoring conventions):

| Signal | Condition | Action | Effect |
|---|---|---|---|
| `emotional_intensity` | > 7 | `validate_only` | No step advancement; LLM given a validating instruction for this turn only |
| `engagement` | < 3 for 3 turns | `check_in_micro` | Micro check-in instruction injected; holds at current step |
| `resistance` | > 6 for 3 turns | `offer_skill_switch_or_break` | Switch or break instruction; holds at current step |

The `for_turns` temporal logic for engagement uses `engagement_trajectory` (the 4-turn lagged window). The for_turns logic for resistance uses `resistance_history` (the rolling 3-turn buffer). For all other signals (including `emotional_intensity`), `for_turns` is ignored — the threshold evaluates the current turn only.

#### Effect 4 — L3 Skill Wrapper: step goal takes priority

The L3 template (v1.2.0) includes this instruction to the LLM:

> *"The step goal above takes priority over the user's conversational direction. Execute the technique even if the user shifts topic, expresses general progress, or comments on the exercise. Cooperative messages such as 'this is helping' or 'I am making progress' are acknowledgment, not completion — continue delivering the technique for this step."*

This means engagement signals and user commentary do NOT cause premature step advancement at the LLM level — step advancement is controlled by the criteria evaluator in `skill_executor`, not by the LLM's reading of user cooperativeness.

#### Effect 5 — Clinical Flag Elevation → L5 adaptation rules

When `escalating_distress` is in `clinical_flags`, it is injected into L5 via `_FLAG_DESCRIPTIONS`:
- *"This user's distress has been elevated across multiple turns."*

This causes the Rules Service's prompt injection layer (`rules/data/prompt_injection/`) to fire a corresponding adaptation. The LLM sees a concrete statement about multi-turn pattern, not just a current-turn score.

#### Effect 6 — Session Summary captures mood trajectory

`summarise_history()` generates the session summary, and `output_gate._persist_session_summary()` stores it with `mood_score` (from the profile extractor's 1–5 scale). The mood trajectory in `user_therapeutic_profiles.mood_trajectory` is `[{session: N, mood_score: N}]` capped at 20 sessions — a longitudinal record of how the user's mood at session end has changed over time. Not currently injected into the prompt, but available for clinician review and future use.

---

### 16.3 Signal Interaction Summary

```
Every turn:
  intent_route  →  emotional_intensity (1-10)
                →  engagement (1-10)

  safety_check  →  distress_trajectory  (4-turn window)
                →  engagement_trajectory (4-turn window)
                →  escalating_distress flag (if 3+ turns ≥6 OR 3+ turns ≤4)

  compose_prompt →  intensity_guidance tier → L2 template
                 →  intensity + engagement numbers → L5 template
                 →  distress_note if escalating_distress set

  output_gate   →  banned opener check (mechanically enforces high-intensity L2 guidance)

During skill execution (only):
  skill_executor →  resistance_score (1-10, LLM-evaluated, Gulf-aware)
               →  resistance_history (3-turn rolling buffer)
               →  step_policy evaluation: intensity>7, engagement<3 for 3t, resistance>6 for 3t
               →  step advance / hold / validate_only / check_in_micro / offer_switch
```

## 17. Known Gaps and Pending Items

| ID | Gap | Status | Notes |
|---|---|---|---|
| S2 | MARBERT Arabic crisis classifier | Not implemented | Architecture comment in `safety_check.py`. S3 provides semantic coverage; S2 adds dialectal Arabic coverage. |
| S3-AR | S3 on Arabic text | Not implemented | `check_s3` runs on `message_en` only. TODO comment in `safety_check.py` and `s3_semantic.py`. |
| BGE-cold | BGE-M3 cold-start in slow tests | P2 | First slow test fails with `embedding_timeout` on 16GB M4. Fix: session-scoped pre-warm fixture in conftest.py. |
| CUO-missing | Empty `cultural_overrides` in 4 skills | P2 | `box_breathing`, `mood_check_in`, `stop_technique`, `worry_time` have empty `cultural_overrides`. |
| Streaming | `freeflow_respond` uses `ainvoke`, not `astream` | By design for POC | Deferred post-POC (Option B). p95 latency = 9.6s. |
| FALLBACK | `_VETTED_FALLBACK_RESPONSE` pending clinical review | Placeholder | See `docs/superpowers/reviews/FALLBACK_RESPONSE_REVIEW.md`. |
