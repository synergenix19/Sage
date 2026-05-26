# sage-poc Codebase Audit
**Date:** 2026-05-26  
**Scope:** Complete validated audit — every claim verified against actual code, not comments  
**Method:** Full file reads of all nodes, rules engine, skills, prompts, memory, API, and test layers

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [LangGraph Architecture](#2-langgraph-architecture)
3. [LLM-Driven Components](#3-llm-driven-components)
4. [Deterministic Components](#4-deterministic-components)
5. [Safety System](#5-safety-system)
6. [Skill System](#6-skill-system)
7. [Memory and Knowledge Layer](#7-memory-and-knowledge-layer)
8. [API Surface](#8-api-surface)
9. [Language Handling](#9-language-handling)
10. [Resilience Layer](#10-resilience-layer)
11. [Prompt Composition](#11-prompt-composition)
12. [Test Coverage](#12-test-coverage)
13. [Confirmed Gaps and Dead Code](#13-confirmed-gaps-and-dead-code)

---

## 1. Project Structure

```
sage-poc/
├── server.py                        Entry point: FastAPI HTTP server
├── run.py                           Entry point: CLI REPL (dev/testing)
├── pyproject.toml                   Dependencies and build config
├── src/sage_poc/
│   ├── graph.py                     LangGraph topology + all routing functions
│   ├── state.py                     SageState TypedDict (single source of truth)
│   ├── config.py                    All env-var config with defaults
│   ├── language.py                  Language detection + translation
│   ├── llm.py                       ChatOpenAI factory functions
│   ├── knowledge.py                 Static 10-entry knowledge dict (POC)
│   ├── skill_ids.py                 Canonical SKILL_REGISTRY (13 skills)
│   ├── nodes/
│   │   ├── safety_check.py          Node 1: S1 lexical safety + trajectory
│   │   ├── intent_route.py          Node 2: LLM intent classifier
│   │   ├── skill_select.py          Node 3: keyword + semantic skill selection
│   │   ├── skill_executor.py        Node 4: deterministic step execution
│   │   ├── freeflow_respond.py      Node 5: LLM responder with tools
│   │   ├── output_gate.py           Node 6: format/cultural check + output
│   │   ├── low_confidence_respond.py LLM clarifier for ambiguous input
│   │   ├── post_crisis_classifier.py S7: post-crisis monitoring classifier
│   │   └── tools/
│   │       ├── knowledge_lookup.py  LLM tool wrapping static dict
│   │       ├── flag_for_review.py   LLM tool: writes to clinician queue
│   │       └── record_observation.py LLM tool: appends to therapeutic profile
│   ├── rules/
│   │   ├── engine.py                5-category stateless rules evaluator
│   │   ├── loader.py                JSON loader with Arabic regex lint
│   │   ├── normalize.py             normalize_text + normalize_arabic
│   │   └── data/safety/
│   │       ├── crisis_keywords.json         SK-EN-001, SK-AZ-001, SK-AR-001, SK-EN-003, SK-EN-004
│   │       ├── passive_si_patterns.json     SK-EN-002 v1.1.0, SK-AR-002, SK-AZ-002, SK-AR-003, SK-EN-005
│   │       ├── false_positive_exclusions.json FPE-EN-001, FPE-AR-001 (active); FPE-AR-002, FPE-EN-002, FPE-EN-003 (inactive)
│   │       ├── clinical_flag_patterns.json  CF-001 through CF-005
│   │       └── cultural_output_rules.json   Post-generation cultural checks
│   ├── skills/                      13 evidence-based skill JSON definitions
│   ├── prompts/
│   │   ├── composer.py              6-layer prompt assembly (L0–L5)
│   │   ├── loader.py                Template loader + caching
│   │   ├── summarizer.py            LLM history summarizer
│   │   └── templates/               L0–L5 JSON templates + intent variants
│   ├── memory/
│   │   ├── postgres_repository.py   All Postgres/pgvector operations
│   │   ├── embedding.py             BGE-M3 wrapper (delegates to skill_select)
│   │   ├── checkpointer.py          AsyncPostgresSaver setup
│   │   ├── notification.py          pg_notify + clinician_review_queue writer
│   │   ├── profile_extractor.py     LLM-based therapeutic profile extraction
│   │   └── check_user_history.py    pgvector prior-session retrieval
│   └── resilience/
│       ├── __init__.py              resilient_invoke, resilient_stream, circuit breaker
│       └── fallbacks.json           Pre-authored fallback response strings
└── tests/                           36 test files
```

### Key Dependencies (pyproject.toml)

| Package | Pin | Role |
|---|---|---|
| `langgraph` | >=1.0,<2.0 | Graph orchestration |
| `langchain-openai` | >=1.0,<2.0 | LLM client (ChatOpenAI → OpenRouter) |
| `sentence-transformers` | >=3.0,<4.0 | BGE-M3 embeddings |
| `fastapi` | >=0.115,<1.0 | HTTP server |
| `langgraph-checkpoint-postgres` | >=2.0,<3.0 | Persistent session state |
| `asyncpg` | >=0.29,<1.0 | Postgres async pool |
| `psycopg[async]` | >=3.1,<4.0 | Postgres (psycopg for checkpointer) |
| `pydantic` | >=2.0,<3.0 | Schema validation |
| `langdetect` | >=1.0.9,<2.0 | Language detection |

---

## 2. LangGraph Architecture

### Node Classification

| Node | File | Classification |
|---|---|---|
| `safety_check` | `nodes/safety_check.py` | **Deterministic** (rules engine + trajectory math); LLM only via S7 when `crisis_state=monitoring` |
| `intent_route` | `nodes/intent_route.py` | **LLM** |
| `skill_select` | `nodes/skill_select.py` | **Deterministic** (keyword substring + cosine threshold) |
| `skill_executor` | `nodes/skill_executor.py` | **Fully deterministic** |
| `freeflow_respond` | `nodes/freeflow_respond.py` | **LLM** (with bound tools) |
| `output_gate` | `nodes/output_gate.py` | **Deterministic** (format/cultural checks); LLM for translation + summary |
| `crisis_response` | `graph.py` inline | **Deterministic** (rules lookup for locale text) |
| `low_confidence_respond` | `nodes/low_confidence_respond.py` | **LLM** |
| `gate_path_set` | `graph.py` inline | **Deterministic** (state field stamp) |

### Complete Routing Logic

```
INPUT → safety_check
  ├─ [crisis_state=monitoring AND (not is_safe OR s7_result=NEW_CRISIS)] ──► crisis_response ──► END
  ├─ [crisis_state=monitoring AND is_safe AND s7_result≠NEW_CRISIS]      ──► intent_route
  ├─ [is_safe]                                                            ──► intent_route
  └─ [not is_safe]                                                        ──► crisis_response ──► END

intent_route
  ├─ intent=crisis                                  ──► crisis_response ──► END
  ├─ intent=scope_refusal | jailbreak               ──► gate_path_set ──► output_gate ──► END
  ├─ crisis_state=monitoring  (confidence gate BYPASSED)  ──► skill_select
  ├─ confidence < 0.6                               ──► low_confidence_respond ──► output_gate ──► END
  ├─ intent=new_skill | info_request                ──► skill_select
  ├─ intent=exit_skill + active_skill_id set        ──► skill_executor
  ├─ intent=skill_continuation + active_skill_id    ──► skill_executor
  └─ else (general_chat, freeflow)                  ──► freeflow_respond

skill_select
  ├─ active_skill_id set    ──► skill_executor ──► freeflow_respond ──► output_gate ──► END
  └─ no match               ──► freeflow_respond ──► output_gate ──► END
```

**8 distinct execution paths.** Crisis paths always terminate at END without passing through a responder.

### SageState — Complete Field Reference

| Field | Type | Set By | Notes |
|---|---|---|---|
| `raw_message` | str | `_build_state` | Per-turn input |
| `detected_language` | str | `safety_check` | `"en"` or `"ar"` |
| `message_en` | str | `safety_check` | Translated if Arabic |
| `is_safe` | bool | `safety_check` | `len(crisis_flags) == 0` |
| `crisis_flags` | list[str] | `safety_check` | `si_explicit`, `si_passive`, `si_method` — **per-turn, reset each turn** |
| `clinical_flags` | list[str] | `safety_check` | `substance_use`, `trauma_indicator`, `eating_concern`, `medication_mention`, `domestic_situation`, `escalating_distress` — **accumulated via set union** |
| `third_party_crisis` | bool | `safety_check` | |
| `crisis_state` | str | `crisis_response` | `"none"` / `"monitoring"` / `"resolved"` — **persisted via checkpoint** |
| `s7_result` | Optional[str] | `safety_check` | Only when `crisis_state=monitoring` |
| `s7_method` | Optional[str] | `safety_check` | `"keyword"` or `"llm"` |
| `distress_trajectory` | list[int] | `safety_check` | Rolling window of 4 `emotional_intensity` values |
| `engagement_trajectory` | list[int] | `safety_check` | Rolling window of 4 `engagement` values |
| `code_switching` | bool | `safety_check` | Arabic + Latin Unicode both present |
| `conversation_summary` | Optional[str] | `output_gate` | LLM-generated every 10 turns |
| `primary_intent` | Optional[str] | `intent_route` | 8-label enum |
| `secondary_intent` | Optional[str] | `intent_route` | Blended intent |
| `intent_confidence` | float | `intent_route` | 0.0–1.0 |
| `emotional_intensity` | int | `intent_route` | 1–10 |
| `engagement` | int | `intent_route` | 1–10 |
| `active_skill_id` | Optional[str] | `skill_select` / `skill_executor` | Cleared to None on completion or crisis |
| `active_step_id` | Optional[str] | `skill_select` / `skill_executor` | Next turn's starting step |
| `executed_step_id` | Optional[str] | `skill_executor` | Step used this turn |
| `step_instruction` | Optional[str] | `skill_executor` | Injected into responder L3 layer |
| `skill_match_method` | Optional[str] | `skill_select` | `"keyword"` / `"semantic"` / `"post_crisis_auto_select"` |
| `semantic_score` | Optional[float] | `skill_select` | Raw cosine similarity |
| `escalation_triggered` | Optional[dict] | `skill_executor` | L1/L2 escalation dict if fired |
| `prompt_layers` | list[str] | `freeflow_respond` | L0–L5 assembly record |
| `token_usage` | dict | `freeflow_respond` | **Always `{}` — not implemented** |
| `cultural_output_violations` | list[str] | `output_gate` | Non-blocking — logged only |
| `gate_path` | Optional[str] | `gate_path_set` / `crisis_response` | `"scope_refusal"` / `"jailbreak"` / `"crisis"` |
| `response_en` | Optional[str] | `freeflow_respond` / `low_confidence_respond` / `output_gate` | English response pre-translation |
| `response` | Optional[str] | `output_gate` | Final response (translated if Arabic) |
| `path` | list[str] | Every node | Each node appends its own name |
| `turn_count` | int | `output_gate` / `crisis_response` | Increments per turn |
| `conversation_history` | list[dict] | `output_gate` / `crisis_response` | Appends user+assistant each turn |
| `therapeutic_profile` | Optional[dict] | `server.py` pre-graph | Loaded from Postgres before `ainvoke` |
| `user_id` | Optional[str] | `_build_state` | |
| `session_id` | Optional[str] | `_build_state` | Also serves as LangGraph `thread_id` |

---

## 3. LLM-Driven Components

All LLM calls route via **OpenRouter** (`https://openrouter.ai/api/v1`) using `langchain_openai.ChatOpenAI`. Every call passes through `resilient_invoke` or `resilient_stream` (see [Section 10](#10-resilience-layer)).

### intent_route_node

- **Model:** `CLASSIFIER_MODEL` env var (default: `openai/gpt-4o-mini`), temperature=0, max_tokens=512
- **Fallback model:** `FALLBACK_CLASSIFIER_MODEL` (same default)
- **Input:** System prompt (8-label intent taxonomy with precise per-label rules) + last 3 conversation history turns + active skill (if any) + user message
- **Output parsing:** Regex `\{.*\}` + `json.loads`. Falls back to `{"primary_intent": "general_chat", "intent_confidence": 0.5}` on any parse failure
- **Returns to state:** `primary_intent`, `secondary_intent`, `intent_confidence`, `emotional_intensity` (1–10), `engagement` (1–10)
- **Notable:** Classifier prompt explicitly instructs NOT to classify somatic panic symptoms as `"crisis"` since `safety_check` has already run

### freeflow_respond_node

- **Model:** `RESPONDER_MODEL` env var (default: `anthropic/claude-sonnet-4-6`), temperature=0.7, max_tokens=1024
- **Fallback model:** `FALLBACK_RESPONDER_MODEL` (default: `openai/gpt-4o`)
- **Prompt:** 6-layer compose_prompt output (see [Section 11](#11-prompt-composition))
- **Tools bound (LLM-callable):** `knowledge_lookup`, `flag_for_review`, `record_observation` — max MAX_ITERATIONS=5 loop
- **Invocation:** If no text produced after tool loop, falls back to `resilient_invoke` directly
- **Returns to state:** `response_en`, `prompt_layers`, `token_usage` (always `{}`)

### low_confidence_respond_node

- **Model:** `RESPONDER_MODEL` via `resilient_stream`
- **Trigger:** `intent_confidence < 0.6`
- **Prompt:** Hardcoded — warm companion, one gentle open-ended clarifying question, max 2 sentences
- **Output:** Streamed and joined to string

### evaluate_s7 (post-crisis classifier)

- **Model:** `CLASSIFIER_MODEL`
- **Trigger:** Only when `crisis_state = "monitoring"` (called from within `safety_check_node`)
- **Architecture:** Keyword tier first, LLM only if no keyword match
  - `_STILL_DISTRESSED_KEYWORDS`: 24-entry frozenset — checked first
  - `_RECOVERY_KEYWORDS`: 29-entry frozenset
- **4 labels:** `RECOVERING` / `STILL_DISTRESSED` / `UNCLEAR` / `NEW_CRISIS`
- **Returns:** `(label, method)` where method is `"keyword"` or `"llm"`
- **Effect:** `NEW_CRISIS` re-routes to `crisis_response` even when `is_safe=True`

### summarise_history

- **Model:** `CLASSIFIER_MODEL`
- **Trigger:** `output_gate` every 10 turns
- **Output:** 2–3 sentence summary (life situation, emotional themes, routines, commitments)
- **Stored:** In `conversation_summary` state field + persisted to `session_summaries` via pgvector

### translate_to_english / translate_to_arabic

- **Model:** `TRANSLATOR_MODEL` env var (default: `openai/gpt-4o-mini`), temperature=0
- **Sync call:** `translate_to_english()` in `safety_check_node` — fallback to raw input on failure
- **Async call:** `async_translate_to_arabic()` in `output_gate_node` — 30s timeout, fallback to English on failure

### extract_session_profile

- **Model:** `CLASSIFIER_MODEL`
- **Trigger:** `POST /extract-profile` endpoint only — never called automatically during graph execution
- **Extraction gate:** `turn_count - last_extraction_turn >= 5` AND `delta_history >= 4` messages
- **Output:** 8 structured therapeutic fields merged into existing Postgres profile

---

## 4. Deterministic Components

### Rules Engine

`rules/engine.py` — fully stateless, 5 categories dispatched from `evaluate(category, context)`.

**Text normalization (`rules/normalize.py`):**
- `normalize_text`: strip invisible chars → NFKC → typographic substitution (smart quotes/dashes → ASCII) → lowercase
- `normalize_arabic`: above + strip harakat (diacritics) + normalize alef variants (آأإٱ → ا)
- Loader lints Arabic regex patterns at load time for unnormalized alef-hamza variants

**`safety` category:**
- `match_type: "keyword"` → `.find()` substring on `normalize_text(message_en)` or `normalize_arabic(text_ar)`
- `match_type: "regex"` → `re.search()`
- `negation_check` modifier → scan 6 tokens before match start for negation words (English + Arabic negation lists)
- `_apply_suppressions()` → span-overlap suppression: FPE rule must fire at an overlapping character span to cancel a crisis flag. No span overlap = no suppression. Missing span = no suppression (safe default)

**`crisis_content` category:** Locale-select for crisis response text (`{language}_uae`, `crisis_level=acute|extended`). Used by `crisis_response` node.

**`cultural` category:** `code_switch` and `keyword_match` trigger types by language. Injected into `compose_prompt` system role.

**`prompt_injection` category:** 5 trigger types — `keyword_match`, `flag_present`, `intent_match`, `secondary_intent_present`, `session_flag_present`. Anti-jailbreak and contextual guards.

**`cultural_output` category:** Post-generation check in `output_gate`. `check_type: "blocklist"` and `check_type: "allowlist_required"`. Non-blocking — only logs violations.

### Skill Executor

`nodes/skill_executor.py` — entirely deterministic.

**Step 1 — Escalation matrix:**
- L1: substring match against 14 multi-word natural exit phrases → exits skill
- L2: any `clinical_flags` present → flags clinician

**Step 2 — Step policy evaluation:**
```python
signals = {
    "emotional_intensity": state["emotional_intensity"],
    "engagement": state["engagement"],
}
```
Iterates `step_policy` list. Checks `condition.step == "ANY"` or exact match. Looks up `signals.get(condition.signal)` → if `None`, rule is silently skipped. Applies operator comparison if value found.

**Step 3 — Completion criteria:**
If no policy fires and `_meets_completion_criteria(message_en)` (word count > 10): advance to next step, or set `skill_complete=True` if last step.

### Skill Select — Two Deterministic Tiers

**Tier 1 (keyword):**
- Iterates all 13 skills' `target_presentations`
- `if keyword.lower() in state["message_en"].lower()` → select, first match wins
- Runs on English translation only (see Gap #3)

**Tier 2 (semantic):**
- BGE-M3 (`BAAI/bge-m3`, revision `5617a9f61b028005a4858fdac845db406aefb181`)
- `SEMANTIC_THRESHOLD = 0.5295` (calibrated 2026-05-23, gap=0.0128, corpus covers 3 of 13 skills)
- `asyncio.wait_for` with 10-second timeout — timeout falls back gracefully to freeflow

**Post-crisis override:**
- If `crisis_state = "monitoring"`: skip both tiers, auto-select `post_crisis_check_in`

### Output Gate

`nodes/output_gate.py` — deterministic checks before output.

**Format violation detection (non-blocking):**
```python
_FORMAT_VIOLATIONS = re.compile(r"—|\*\*|[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FAFF]")
```
Catches: em dash (`—`), bold markdown (`**`), emoji blocks. Logged to console only — does not block or retry.

**Clinical review trigger (deterministic threshold):**
- Fires when `(crisis_flags OR clinical_flags) AND session_id AND user_id`
- `severity="high"` for crisis_flags, `"medium"` for clinical-only
- Written as fire-and-forget `asyncio.create_task()`

**Scope refusal / jailbreak response:**
- If `gate_path = "scope_refusal"` or `"jailbreak"`: replaces `response_en` with hardcoded strings, skips cultural output checks entirely

---

## 5. Safety System

### Architecture

The safety system has a **documented, multi-layer target architecture** with only partial implementation:

| Layer | Name | Status |
|---|---|---|
| S1 | Lexical crisis detection (rules engine) | **Implemented** |
| S2 | MARBERT binary Arabic classifier | **Not implemented** |
| S3 | BGE-M3 semantic crisis embedding search | **Not implemented** |
| S7 | Post-crisis monitoring classifier | **Implemented** |

The file `safety_check.py` opens with an explicit architecture warning (lines 1–22) that this gap exists. **The comment is current and accurate — the code confirms S2 and S3 are absent.** Coverage is bounded entirely by human-enumerated lexicons.

### S1 — Lexical Layer: 10 Active Rules, ~183 Patterns

**crisis_keywords.json** — explicit SI:

| Rule ID | Language | Patterns | Flag | Notes |
|---|---|---|---|---|
| SK-EN-001 v1.0.0 | English | 21 | `si_explicit` | Negation_check enabled |
| SK-AZ-001 v1.0.0 | Arabizi | 13 | `si_explicit` | Code-switching |
| SK-AR-001 v1.0.0 | Arabic | 25 | `si_explicit` | No negation_check |
| SK-EN-003 v1.0.0 | English | 10 | `si_method` | Method references |
| SK-EN-004 v1.0.0 | English | 14 | `third_party_si` | Action: `third_party_crisis` |

**passive_si_patterns.json** — passive/veiled SI:

| Rule ID | Language | Patterns | Flag | Version |
|---|---|---|---|---|
| SK-EN-002 | English | 55 | `si_passive` | v1.1.0 (updated 2026-05-26) |
| SK-AR-002 | Arabic | 17 | `si_passive` | v1.0.0 |
| SK-AZ-002 | Arabizi | 9 | `si_passive` | v1.0.0 |
| SK-AR-003 | Arabic (Gulf) | 8 | `si_passive` | v1.0.0 — emotional exhaustion idioms |
| SK-EN-005 | English (regex) | 11 | `si_passive` | v1.0.0 — metaphorical escape/non-return |

**clinical_flag_patterns.json** — 5 persistent clinical categories (language: any):

| Rule | Category | Patterns |
|---|---|---|
| CF-001 | `substance_use` | 16 |
| CF-002 | `trauma_indicator` | 13 |
| CF-003 | `eating_concern` | 9 |
| CF-004 | `medication_mention` | 7 |
| CF-005 | `domestic_situation` | 17 |

### False Positive Exclusions (FPE)

**2 active, 3 inactive (pending clinician review):**

| Rule | Phrases | Suppresses | Status | Approved |
|---|---|---|---|---|
| FPE-AR-001 | 3 Arabic laughter idioms | `si_explicit + si_passive` | ✅ Active | 2026-05-22 |
| FPE-EN-001 | 15 English hyperbolic idioms ("dying of laughter", "killing it", "dead tired"...) | `si_explicit + si_passive` | ✅ Active | 2026-05-22 |
| FPE-AR-002 | 3 Gulf frustration supplication idioms ("الله ياخذني من هالدنيا") | `si_passive` | ❌ Inactive | Awaiting Khaleeji clinician review |
| FPE-EN-002 | 11 work/burnout hyperbole phrases ("this is killing me") | `si_passive` | ❌ Inactive | Also genuine burnout — pending review |
| FPE-EN-003 | 9 digital/social disconnection phrases ("disappear from social media") | `si_passive` | ❌ Inactive | Pending clinician review |

**Suppression mechanism:** Span-overlap only. If FPE fires at character span X and crisis flag fires at span Y, suppression only applies if X and Y overlap. No span = no suppression.

**Third-party crisis override:** If `third_party_flags` fires, `new_crisis_flags` is cleared to `[]` → `is_safe = True`. Third-party crisis routes separately.

### S7 — Post-Crisis Monitoring Classifier

- **Trigger:** Only when `crisis_state = "monitoring"`
- **Architecture:** Keyword tier first, LLM fallback
- **`_STILL_DISTRESSED_KEYWORDS`:** 24 entries — checked first
- **`_RECOVERY_KEYWORDS`:** 29 entries
- **`NEW_CRISIS` routing:** Overrides `is_safe=True` — re-routes to `crisis_response`

---

## 6. Skill System

### 13 Skills (Verified from `skill_ids.py` SKILL_REGISTRY)

| skill_id | Name | Evidence Base | Steps |
|---|---|---|---|
| `cbt_thought_record` | CBT Thought Record | Beck (1979); NICE CG159 | 3 |
| `grounding_5_4_3_2_1` | 5-4-3-2-1 Grounding | Linehan (1993); DBT | 5 |
| `sleep_hygiene` | Sleep Hygiene | Walker (2017); NHS; CBT-I | 3 |
| `post_crisis_check_in` | Post-Crisis Check-In | ASIST (2018); SafeTALK | 2 |
| `box_breathing` | Box Breathing | Jerath et al. (2006) | 4 |
| `mood_check_in` | Mood Check-in | PHQ-9; IAPT Minimum Dataset | — |
| `behavioral_activation` | Behavioral Activation | Martell et al. (2001); NICE CG90 | — |
| `worry_time` | Worry Time | Borkovec et al. (1983); NICE CG113 | — |
| `mi_readiness_ruler` | MI Readiness Ruler | Miller & Rollnick (2013) | — |
| `stop_technique` | STOP Technique | Linehan (1993); Kabat-Zinn (1990) | — |
| `progressive_muscle_relaxation` | PMR | Jacobson (1938); NICE CG90 | — |
| `safe_place_visualization` | Safe Place Visualization | Shapiro (2001); Bourne (2010) | — |
| `dbt_tipp` | DBT TIPP | Linehan (1993) | — |

**`post_crisis_check_in`** has empty `target_presentations` — it is **never keyword or semantically selected**. Only activated via the post-crisis auto-select override.

### Selection Hierarchy

```
1. crisis_state=monitoring?         → auto-select post_crisis_check_in (bypasses all tiers)
2. Any target_presentation keyword  → keyword match (first match wins, deterministic)
   in message_en.lower()?
3. BGE-M3 cosine ≥ 0.5295?          → semantic match (calibrated on 3/13 skills only)
4. No match                         → freeflow_respond (no skill)
```

### Skill Execution State Machine

```
Turn N:   skill_select sets active_skill_id + active_step_id (first step)
Turn N+k: skill_executor reads active_step_id
             → check escalation (L1 phrase match → exit; L2 clinical flags → flag clinician)
             → evaluate step_policy (emotional_intensity + engagement signals only)
             → check completion criteria (word count > 10)
             → return executed_step_id (this turn) + active_step_id (next turn)
          freeflow_respond reads executed_step_id + step_instruction
             → injects into L3 prompt layer
             → LLM responds guided by step
          On skill_complete=True: active_skill_id → None
```

### Skill JSON Schema Fields

```
skill_id, skill_name, skill_type, evidence_base, self_evolution
target_presentations: list[str]      — keyword tier matching
semantic_description: str            — embedding target (technique identity language)
steps: list[SkillStep]               — step_id, goal, technique, technique_description,
                                       tone, examples, contraindications, completion_criteria
step_policy: list[StepPolicyRule]    — condition (signal, operator, value, step) + action
escalation_matrix: dict              — L1, L2, L3, L4 string instructions
cultural_overrides: dict             — per-locale adaptations
```

---

## 7. Memory and Knowledge Layer

### LangGraph Checkpointing

`AsyncPostgresSaver` keyed by `session_id` (= LangGraph `thread_id`). Creates 4 tables on `setup()`. All SageState fields persist across HTTP requests within a session. **Without `DATABASE_URL`, runs in-memory — state resets between calls.**

### Therapeutic Profiles

**Table:** `public.user_therapeutic_profiles`  
**Write:** UPSERT via `/extract-profile` endpoint (never auto-triggered by graph)  
**Gate:** `turn_count - last_extraction_turn >= 5` AND `delta_history >= 4` messages  
**Fields:** `effective_techniques`, `ineffective_techniques`, `distortion_patterns`, `disclosed_concerns`, `communication_style`, `cultural_preferences` (jsonb), `mood_trajectory` (jsonb, last 20), `total_skills_completed`, `session_count`, `observations` (jsonb, last 50), `last_extraction_turn`, `last_updated_at`  
**Versioning:** Every upsert writes a snapshot to `public.therapeutic_profile_history`  
**Read:** Loaded by `server.py` before each `graph.ainvoke()` call, injected into state as `therapeutic_profile`, composed into L5 prompt layer

### pgvector Session Summaries

**Table:** `public.session_summaries` — `embedding vector(1024)`, `safety_level`, `skills_used`, `mood_score`  

**Write path (every 10 turns):**
```
output_gate → summarise_history() [LLM, 2–3 sentences]
           → get_embedding_async() [BGE-M3, 1024-dim]
           → repo.save_session_summary() [DELETE + INSERT]
```

**Read path (before each freeflow LLM call):**
```
freeflow_respond → retrieve_prior_context() [check_user_history.py]
                → embed current message [BGE-M3]
                → query session_summaries WHERE user_id = ?
                  AND safety_level NOT IN ["crisis"]
                  AND cosine_similarity >= 0.4774  [calibrated 2026-05-24]
                → return up to 3 results, capped at 800 chars total
```

Previous threshold was 0.6 — at that level 13/14 known-relevant queries fell below threshold.

### Clinician Review Queue

**Table:** `public.clinician_review_queue`  
**Two write paths:**
1. **Deterministic** (`output_gate`): fires when `(crisis_flags OR clinical_flags) AND session_id AND user_id` — `severity="high"` for crisis, `"medium"` for clinical-only — fire-and-forget async task
2. **LLM-perceived** (`flag_for_review` tool): responder model calls this for cumulative subtle risk it perceives

Both paths also call `pg_notify()` for real-time delivery.

### Knowledge Base (Static POC)

`knowledge.py` — Python dict, 10 entries: anxiety, depression, CBT, DBT, mindfulness, burnout, trauma, self-care, stress, motivational interviewing. Lookup via substring match only. No vector search, no ingestion pipeline. The `knowledge_lookup` LLM tool wraps this same dict. The codebase explicitly marks this as a POC; production target is Azure AI Search + BGE-M3 hybrid reranker with citation metadata.

---

## 8. API Surface

### POST /chat

```
Auth:     X-Sage-Api-Key header, hmac.compare_digest()
          If SAGE_API_KEY env var unset → auth bypassed entirely (open API)
Body:     {"messages": [...], "session_id": str, "user_id": str|null}
Response: StreamingResponse text/plain
          - Optional prefix: "[[CRISIS_DETECTED]]\n" when is_safe=False
          - Words streamed one at a time, 25ms delay each
          - On graph exception: "[[SERVER_ERROR]]"
```

**18 diagnostic response headers:**

| Header | Value |
|---|---|
| `X-Sage-Node-Path` | `path` field (node execution trace) |
| `X-Sage-Intent` | `primary_intent` |
| `X-Sage-Skill-Id` | `active_skill_id` |
| `X-Sage-Step-Id` | `executed_step_id` |
| `X-Sage-Active-Step-Id` | `active_step_id` |
| `X-Sage-Gate-Path` | `gate_path` |
| `X-Sage-Crisis-Flags` | `crisis_flags` |
| `X-Sage-Clinical-Flags` | `clinical_flags` |
| `X-Sage-Crisis-State` | `crisis_state` |
| `X-Sage-Emotional-Intensity` | `emotional_intensity` |
| `X-Sage-Distress-Trajectory` | `distress_trajectory` |
| `X-Sage-Engagement-Trajectory` | `engagement_trajectory` |
| `X-Sage-Conversation-Summary` | `conversation_summary` |
| `X-Sage-Semantic-Score` | `semantic_score` |
| `X-Sage-Prompt-Layers` | `prompt_layers` |
| `X-Sage-Token-Usage` | Always `{}` — not implemented |
| `X-Sage-Turn-Number` | `turn_count` |
| `X-Sage-Model` | RESPONDER_MODEL value |

### POST /extract-profile

```
Auth:     X-Sage-Api-Key header (same bypass when unset)
Body:     {"session_id": str, "user_id": str}
Action:   Fetch LangGraph checkpoint → LLM profile extraction → Postgres upsert
Response: {"status": "ok"|"skipped"|"error", ...}
```

**CORS:** `POST` method only. Origins from `CORS_ALLOWED_ORIGINS` env var (default: `http://localhost:3000`).

---

## 9. Language Handling

```
Detection (language.py):
  1. Strip Unicode directional marks
  2. Any U+0600–U+06FF char present? → "ar" (catches code-switching)
  3. langdetect.detect_langs() with ASCII guard
  4. Default: "en" on any exception

Code-switching:
  safety_check: Arabic Unicode AND Latin Unicode in same message → code_switching=True
  Stored in state, used to trigger cultural rules in compose_prompt

Arabic pipeline:
  safety_check  → translate_to_english() [sync LLM, fallback=raw input]
                → run S1 safety rules on BOTH message_en AND raw_message (text_ar)
  intent_route  → operates on message_en (English only)
  skill_select  → keyword tier on message_en.lower() only [see Gap #3]
  compose_prompt → cultural rules evaluate both text_en and text_ar
  output_gate   → async_translate_to_arabic(response_en) [30s timeout, fallback=English]
```

---

## 10. Resilience Layer

`resilience/__init__.py` — wraps all LLM calls with:

| Parameter | Value |
|---|---|
| `LLM_TIMEOUT_SECONDS` | 30.0 |
| `EMBEDDING_TIMEOUT_SECONDS` | 10.0 |
| `LLM_MAX_RETRIES` | 2 (= 3 total attempts) |
| Retry backoff | Exponential: `min(1.0 × 2^attempt, 8.0)` ± 20% jitter |
| `CIRCUIT_BREAKER_THRESHOLD` | 5 consecutive failures |
| `CIRCUIT_BREAKER_RESET_SECONDS` | 60.0 |

**Retryable conditions:** HTTP 429/502/503/504, `httpx.ConnectError`, `httpx.RemoteProtocolError`, `asyncio.TimeoutError`, `TimeoutError`, `OSError`

**Circuit breaker:** State keyed per `"{base_url}/{model_name}"`. When open: immediately skips primary, tries fallback model, then pre-authored fallback strings from `fallbacks.json`.

**Fallback chain:**
```
Primary LLM
  └─ [retries exhausted or circuit open]
     └─ Fallback LLM (configured per node in llm.py)
        └─ [also fails]
           └─ get_fallback_response(node, language) → pre-authored string from fallbacks.json
```

**`resilient_stream`:** Same retry/circuit logic. First-chunk timeout enforced; no per-chunk timeout after first chunk.

---

## 11. Prompt Composition

`prompts/composer.py` — 6-layer assembly with word budget enforcement.

**Word budgets:**
- L1 history budget (with skill/knowledge active): 450 words
- L1 history budget (pure freeflow): 600 words
- Cultural injection cap: 250 words (system role)
- Total budget: 1100 words — overflow triggers L1 shrink to 300 words at half window

**Layer assembly order:**

| Layer | Role | Content | Condition |
|---|---|---|---|
| L0 | System | `L0_persona` template — Sage persona, format rules | Always |
| Cultural | System | Rules engine `"cultural"` results, priority-sorted | When cultural rules fire |
| Prompt injection | System | Rules engine `"prompt_injection"` (system-target) | When rules fire |
| L1 | User | `L1_history` template — last 8 turns + conversation_summary if present | Always |
| L2 | User | `L2_intents/{intent}.json` — intent framing; secondary intent appended as text | Always |
| L5 | User | `L5_user_context` — clinical flags + cross-session therapeutic profile | When data present |
| Third-party crisis | User | Hardcoded text | When `third_party_crisis=True` |
| Post-crisis context | User | Hardcoded text + S7 result | When `crisis_state=monitoring` |
| Prompt injection | User | Rules engine `"prompt_injection"` (user-target) | When rules fire |
| L3 | User | `L3_skill_wrapper` — current step context | When `executed_step_id` set |
| L4 | User | `L4_knowledge` — knowledge snippet | When `info_request` in intent AND knowledge hit |
| USER message | User | Raw user message | Always — appended last |

---

## 12. Test Coverage

**36 test files.** BGE-M3 stubbed to zero vectors via `conftest.py` autouse fixture for all non-`@pytest.mark.slow` tests. All LLM calls mocked via `resilient_invoke` patches.

| Test File | Primary Coverage |
|---|---|
| `test_nodes.py` | `safety_check_node`: all safety paths, clinical flags, trajectories, Arabic, S7, accumulation |
| `test_graph.py` | 8 e2e execution paths; `@pytest.mark.slow` (real LLM) |
| `test_rules_integration.py` | All 5 rule categories, FPE suppression, negation |
| `test_prompts_composer.py` | 6-layer composition, word budget, L3/L5 injection |
| `test_resilience.py` | Circuit breaker, retry, fallback chain, timeout |
| `test_routing.py` | All routing functions and edge conditions |
| `test_server.py` | HTTP endpoints, auth, streaming, error handling |
| `test_skill_schema.py` | All 13 skills load and validate cleanly |
| `test_skill_select.py` | Keyword match, semantic miss (mocked), post-crisis auto-select |
| `test_rules_safety.py` | Safety rule patterns, suppression, negation |
| `test_rules_engine.py` | All 5 `_eval_*` functions |
| `test_rules_normalize.py` | normalize_text, normalize_arabic (NFKC, alef, harakat) |
| `test_audit_group3.py` | Regex (A3), third-party (A4), thread safety (A5), frontend formulas (B1/B3/B4), loader lint (A3-F1) |
| `test_l5_profile_injection.py` | Therapeutic profile L5 injection |
| `test_freeflow_respond.py` | Tool loop, retrieval integration, fallback |
| `test_check_user_history.py` | pgvector retrieval threshold, attribution, crisis exclusion |
| `test_safety_node_integration.py` | Integration class-based safety tests |
| `test_output_gate_response_paths.py` | scope_refusal, jailbreak, standard, crisis output paths |
| `test_output_gate_session_summary.py` | Session summary persistence trigger |
| `test_output_gate_clinical_review.py` | Clinical review notification trigger |
| `test_post_crisis_classifier.py` | S7 keyword tier + LLM fallback |
| `test_language.py` | Language detection: English, Arabic, code-switch, empty |
| `test_postgres_repository.py` | All `PostgresMemoryRepository` methods |
| `test_embedding.py` | `get_embedding`, `get_embedding_async` |
| `test_knowledge_lookup.py` | Tool wrapping, abstain path |
| `test_profile_extractor.py` | `extract_session_profile` |
| `test_trace_fields.py` | Audit trail field presence in output_gate |

---

## 13. Confirmed Gaps and Dead Code

All items below were verified against actual code, not comments.

### Safety Gaps

**G1 — S2 not implemented** `[safety_check.py lines 1–22]`  
MARBERT binary Arabic classifier. Architecture warning in code is accurate. No imports, no calls, no stub. Safety check runs S1 rules only.

**G2 — S3 not implemented** `[safety_check.py lines 1–22]`  
BGE-M3 semantic crisis detection (planned in v7 Door 1.5). No `src/sage_poc/safety/` directory exists. No `check_s3` call. No `calibrate_s3_threshold.py`. The architecture warning is current.

**G3 — FPE-AR-002, FPE-EN-002, FPE-EN-003 inactive**  
Gulf frustration supplication idioms, work/burnout hyperbole, and digital disconnection phrases are not suppressed. These phrases will trigger `si_passive` with no FPE protection until clinical review completes.

### Dead Code

**G4 — `step_policy` signals are partially dead** `[skill_executor.py lines 75–78]`  
```python
signals = {
    "emotional_intensity": emotional_intensity,
    "engagement": engagement,
}
```
Signals referenced in skill JSON step_policy rules but **never wired**: `resistance`, `hopelessness`, `user_stop_request`, `trauma_disclosure_detected`, `sensory_limitation_disclosed`, `re_escalation_detected`. Any step_policy rule referencing these signals will silently skip via `if signal_value is None: continue`. This affects `behavioral_activation.json`, `grounding_5_4_3_2_1.json`, and likely others. The clinical logic in those rules is inert at runtime.

**G5 — Arabic `target_presentations` keywords never match** `[skill_select.py line 100]`  
```python
message = state["message_en"].lower()  # English translation
```
The keyword tier runs on the English translation. Arabic phrases in `target_presentations` (e.g. `"ما أقدر أركز"`, `"حاسس إني مو هني"`, `"ما أقدر أقوم"`, `"ما عندي خلق"`) are compared against the English output of `translate_to_english()` and will never match. Raw Arabic input is available in `state["raw_message"]` but is not checked by the keyword tier.

**G6 — `token_usage` always `{}`** `[freeflow_respond.py]`  
```python
"token_usage": {}  # hardcoded
```
`X-Sage-Token-Usage` header always `{}`. No usage tracking implemented despite the state field and response header existing.

### Configuration Risks

**G7 — `SAGE_API_KEY` unset = open API** `[server.py lines 119–124]`  
```python
_expected_key = os.environ.get("SAGE_API_KEY", "")
if _expected_key and (...):  # guard is falsy when unset
    raise HTTPException(...)
```
Both `/chat` and `/extract-profile` are completely open when `SAGE_API_KEY` is not set in the environment.

### Calibration Limitations

**G8 — Semantic threshold calibrated on 3 of 13 skills** `[skill_select.py lines 18–32; scripts/calibrate_threshold.py]`  
`SEMANTIC_THRESHOLD = 0.5295` was calibrated against a KNOWN_HITS corpus covering only `cbt_thought_record` (5 examples), `grounding_5_4_3_2_1` (3), and `sleep_hygiene` (2). The remaining 10 skills (`dbt_tipp`, `behavioral_activation`, `worry_time`, `mi_readiness_ruler`, `stop_technique`, `progressive_muscle_relaxation`, `safe_place_visualization`, `box_breathing`, `mood_check_in`, `post_crisis_check_in`) have no hit-score representation in the calibration corpus. The threshold may be too high or too low for these skills.

### Other

**G9 — Knowledge base is static (POC)** `[knowledge.py]`  
10-entry Python dict, substring matching only. No `knowledge/` module, no `knowledge_retrieve.py` node, no vector search. The codebase acknowledges this as a POC.

**G10 — Jailbreak during monitoring silences S7 for that turn** `[graph.py line 90, commented]`  
A jailbreak attempt during `crisis_state=monitoring` routes to `gate_path_set → output_gate`, bypassing S7 re-evaluation. `crisis_state` remains `monitoring`, so S7 resumes next turn. Acknowledged in code comment.

---

*Audit produced 2026-05-26. Every claim verified against actual source code by direct file read.*
