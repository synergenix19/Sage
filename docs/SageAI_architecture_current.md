# SageAI Architecture — Current State

**Document type:** Living codebase reference  
**Last updated:** 2026-06-12 (R1 consent-gated skill entry via skill_matching rules category; R3 engage-then-bridge in L2_general_chat v1.3.0; R5 criteria_hold_budget; see docs/superpowers/plans/2026-06-12-engagement-r1-r3-r5.md). Prior: 2026-05-31 (Phase 1: L2 unmatched-disclosure template; embedding field audit; open items GRIEF-SKILL, TIER2-DUALIDX, L2-AUTHORITY, EMOTIONS-FIELD added)  
**Supersedes:** `SageAI_v7_FINAL_COMPLETE.docx` and `docs/v7.1-post-crisis-state-addendum.md` for all code-level claims  
**Ground truth path:** `sage-poc/`

---

## 1. Overview

SageAI is an English-first therapeutic wellness companion with Arabic delivery via translation. It handles both languages but is not natively bilingual — skill logic is authored in English; Arabic replies are produced by translating the English response via the output_gate pipeline. See §3 (Language Pipeline) for the full translation architecture. It routes each user turn through a deterministic 9-node graph, selecting from 20 structured therapeutic skills or falling back to evidence-informed freeflow conversation. Crisis detection, clinical flag tracking, and post-crisis state management run on every turn ahead of any response generation.

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
| `offered_skill_ids` set AND `offer_response == "accept"` | `skill_select` (offer promotion; bypasses confidence gate, same precedent as monitoring) |
| Tier 1/Tier 2 match, `acute_direct_entry` rule NOT fired | `freeflow_respond` with `L2_skill_offer` (consent offer turn; `active_skill_id` stays `None`) |
| `intent_confidence < 0.6` (not monitoring) | `low_confidence_respond` |
| `primary_intent == "info_request"` | `skill_select` → immediate early-return → `knowledge_retrieve` |
| `primary_intent == "exit_skill"` AND active skill | `skill_executor` (runs L1 exit protocol) |
| `primary_intent == "scope_refusal"` or `"jailbreak"` | `output_gate` (deterministic response, no LLM) |
| Banned opener detected (first occurrence) | `output_gate` → retry → `freeflow_respond` |
| Banned opener persists after retry | Vetted fallback substituted; `output_gate_fallback_substituted` appended to path |

---

## 3. Language Pipeline

`language.py`. Fires in `safety_check_node` before any other processing.

### 3.1 Language Detection

Library: `langdetect`. Two overrides applied before the library result is trusted:

1. **Arabic Unicode override:** If the raw message contains any character in the Arabic Unicode range `[؀-ۿ]`, the result is `"ar"` regardless of what `langdetect` returns. This correctly handles code-switched messages (mixed Arabic/Latin).

2. **Latin false-positive collapse:** `langdetect` assigns unexpected codes (e.g. `"so"` for Somali, `"ha"` for Hausa) to short English phrases. Any result in a known Latin-script language set (50+ codes including `"so"`, `"ha"`, `"mg"`, `"st"`, `"ht"`) is collapsed to `"en"` when the text contains no non-ASCII characters.

3. **Directional mark stripping:** Unicode bidirectional and directional formatting marks (`U+200E`, `U+200F`, `U+202A–202E`, `U+2066–2069`) are stripped before detection. These can corrupt `langdetect` on RTL text (P2-5 fix).

**Code-switching detection** (separate from language detection): `safety_check_node` checks whether the raw message contains BOTH Arabic range characters AND Latin letters. If yes, `code_switching=True` is set in state. This triggers the `CU-CS-001` cultural rule in `compose_prompt`.

**Fallback:** Any `LangDetectException` or empty/None input → `"en"`.

### 3.2 Translation

Both directions use `get_translator()` (gpt-4o-mini by default, overridable via `SAGE_TRANSLATOR_MODEL`).

**Arabic → English (input translation):** Called in `safety_check_node` when `lang == "ar"`. Prompt: *"Translate the following text to English. Return ONLY the translation, nothing else."* The translated English is stored as `message_en` and used for all downstream processing (safety rules, intent routing, skill matching).

**English → Arabic (output translation):** Called in `output_gate_node` when `detected_language == "ar"`. Prompt: *"You are translating warm, supportive messages from a wellness companion named Sage. Translate to informal Gulf Arabic (Khaleeji dialect). Preserve emotional warmth and conversational tone. Avoid formal or clinical Arabic. Return only the translation."*

**Fallback:** If translation fails (LLM error, timeout), the original text is returned unchanged. The system never silences a response due to a translation failure.

**Async variants:** `async_translate_to_english` and `async_translate_to_arabic` use `resilient_invoke` (timeout, retry, circuit breaker). The sync variants (`translate_to_english`, `translate_to_arabic`) use a direct `llm.invoke()` call and exist for the rare synchronous code paths.

---

## 4. Safety Layer

### 4.1 S1 — Rules-Engine Lexicon

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

`skill_ids.py`. **24 skills as of 2026-06-01 (all production-approved):**

```
cbt_thought_record       grounding_5_4_3_2_1      sleep_hygiene
post_crisis_check_in     box_breathing             mood_check_in
behavioral_activation    worry_time                mi_readiness_ruler
stop_technique           progressive_muscle_relaxation  safe_place_visualization
dbt_tipp                 psychoed_anxiety          psychoed_depression
psychoed_stress          values_clarification      assertive_communication
self_compassion_break    mindfulness_body_scan     cognitive_restructuring
interpersonal_effectiveness  financial_anxiety     grief_loss
```

SK-001–SK-020 in production since v7 Gitex sprint (2026-05-27). SK-021–SK-024 (`cognitive_restructuring`, `interpersonal_effectiveness`, `financial_anxiety`, `grief_loss`) authored 2026-05-31, clinician-approved and promoted to production 2026-06-01.

`post_crisis_check_in` is exclusively auto-selected via `post_crisis_auto_select`; it has empty `target_presentations` and empty `semantic_description`.

Canonical inventory: `docs/SageAI_Skills_Knowledge_Base.md`. Proposed future skills (SK-025–SK-028): `emotion_regulation`, `thought_defusion`, `behavioural_experiment`, `problem_solving` — not yet authored.

### 5.2 Matching

`nodes/skill_select.py`. Two-tier — with several early-return paths ahead of the tiers. The in-node order is:

**Early-return order (each skips everything below it):**
1. `primary_intent == "info_request"` → returns immediately (preserving any active skill), routes to `knowledge_retrieve`
2. `crisis_state == "monitoring"` → `post_crisis_check_in` auto-selected unconditionally, no keyword or semantic check
3. `psychotic_disclosure` flag active AND referral not yet delivered → `psychotic_referral` auto-selected
4. Offer promotion (R1): pending `offered_skill_ids` AND `offer_response == "accept"` → the chosen offered skill is activated directly (`skill_match_method="offer_accept"`, path marker `offer_promoted`); a stale offer whose ids no longer resolve to known skills is cleared via the node's return dict and matching continues
5. Tier 1 match found → Tier 2 never runs
6. Tier 2 semantic matching

**Tier 1 — Keyword matching:**

Best-match keyword scoring (SF-1 semantics). Collects ALL matches across all skills in `SKILL_REGISTRY`, checking every `target_presentations` entry with `keyword.lower() in message_en.lower()` — case-insensitive substring. Matches are ranked by longest matched keyword (most specific first); the stable sort preserves registry order on ties. This eliminates the registry-order-as-tiebreaker dominant-shadower failures where a short keyword in a low-index skill blocked a longer, more-specific keyword in a high-index skill. For Arabic sessions, keywords are also matched against `raw_message` (Arabic-script keywords cannot match a translated English string).

There is no partial or contextual keyword match — it is always substring presence. The ranked candidate list is handed to the consent gate (below), which decides whether the top candidate activates directly or is offered.

**Tier 2 — BGE-M3 semantic matching:**

Only runs if Tier 1 found no match. Encodes `state["message_en"]` with BGE-M3 (in a thread, 10s timeout `EMBEDDING_TIMEOUT_SECONDS`). Computes cosine similarity against pre-computed embeddings of all skills' `semantic_description` fields. Returns the best-scoring skill if its score ≥ `SEMANTIC_THRESHOLD`, plus a runner-up — the highest-scoring OTHER skill at/above `SEMANTIC_THRESHOLD` — which R1 uses as the second offer candidate.

The embeddings are built at startup (or first request if warmup disabled) from `skill.semantic_description` for all skills that have a non-empty description. `post_crisis_check_in` has an empty description and is never in the semantic pool.

**Threshold calibration:** `uv run python scripts/calibrate_threshold.py`. Re-run after any `semantic_description` edit or skill addition. The threshold is the midpoint between the lowest cross-cluster hit score and the highest off-topic miss score. Gap as of 2026-05-27: 0.0533.

**On timeout:** If BGE-M3 takes > 10s, returns `embedding_timeout=True` in state, falls back to no skill (freeflow). Does not crash.

**No-match fallback path:** When both tiers miss (neither keyword nor semantic match), `_route_after_skill_select` returns `"freeflow"` (not `"knowledge_retrieve"` — that is the `info_request` path). The freeflow response is generated with the `L2_new_skill_unmatched` template (see §7.1), which supplies structural constraints. Without a matched skill, L3 is entirely absent from the prompt.

**Embedding field note (2026-05-31):** Tier 2 embeds `semantic_description` only — the technique-identity field. `target_presentations` (symptom/presentation language) is used exclusively in Tier 1 keyword matching. This is intentional: Tier 2 was calibrated for cross-cluster disambiguation between existing skills, not for catching novel symptom phrasings. A `new_skill` disclosure with no `target_presentations` keyword match AND no semantically adjacent skill will always fall through to the no-match path. The fix for a missing skill is authoring the skill with broad `target_presentations`, not extending Tier 2 (which is a standalone §4.3 evaluation — see §20.4).

**Consent gate (R1, 2026-06-12):**

A Tier 1 or Tier 2 match no longer activates a skill unconditionally. Once either tier produces ranked candidates (Tier 1: longest-keyword best-match list; Tier 2: best match plus a runner-up ≥ `SEMANTIC_THRESHOLD`), `skill_select._resolve_entry()` calls `rules_engine.evaluate("skill_matching", {matched_skill_id, emotional_intensity})` to decide how the primary candidate enters the conversation. Evaluation is first-match-wins by ascending priority; the loader pre-sorts at load time so the evaluator does not re-sort on the hot path.

Two rules are live in `rules/data/skill_matching/skill_matching_rules.json`:

- **`acute_direct_entry`** (priority 1): the 4 acute somatic skills (`box_breathing`, `grounding_5_4_3_2_1`, `stop_technique`, `dbt_tipp`) at `emotional_intensity ≥ 8` → direct activation, exactly the pre-R1 behaviour. `ignore_declined: true` — a prior decline does not block acute entry (safety over preference).
- **`default_offer`** (priority 99, empty condition = always matches): candidates become `offered_skill_ids` (≤ `max_offered` 2, declined skills filtered out), `active_skill_id` stays `None`, and the turn routes to `freeflow_respond`, which renders the `L2_skill_offer` template with plain-language blurbs from `prompts/offer_descriptions.json` (bilingual envelope; `ar: null` falls back to `en` — output_gate translates the composed reply for Arabic sessions).

If no rule fires at all (rules file missing/empty), the node falls back to a consent offer (`fallback_offer`) — consent is the fail-safe default, never silent entry. The fired rule_id always lands in `path` as `skill_matching_rule:<id>`.

**Path markers (the offer lifecycle audit trail):** `skill_offer_made` (offer created), `offer_promoted` (skill_select activated an accepted offer), `offer_accepted` / `offer_declined` / `offer_ignored` (intent_route classified the reply), `offer_unparsed` (classifier output unusable; offer preserved), `all_candidates_declined` (every candidate already declined; freeflow with no offer), `offer_voided_fallback` (S1-1: offer created this turn but the user-visible reply was replaced by the vetted fallback; the unseen offer is voided in the same state update), `enter_direct_declined_fallback` (see rule-author note below). Acceptance-rate metric: `count(offer_accepted) / (count(skill_offer_made) - count(offer_voided_fallback))` over `session_audit.path` — voided offers carry `skill_offer_made` but were never user-visible, so the raw made-count under-reports acceptance by design. Server-side voids after errored turns need no denominator adjustment in principle (the errored turn's audit row, when the C-4-class race drops it, is absent entirely); any errored-turn row that does persist also carries `skill_offer_made` without a possible accept, which is a known residual bias the C-4 fix should revisit.

**Declined skills:** session-scoped (`declined_scope: "session"` in the rules data). `intent_route` records declines (all skills in the declined offer are appended to `declined_skills`, order-preserving dedup via `dict.fromkeys`); declined skills are never re-offered within the session; the 4h stale-gap reset in `server_helpers._stale_skill_overrides` clears both `declined_skills` and any pending `offered_skill_ids` (session boundary). `_crisis_response_node` clears pending offers (`offered_skill_ids=None`) but does NOT clear declines.

**Rule-author note:** an `enter_direct` rule WITHOUT `ignore_declined` that matches a declined skill does not enter — it falls through to the consent path, and the path marker `enter_direct_declined_fallback` is appended so the audit trail explains the divergence between the fired rule and the action taken on that turn.

**Offer-reply classification (intent_route):** when `offered_skill_ids` is pending, `build_intent_prompt` appends a `PENDING OFFER` block to the per-turn user prompt asking the classifier for two extra JSON fields, `offer_response` ("accept" / "decline" / "other") and `offer_choice_skill_id`. `INTENT_SYSTEM` is untouched. Choice resolution (`_resolve_offer_choice`) tolerates display-name echo and positional index echo ("the first one", "الاول"). An absent `offer_response` field is treated as classifier degradation: the offer is preserved (`offer_unparsed`) and the composer re-renders it next turn as a gentle re-ask; an explicit `"other"` releases the offer. Total LLM failure on `intent_route` returns the neutral JSON fallback from `resilience/fallbacks.json` (general_chat, no `offer_response` key), so pending offers survive outages rather than being silently dropped.

**Governance status:** the `skill_matching` rules, `L2_skill_offer` template, `offer_descriptions.json`, and `soft_advance_instruction.json` are all `draft-pending-review`, `approved_by: null` — merge-gated on Rule 1 approval + clinical sign-off.

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
| `criteria_hold_budget` | Yes | `skill_executor` `evaluate_step_policy` criteria-blocked branch; `null` = no budget (hold indefinitely); 10 word-count skills opt in at `1` |

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

### 5.5 End-to-End Skill Activation Flow

This section traces exactly what happens from a user message to an LLM response within an active skill. Understanding this flow is essential because `skill_executor` and `freeflow_respond` divide the work in a way that is not obvious from looking at either node alone.

**The key insight: `skill_executor` never calls the LLM. `freeflow_respond` always generates the response. `skill_executor` only determines which instruction goes into the prompt.**

#### Turn 1 — Skill selection and first step

```
User: "I can't breathe, my heart is racing"

safety_check   → is_safe=True, no crisis flags
intent_route   → primary_intent="new_skill", emotional_intensity=7
skill_select   → Tier 1: "heart racing" in box_breathing.target_presentations → MATCH
                 returns: active_skill_id="box_breathing", active_step_id="step_1"
skill_executor → reads active_skill_id="box_breathing", active_step_id="step_1"
                 loads skill JSON, finds step "step_1"
                 runs L1 escalation check → no match
                 runs step_policy Phase 1 → intensity=7 > threshold? depends on skill config
                 runs completion_criteria check → no prior response to evaluate (turn 1)
                 returns: step_instruction="Guide user through box breathing...",
                          executed_step_id="step_1",
                          active_step_id="step_2"  ← next step for NEXT turn
                          active_skill_id="box_breathing"
freeflow_respond → compose_prompt sees step_instruction set and executed_step_id="step_1"
                   builds L3 block from skill JSON step "step_1":
                     goal, technique, tone, examples, contraindications
                   LLM generates response using L3 instruction as guide
output_gate    → cultural check, format check, translate if Arabic, audit
```

#### Turn 2 — Skill continuation

On the next turn, `active_step_id="step_2"` is loaded from the LangGraph checkpoint (NOT from the client request). `_build_state()` does not set `active_skill_id` or `active_step_id` — they come from checkpoint.

```
User: "Okay, I'm inhaling slowly..."

safety_check   → is_safe=True
intent_route   → primary_intent="skill_continuation"
              (NOT new_skill — the LLM sees the active skill in conversation history)
              → routes directly to skill_executor (bypasses skill_select)
skill_executor → reads active_skill_id="box_breathing", active_step_id="step_2"
                 evaluates completion_criteria for step_1 on THIS user message
                 (for _LLM_CRITERIA_SKILLS: LLM evaluator; for others: word-count)
                 if criteria met → advances to step_2, sets active_step_id="step_3"
                 if criteria not met → holds at step_2 (next_step_id="step_2")
```

#### Step state fields and their roles

| Field | Set by | Persists in checkpoint | Meaning |
|---|---|---|---|
| `active_skill_id` | `skill_select` | Yes | Skill currently being executed; `None` when no skill active |
| `active_step_id` | `skill_select` (first turn), `skill_executor` (subsequent) | Yes | Step to execute on the **next** turn |
| `executed_step_id` | `skill_executor` | No (reset each turn) | Step that was executed **this** turn; used by `compose_prompt` to build L3 |
| `step_instruction` | `skill_executor` | No (reset each turn) | The instruction text `compose_prompt` injects as L3 |
| `prev_step_id` | `skill_executor` | Yes | Step executed on the **previous** turn; used for continuation detection in step_policy |
| `rule_fired` | `skill_executor` | No (reset each turn) | True when a step_policy rule fired (not a normal advance); causes `compose_prompt` to use plain `step_instruction` instead of rebuilding from skill JSON |
| `criteria_hold_count` | `skill_executor` | Yes | R5: consecutive criteria holds at the current step; reset to 0 when `criteria_hold_step_id` no longer matches the step being executed |
| `criteria_hold_step_id` | `skill_executor` | Yes | R5: step the hold counter belongs to |

**Why `executed_step_id` and not `active_step_id` in L3:** After `skill_executor` runs, `active_step_id` has already been updated to the NEXT step. `compose_prompt` reads `executed_step_id` (the step just used) to rebuild the full L3 block with goal/technique/examples. Using `active_step_id` would show the LLM next turn's step — wrong.

#### Criteria hold budget and soft advance (R5, 2026-06-12)

`criteria_hold_count` is the **seventh** signal in `_KNOWN_STEP_POLICY_SIGNALS` — skill authors may write `step_policy` rules against it like any other signal. Independent of authored rules, a system-default budget rule lives in `evaluate_step_policy`: it fires **only at the criteria-blocked point** (after no step_policy rule fired and criteria did not pass), so it can never fire over a turn whose criteria actually passed.

When `skill.criteria_hold_budget` is non-null and `criteria_hold_count >= criteria_hold_budget`, the step soft-advances instead of holding: the action becomes `advance` (or `complete` on the last step) and governed text from `rules/data/step_policy/soft_advance_instruction.json` is appended to the step instruction ("respond to what they said, move forward naturally, do not repeat the previous question"). Therapeutic language does not live in `.py` files; the JSON carries the standard governance envelope (`draft-pending-review`, `approved_by: null`). The soft advance sets `rule_fired=True` so `compose_prompt` uses the appended `step_instruction` verbatim — the note survives composition rather than being lost to an L3 rebuild from skill JSON.

Code invariants the data cannot override: `entry_screen` steps are exempt (the medical-safety gate must never be budget-advanced), and `null` budget means no budget (hold indefinitely — the pre-R5 behaviour). 10 word-count-heuristic skills opt in at budget `1`; the `_LLM_CRITERIA_SKILLS` (which have a real evaluator rather than a token count) do not.

Counter lifecycle follows the **post-precedence-resolver** outcome, not the Phase 1 sentinel: the counter resets to 0 only when the final result is an advance/complete; it increments when the turn was criteria-blocked and the LLM evaluator did not confirm criteria; a Phase 2 safety hold (`validate_only`) that overrides a soft advance preserves the counter unchanged (the held turn neither resets nor double-counts). The counter also resets when the executor sees a different `criteria_hold_step_id` than the step being executed, and on L1 exit.

#### Skill completion

When `evaluate_step_policy` returns `action="complete"` (last step + criteria met):
- `skill_executor` sets `active_skill_id=None` in the return dict
- This is written to the LangGraph checkpoint
- Next turn: `_build_state()` does not set `active_skill_id`; checkpoint has `None`
- `intent_route` sees no active skill; routes based on new user intent

For `post_crisis_check_in` specifically: completion additionally sets `crisis_state="resolved"`.

#### L1 exit (user requests to stop)

If any phrase in `L1_EXIT_PHRASES` matches the message, `skill_executor` immediately returns with `active_skill_id=None` and `step_instruction="[L1] {escalation_matrix.L1 text}"`, bypassing all step_policy evaluation. The LLM sees the L1 exit instruction and produces a warm closing. No next step is set.

---

## 6. Knowledge Retrieval (Node: `knowledge_retrieve`)

`nodes/knowledge_retrieve.py`. Fires when `primary_intent == "info_request"` and `active_skill_id is None`.

### 6.1 Two Knowledge Retrieval Paths

**Don't confuse them — same underlying repository, different trigger points:**

| Path | Trigger | Where | State fields set |
|---|---|---|---|
| **Node path** | `info_request` intent + no active skill → `skill_select` early-return → `knowledge_retrieve` node | Before LLM call | `knowledge_passages`, `knowledge_abstain=False`, `knowledge_source="node_6"` |
| **Tool path** | LLM inside `freeflow_respond` calls `knowledge_lookup` tool mid-generation | Inside LLM tool loop | Passages returned to LLM as tool output; `knowledge_source="tool_lookup"` set after loop |

Both paths use `PostgresKnowledgeRepository` and the same `knowledge_articles` pgvector table.

**Key difference:** The node path makes passages available to the LLM before it starts writing. The tool path lets the LLM retrieve mid-response when it decides it needs clinical backing — the LLM calls the tool, reads the JSON result, then continues generating. The tool path is triggered by LLM judgement ("the user asked a factual question I should support"); the node path is triggered by deterministic `info_request` routing.

### 6.2 Hybrid Retrieval — Reciprocal Rank Fusion

`knowledge/postgres_repository.PostgresKnowledgeRepository.retrieve(query, language="en", top_k=5)`:

1. **Vector search:** BGE-M3 embeds the query, cosine distance via pgvector (`<=>` operator), top `top_k × 4` candidates
2. **Full-text search:** `ts_rank_cd(chunk_tsv, plainto_tsquery('english', query))`, top `top_k × 4` candidates
3. **RRF fusion:** `score = 1/(60 + vec_rank) + 1/(60 + txt_rank)` — k=60 is the standard literature default
4. **Final selection:** top `top_k` (default 5) by RRF score; passages with `rrf_score <= KNOWLEDGE_ABSTAIN_THRESHOLD` (0.0) are excluded

**`KNOWLEDGE_ABSTAIN_THRESHOLD = 0.0`** (POC setting): any match at all is returned; the abstain flag only fires when truly no rows match. This means the system may return marginally relevant passages. Pre-production: raise the threshold or add BGE-reranker-v2-m3 reranking pass (noted in a TODO comment in `postgres_repository.py`).

**When abstain=True:** The L4 block injects: *"KNOWLEDGE: No relevant clinical evidence found for this query. Do not fabricate clinical facts. If asked, tell the user you do not have specific information on that topic and offer to help them find a professional resource."* This is a clinical safety feature — the LLM is explicitly instructed not to invent answers when the knowledge base has nothing.

### 6.3 Corpus and Ingestion Pipeline

**Corpus:** `data/knowledge_corpus/en/` — 30 EN articles, 137 chunks. `data/knowledge_corpus/ar/` — 20 AR articles, 80 chunks (ingested 2026-06-01). Total: 50 articles, 217 chunks across both languages in `knowledge_articles`.

**Article format** (7 required fields):
```json
{
  "article_id":        "cbt-001",
  "language":          "en",
  "title":             "CBT Overview",
  "source_url":        "https://...",
  "citation":          "Beck (1979)",
  "content":           "...",
  "is_crisis_content": false
}
```

**Ingestion script:** `scripts/ingest_knowledge.py --corpus-dir path/ --db-url postgresql://...`

**Pipeline** (`knowledge/ingestion.py`):
1. **Validate schema** — all 7 fields present, language is "en" or "ar"
2. **Chunk** — sentence-boundary split at `~75 words per chunk` (100 tokens × 0.75 approximation). Crisis content (`is_crisis_content=true`) is never split — stored as a single chunk regardless of length.
3. **Embed** — each chunk embedded with BGE-M3 via `memory/embedding.get_embedding(chunk)` at ingestion time
4. **Upsert** — `INSERT INTO knowledge_articles ... ON CONFLICT (article_id) DO UPDATE` — re-running is safe; existing chunks are updated in-place
5. **Bilingual pairing check** — warns if an `article_id` has only one language variant (en without ar, or ar without en). Does not abort.

**`knowledge_articles` table columns:** `article_id`, `language`, `chunk_text`, `chunk_embedding` (vector 1024-dim), `is_crisis_content`, `source_title`, `source_url`, `citation_metadata` (JSONB), `chunk_tsv` (tsvector, for full-text search).

**Chunk ID convention:** Multi-chunk articles: `{article_id}-{language}-{index:03d}` (e.g. `cbt-001-en-000`). Single-chunk articles: `{article_id}-{language}` (e.g. `crisis-004-en`).

### 6.4 Arabic Knowledge Retrieval — Current State and Named Decisions

**Corpus (post 091d103):** Bilingual. 30 EN articles (`data/knowledge_corpus/en/`) + 20 AR articles (`data/knowledge_corpus/ar/`). Arabic users now retrieve from the Arabic corpus directly.

**Language routing (post 091d103):** `knowledge_retrieve_node` reads `detected_language` from state and passes it to `PostgresKnowledgeRepository.retrieve()`. The repository branches on language: FTS uses `plainto_tsquery('simple', query)` for Arabic (whitespace-only tokenisation, language-agnostic) and `plainto_tsquery('english', query)` for English (stemming + stopwords). The `knowledge_lookup` tool uses a language-injected factory (`make_knowledge_lookup_tool(language=detected_language)`) wired in `freeflow_respond.py`.

**`knowledge/rewriter.py`** provides `normalize_arabic_query()` (alef variants أإآ → ا, ta marbuta ة → ه, tatweel removal). It is **dead code by design** — not imported by any production path.

#### Named Decision: Arabic Orthographic Normalization — Deferred for POC

*Decision date: 2026-06-01. Status: Accepted POC risk.*

`normalize_arabic_query()` is deliberately not wired into either the ingest path (`ingestion.py`) or the query path (`postgres_repository.py`). The consequence: ~4–5% of Arabic word forms in the corpus use orthographic variants (e.g. ناسنإ stored vs ناسنا queried) that `plainto_tsquery('simple', ...)` does not normalise. Those forms silently degrade from hybrid (FTS+vector) to vector-only retrieval. BGE-M3 semantic embeddings handle the orthographic variation, so there is no silent failure — quality degrades, not correctness.

**Why not wire query-only now:** Query-only normalization without ingest-side normalization shifts which forms break — it would regress currently-working exact matches (user types the hamza form, corpus stores the hamza form, normalization collapses to bare alef → miss). Symmetric normalization (both sides, atomic) is required for correctness. Running an atomic fix requires: (1) `chunk_tsv` regeneration for all AR rows inside the migration, (2) `normalize_arabic_query()` called on the query at `retrieve()` time, applied in one changeset.

**Pre-production fix:** Wire `normalize_arabic_query()` symmetrically — call it during ingest (on `chunk_text` before `to_tsvector('simple', ...)`) and during retrieval (on the query before `plainto_tsquery('simple', ...)`), with `chunk_tsv` regenerated for all existing AR rows. Both changes in one migration. Never the query side without the corpus side.

#### Named Decision: Arabizi (Latin-script Arabic) on Retrieval — Out of POC Scope

*Decision date: 2026-06-01. Status: Out of scope, explicitly named.*

Arabizi queries (e.g. "ana ta3ban" typed in Latin script) are not detected, transliterated, or routed to the Arabic corpus. If a user submits an Arabizi query, `safety_check` will classify `detected_language` as `"en"` (Latin characters), and the query will route to the English corpus. This is neither handled nor an error — it is an undiscovered hole converted to a named, scoped decision. Arabizi-on-retrieval requires a transliteration layer (CAMeL Tools or equivalent) upstream of language detection. Defer to post-POC.

### 6.5 Legacy Static Knowledge Dictionary

`knowledge/static.py`. A hardcoded dictionary of 10 topic → answer pairs (anxiety, depression, CBT, DBT, mindfulness, burnout, trauma, self-care, stress, motivational interviewing). Uses exact phrase substring matching: `phrase in query.lower()`.

**This is no longer the primary knowledge source.** The `knowledge_lookup` tool was upgraded from this static dict to `PostgresKnowledgeRepository` (hybrid BM25+vector). The static dict is kept in `knowledge/__init__.py` as a backward-compatible re-export in case any code path still imports `lookup_knowledge` directly. For all production knowledge retrieval, use `PostgresKnowledgeRepository`.

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
- **L2** (`L2_intents/`): Intent-specific framing — always included. Template is selected by `composer.py` based on `primary_intent`. Two selector overrides exist. (1) When `primary_intent == "new_skill"` AND `active_skill_id is None` (skill_select found no match), composer selects `L2_new_skill_unmatched` instead of `L2_new_skill`. This template carries structural constraints for the unmatched-disclosure path: name the specific disclosure, do not re-probe emotions already stated, offer presence over solutions. It prevents the generic freeflow anti-pattern ("how are you managing those feelings?") when emotional disclosures fall through skill matching. Template is `draft-pending-review` (Rule 1 + clinical); `approved_by: null`, `effective_date: pending`. (2) R1 (2026-06-12): pending `offered_skill_ids` overrides intent-based selection entirely — composer selects `L2_skill_offer` with the `{offer_options_block}` variable (one numbered line per offered skill: display name + plain blurb from `prompts/offer_descriptions.json`). State-driven because the offer is created by `skill_select`, not `intent_route`. The offer block's actual word count is deducted from the L1 history budget proactively (`offer_words` param on `_compute_l1_budget`), so the offer never triggers reactive history shrinking. An empty options block (all ids unknown) falls back to intent-based L2 selection — the offer template never renders with a blank menu. `L2_skill_offer` is `draft-pending-review` (Rule 1 + clinical); `approved_by: null`. Separately, `L2_general_chat` is at v1.3.0 (R3, 2026-06-12): engage-then-bridge — engage briefly and substantively with non-wellbeing topics then connect back to the user; the prior deflection clause was removed, and answering a direct question with a feelings probe is explicitly prohibited.
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
`raw_message`, `message_en`, `detected_language`, `is_safe`, `crisis_flags`, `third_party_crisis`, `primary_intent`, `secondary_intent`, `intent_confidence`, `emotional_intensity`, `engagement`, `executed_step_id`, `step_instruction`, `rule_fired`, `escalation_triggered`, `gate_path`, `response_en`, `response`, `path`, `code_switching`, `s7_result`, `s7_method`, `skill_match_method`, `semantic_score`, `prompt_layers`, `token_usage`, `cultural_output_violations`, `new_clinical_flags_turn`, `resistance_score`, `knowledge_source`, `knowledge_abstain`, `knowledge_passages`, `session_id`, `user_id`, `banned_opener_retry_count`, `banned_opener_correction`, `banned_opener_fallback_used`, `offer_response`, `offer_choice_skill_id`

**Persistent via checkpoint (NOT set by `_build_state`):**
`conversation_history`, `crisis_state`, `active_skill_id`, `active_step_id`, `clinical_flags`, `distress_trajectory`, `engagement_trajectory`, `conversation_summary`, `turn_count`, `therapeutic_profile`, `resistance_history`, `prev_step_id`, `stale_skill_id`, `last_turn_at`, `re_escalation_within_monitoring`, `offered_skill_ids`, `declined_skills`, `criteria_hold_count`, `criteria_hold_step_id`

**R1/R5 field semantics (2026-06-12):**

| Field | Persistence | Lifecycle |
|---|---|---|
| `offered_skill_ids` | Checkpoint | Set by `skill_select` (consent offer). Cleared on accept (`skill_select` promotion), decline/ignore (`intent_route`), crisis (`_crisis_response_node`), and the 4h stale gap (`_stale_skill_overrides`) |
| `offer_response` | Per-turn (reset in `_build_state`) | `"accept"` / `"decline"` / `"other"`, written by `intent_route`; absent field preserves the offer (`offer_unparsed`) |
| `offer_choice_skill_id` | Per-turn (reset in `_build_state`) | Resolved offered skill id on accept; tolerates display-name and index echo |
| `declined_skills` | Checkpoint | Appended by `intent_route` on decline (order-preserving dedup); never re-offered within the session; cleared ONLY at the 4h stale gap — crisis does NOT clear declines |
| `criteria_hold_count` | Checkpoint | Consecutive criteria holds at the current step (R5); reset on advance/complete, L1 exit, or step change; preserved through a `validate_only` safety hold |
| `criteria_hold_step_id` | Checkpoint | Step the hold counter belongs to (R5) |

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

## 16. Rules Engine

`rules/engine.py`. A stateless evaluator that never reads or writes `SageState`. Called from `safety_check_node`, `skill_select_node`, `compose_prompt`, and `output_gate_node` with different categories and contexts.

### 16.1 Six Rule Categories

| Category | Called by | What it does |
|---|---|---|
| `safety` | `safety_check_node` | Detects crisis signals and clinical flags in user message |
| `crisis_content` | `_crisis_response_node` | Selects the locale-appropriate crisis hotline response |
| `cultural` | `compose_prompt` | Injects cultural adaptations into system prompt |
| `prompt_injection` | `compose_prompt` | Injects clinical/situational adaptations into prompt |
| `cultural_output` | `output_gate_node` | Post-generation check — validates response against cultural constraints |
| `skill_matching` | `skill_select_node` | Decides how a matched skill enters the conversation: direct entry or consent offer (R1, 2026-06-12) |

### 16.2 Safety Rule Evaluation

Context: `{text_en, text_ar, language}`.

- **OR-semantics for crisis flags:** every matching rule fires independently; `safety_check_node` collects all `crisis_flag` actions into `crisis_flags`.
- **Accumulate for clinical flags:** `clinical_flag` actions accumulate into `clinical_flags`.
- **Arabic patterns routed to normalized Arabic text:** rules with Arabic-script patterns or `language="ar"` are matched against `normalize_arabic(text_ar)` rather than `text_en`.
- **Negation detection:** if a `negation_check` modifier is present on a rule, the engine checks the 6 tokens before the match start for negation words (don't, not, never, لا, ما, مو, etc.). A negation → match is discarded.
- **Span-scoped suppression:** `false_positive_exclusions.json` rules set `type: "crisis_suppress"`. A suppression only cancels a crisis_flag rule if both spans overlap in the text. Missing span info on either side → suppression does NOT fire (conservative default — missing position data is not grounds for hiding a crisis signal).

### 16.3 Crisis Content Evaluation

Context: `{language, crisis_level}`. Locale-select strategy: builds `locale = f"{language}_uae"` and returns the first rule matching both locale and crisis_level. At most one rule fires.

Four rules (two locales × two crisis levels):

| Rule | Locale | Crisis level | First line |
|---|---|---|---|
| CC-EN-001 | en_uae | acute | "I'm really concerned about what you've shared. Please reach out for support now. In the UAE: MoHAP Counselling Line 800 46342 (free, 24/7), or emergency services: 999." |
| CC-EN-002 | en_uae | extended | Resource list: MoHAP 800 46342, CDA 800 4888, Emergency 999, Al Amal Hospital |
| CC-AR-001 | ar_uae | acute | Arabic equivalent of CC-EN-001 with same UAE numbers |
| CC-AR-002 | ar_uae | extended | Arabic resource list |

`_crisis_response_node` calls `rules_engine.evaluate("crisis_content", {"language": lang, "crisis_level": "acute"})`. If no rule fires, a hard-coded fallback response is used (graph.py lines 41-47).

### 16.4 Cultural Rule Evaluation

Context: `{text, text_ar, language, code_switch}`.

Three trigger mechanisms:
- **Empty `trigger_keywords`:** language-only trigger — fires on every message in the rule's target language without inspecting content (e.g. dialect mirroring fires on every Arabic turn).
- **`trigger_type: "code_switch"`:** fires when `code_switch=True` in context.
- **`trigger_type: "keyword_match"`:** Arabic-script keywords matched against `normalize_arabic(text_ar)`; Latin keywords matched against `normalize_text(message_en)`.

All matching cultural rules accumulate in the result. Their actions are injected into the system prompt in priority order (ascending priority number = highest priority first) within the 250-word global cultural budget.

### 16.5 Prompt Injection Rule Evaluation

Context: `{text, text_ar, clinical_flags, primary_intent, secondary_intent, session_flags}`.

Five trigger types:

| Type | Fires when |
|---|---|
| `keyword_match` | English or Arabic keyword found in message |
| `flag_present` | Named clinical flag is in `clinical_flags` |
| `intent_match` | `trigger_value` matches `primary_intent` or `secondary_intent` |
| `secondary_intent_present` | `secondary_intent` is not None |
| `session_flag_present` | `trigger_value` is in `session_flags` (e.g. `crisis_occurred`) |

All matching rules accumulate. Their content is injected into the user role under "SUPPORT ADAPTATIONS".

### 16.6 Cultural Output Evaluation

Context: `{response_text, message_en, clinical_flags}`.

Two-phase per rule:
1. **Condition check:** `always` / `keyword_in_message` / `flag_present`
2. **Violation check:** `blocklist` (any pattern found in response) or `allowlist_required` (no pattern found in response)

**Cultural output screening does not run on every response.** Three paths skip it entirely: `scope_refusal` (uses a hardcoded response string, not passed through cultural check), `jailbreak` (same), and `crisis_response` (bypasses `output_gate` entirely — no cultural output check, no audit_warn, no substitute). Only the standard, skill, freeflow, and knowledge paths are screened.

**Critical distinction: only one rule actually changes the response.**

| Rule | Check type | Action type | Effect |
|---|---|---|---|
| CUO-ID-001 (wellness identity) | blocklist | `substitute` | **Response is replaced** with canonical wellness companion statement |
| CUO-FA-001 (family framing) | blocklist | `audit_warn` | `_log.warning()` + `cultural_output_violations` in session audit. Response unchanged. |
| CUO-GC-001 (general cultural) | blocklist | `audit_warn` | `_log.warning()` + `cultural_output_violations` in session audit. Response unchanged. |
| CUO-SU-001 (substance language) | blocklist (flag_present condition) | `audit_warn` | `_log.warning()` + `cultural_output_violations` in session audit. Response unchanged. |
| CUO-IS-001 (religious mirroring) | allowlist_required | `audit_warn` | `_log.warning()` + `cultural_output_violations` in session audit. Response unchanged. |

**`audit_warn` violations do NOT reach the clinician review queue.** They are written to the server log and included in the `cultural_output_violations` field of the Supabase session_audit row. `PostgresNotifier.notify_review_required()` is not called. Clinicians see nothing in their dashboard about a cultural output violation — that queue is only triggered by `crisis_flags` and `clinical_flags`.

CUO-IS-001 checks that when the user used Islamic vocabulary, the response also contains some Islamic vocabulary or patience/trust language — verifying that mirroring occurred, not preventing it.

### 16.7 Skill Matching Rule Evaluation

Context: `{matched_skill_id, emotional_intensity}`. Called from `skill_select._resolve_entry()` after Tier 1 or Tier 2 produces ranked candidates (see §5.2 Consent gate for the full flow and path markers).

**`SkillMatchingRule` schema** (`rules/schemas.py`): governance envelope (`rule_id`, `version`, `authored_by`, `approved_by`, `effective_date`, `active`, `description`) + `priority` (ascending; first match wins) + `condition` (`matched_skill_in`: list of skill ids; `emotional_intensity_gte`: int; empty condition = always matches) + `action` (`{type: "enter_direct", ignore_declined?}` or `{type: "offer", max_offered, declined_scope}`).

**Load-time dead-signal validators** — the same failure class behind the 21 dead step_policy signals (spec present, runtime inert) is rejected at startup, never skipped silently:
- Condition keys outside `{matched_skill_in, emotional_intensity_gte}` → `ValueError` at model validation
- `action.type` outside `{enter_direct, offer}` → rejected
- `declined_scope` other than `"session"` → rejected (declaring unimplemented scopes in data recreates the dead-signal failure class)
- `matched_skill_in` as a bare string → rejected (would silently degrade to a substring test)

**Loader behaviour** (`rules/loader.py`): pre-sorts `skill_matching` rules by ascending priority at load time (stable — file order on ties), so the evaluator iterates in list order on the hot path without re-sorting. Warns on duplicate priorities (first-match-wins then resolves by file order, fragile for clinician-authored rules) and on any ACTIVE rule with `approved_by: null` (clinical sign-off required before production — same treatment as unapproved safety rules).

**Evaluation** (`_eval_skill_matching`): first-match-wins; at most one rule fires; a condition key absent from a rule is not checked. Live rules: `acute_direct_entry` (priority 1) and `default_offer` (priority 99) — see §5.2.

**Governance note:** the `skill_matching` category itself is an architectural addition pending human sign-off per the architecture-doc-debt convention; both live rules are `approved_by: null`, draft-pending-review, merge-gated on Rule 1 + clinical sign-off.

---

## 17. Cultural Intelligence Layer

The cultural intelligence layer is the system's capability to adapt to Gulf Arab cultural context. It operates across multiple points in the turn lifecycle through the rules engine and the language pipeline.

### 17.1 Cultural Rules — System Prompt Injections

Evaluated in `compose_prompt` via `rules_engine.evaluate("cultural", ...)`. All inject into the system role. Budget: 250 words total. Injections sorted by priority (lower number = higher priority).

| Rule | Trigger | Priority | What it injects |
|---|---|---|---|
| CU-SH-001 — Shame/Honour | عيب/عار/فضيحة/dishonor/disgrace keywords | 1 | "In Gulf culture, shame is a social bond signal, not only personal failure. Help the user find a path that honours both their integrity and their relationships." |
| CU-DM-001 — Dialect Mirroring | **Every Arabic turn** (language-only trigger, no keywords) | 2 | "Respond in Arabic. Use Gulf Arabic (Khaleeji) register: وايد over كثير, زين over حسن, شلون over كيف حالك. Mirror Khaleeji markers if user used them; use warm conversational Arabic for MSA. Do NOT switch to English unless the user switches first." |
| CU-CS-001 — Code-Switching | Both Arabic and Latin characters in same message | 3 | "Mirror their bilingual register: blend Arabic and English naturally. Do NOT force a single language. Do NOT comment on or correct their language choice." |
| CU-RR-001 — Ramadan | Ramadan/fasting/إفطار/سحور/عيد keywords | 4 | "Fasting fatigue, sleep disruption, and irritability are expected cultural norms, not clinical symptoms. Do NOT pathologise. Acknowledge the spiritual significance." |
| CU-CO-001 — Collectivist Framing | family/parents/duty/obligation/عائلة/واجب/شرف keywords | 5 | Collectivist framing that respects family investment and obligation without pathologising pressure |
| CU-IS-001 — Islamic Vocabulary | allah/muslim/quran/inshallah/الله/الحمد لله/إن شاء الله keywords | 6 | Turn-specific Islamic framing; integrates Islamic expressions naturally when the user used them |
| CU-RG-001 — Generic Religious | god/faith/prayer/church/bible/hindu/sikh/buddhist keywords | 6 | Affirms spiritual perspective without projecting a specific tradition; explicitly avoids imposing Islamic framing unless user referenced Islam |
| CU-GB-001 — Grief/Bereavement | death/loss/passed away/funeral/إنا لله/توفي/الله يرحمه keywords | — | Islamic bereavement cultural lens; validates mourning as spiritual and communal process |

**Note on CU-DM-001 (dialect mirroring):** This is the only cultural rule that fires on 100% of Arabic turns with no content trigger. It changed from keyword-triggered to language-triggered on 2026-05-22 because dialect mirroring must always be active for Arabic responses, not only when the user happens to use Khaleeji markers.

**Critical qualification — these are LLM instructions, not lexical enforcement.** All cultural rules inject guidance text into the prompt. The LLM is instructed to use وايد/زين/شلون and to mirror code-switching — but there is no output filter that verifies or forces this. Whether the LLM follows the guidance depends on model capability and the specific conversation context.

**Khaleeji dialect quality is not independently validated.** The `test_dialect_mirroring_fires_on_any_arabic_message` test confirms the rule injection reaches the system prompt (i.e. "Arabic" or "LANGUAGE" appears in system_str). It does not evaluate whether the actual Arabic output reads as authentic Khaleeji Gulf dialect. The demo readiness checklist (2026-05-27) lists "run Arabic scenarios with an Arabic-speaking colleague and verify dialect is appropriate for Gulf audience" as a pre-demo to-do — this has not been signed off as completed.

### 17.2 Prompt Injection Rules — User Role Adaptations

Evaluated in `compose_prompt` via `rules_engine.evaluate("prompt_injection", ...)`. All inject into the user role under "SUPPORT ADAPTATIONS". These adapt Sage's behaviour to the clinical or situational context detected this turn.

**Clinical flag adaptations (PI-CF-001 through PI-CF-005):** Fire when the named flag is in `clinical_flags`. These persist for the rest of the session once the flag is set.

| Rule | Trigger | Injection summary |
|---|---|---|
| PI-CF-001 | `substance_use` flag | Motivational interviewing — do NOT judge or suggest immediate cessation. Explore ambivalence. UAE legal context applies. |
| PI-CF-002 | `trauma_indicator` flag | Trauma-sensitive language — do NOT push for details. Prioritise emotional safety and containment. |
| PI-CF-003 | `eating_concern` flag | Body-neutral language — avoid all body or weight comments. |
| PI-CF-004 | `medication_mention` flag | No medication advice — do NOT advise on dosage or changes. Encourage speaking with prescriber. |
| PI-CF-005 | `domestic_situation` flag | Safety-first framing — do NOT advise leaving without safety planning (can increase risk in some situations). |

**Situational / demographic rules:**

| Rule | Trigger type | Trigger | Injection summary |
|---|---|---|---|
| PI-VI-001 — Venting | keyword_match | "just need to vent", "don't want advice", "just want someone to listen", "أبي أفضفض", "ما أبي نصايح" | "Hold space: reflect, validate. Do NOT offer techniques, advice, or solutions." |
| PI-ID-001 — Identity Question | keyword_match | "what are you", "are you a therapist", "are you a coach", "أنت معالج", "enta therapist" | "You are Sage, a wellness companion. Not a therapist, not a counsellor, not a mental health coach." |
| PI-AC-001 — Academic Pressure | keyword_match | exam/grade/study/family expectations education keywords | Collectivist Gulf framing for 18–25 UAE demographic; validates family investment without pathologising. |
| PI-BW-001 — Burnout/Work | keyword_match | burnout/exhaustion/work stress keywords | UAE expat workforce context; validates occupational exhaustion without medicalising. |
| PI-EI-001 — Expat Isolation | keyword_match | "missing home", "far from family", "loneliness", "feels foreign" | Expat isolation framing; validates collectivist longing as normal; contextualises without pathologising. |
| PI-CD-001 — Cumulative Distress | flag_present: `escalating_distress` | — | "Acknowledge the ongoing difficulty. Explore what has been weighing on them. Gently assess whether further support would help." |
| PI-PC-001 — Post-Crisis | session_flag_present: `crisis_occurred` | — | Gentle presence adaptation for turns following a crisis disclosure. |
| PI-SI-001 — Secondary Intent | secondary_intent_present | — | DBT dialectical framing when any secondary intent is detected (blended turn). |
| PI-TP-001 — Third Party | RETIRED | — | Replaced by direct third_party_crisis composer injection. Cannot fire. |

**Two-layer identity defence:**
- PI-ID-001 fires **before** generation, injecting "wellness companion" framing into the prompt so the LLM is correctly oriented before it writes.
- CUO-ID-001 fires **after** generation, substituting the response if the LLM still self-identified as therapist/coach/counsellor despite the PI-ID-001 injection.

### 17.3 L0 Persona — The Behavioural Foundation

`prompts/templates/L0_persona.json` (v1.4.0). Injected into the system role on every single turn. This is the document that defines Sage's voice and the hard behavioural constraints the LLM must follow regardless of any other instruction.

**Format constraints (enforced mechanically by output_gate for critical violations):**
- Plain prose. Commas or short sentences instead of dashes. No emojis. No markdown (`**`, `*`, bullets).
- Do not copy punctuation patterns from skill instructions.

**Phrasing constraints:**
- "Use plain, conversational language a supportive friend would use, not a therapy textbook."
- "Avoid abstract metaphors for distress." (Wrong: "What's sitting heaviest?", Right: "What's been bothering you most?")

**Banned reflective openers** (enforced mechanically by `output_gate._BANNED_OPENER_RE`):
> "It sounds like…" / "That sounds…" / "It seems like…" / "I can hear that…" / "I can see that…" / "It looks like…"
> *"If you are about to write 'It sounds like' or 'That sounds' or 'It seems like': stop. Rewrite it without the formula."*

**Banned opener phrases** (6 exact phrases blocked by L0, enforced by output_gate):
> "That's great to hear." / "That's really good to hear." / "That's wonderful to hear." / "That's good to hear." / "I'm really glad to hear that." / "That's so good to hear." / "It's good to hear." / "I'm glad to hear you're making progress."

**Response length:** 2–4 sentences unless the user needs more.

**Persona:** *"You are Sage, a warm Khaleeji wellness companion, not a therapist, counsellor, or mental health coach."*

**What Sage is not:** Does not diagnose, prescribe, or replace professional mental health care. If in crisis: express care and provide emergency resources only.

**Core instruction:** *"Be present before being helpful."* / *"Match the user's energy and register."*

---

## 18. Signal System — How Sage Reads the Room and Adapts

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

## 19. Performance Baseline

Measured 2026-05-31 against live server with DATABASE_URL (Supabase AP-SOUTH-1 checkpointer) and `SAGE_WARMUP_BGE=0`. 5 runs per scenario. Full report: `docs/superpowers/audits/2026-05-31-latency-benchmark.md`.

**TTFB = total response time** (fake streaming delay removed 2026-05-28; the body flushes immediately after `graph.ainvoke()` completes).

### 19.1 Measured Latency by Turn Type

| Scenario | Mean | p95 | Min | Max | Notes |
|---|---|---|---|---|---|
| EN crisis | 1.42s | 1.45s | 1.40s | 1.45s | Fastest, most consistent — rules-based, no LLM response generation |
| EN scope_refusal | 2.42s | 2.76s | 2.22s | 2.76s | 1 LLM call (intent_route only) |
| EN post_crisis | 3.08s | 3.76s | 2.22s | 3.76s | S7 classifier + post_crisis skill |
| EN low_confidence | 3.11s | 3.58s | 2.80s | 3.58s | |
| EN new_skill | 3.56s | 4.79s | 2.99s | 4.79s | |
| EN skill_continuation | 4.18s | 5.06s | 3.66s | 5.06s | |
| EN general_chat | 4.80s | **10.96s** | 2.82s | 10.96s | Run 1 = BGE-M3 cold-start; warm p95 ~3.0s |
| EN info_request | 5.15s | **10.05s** | 3.58s | 10.05s | One cold-start outlier; warm p95 ~4.4s |
| AR crisis | 1.92s | 2.18s | 1.78s | 2.18s | +0.5s vs EN crisis (translate-in) |
| AR general_chat | 4.49s | 4.66s | 4.37s | 4.66s | Very consistent; +1.6s over warm EN |
| AR code-switching | 4.89s | 5.53s | 4.45s | 5.53s | |
| AR new_skill | 6.07s | 6.81s | 5.39s | 6.81s | Slowest path; translate-in + translate-out |

**v7 KPI (<3s p95 English):** Not met. Warm-state p95 for most EN paths is 3.5–5.1s. Crisis and scope_refusal meet the KPI. All other paths require Option B (real streaming) to reach it.

**Arabic overhead over warm English:** +1.6s mean / +1.7s p95 on freeflow. Two extra gpt-4o-mini LLM calls (async_translate_to_english + async_translate_to_arabic).

### 19.2 Latency Cost Model (per-node estimates)

| Component | Every turn? | Estimated cost |
|---|---|---|
| S3 BGE-M3 semantic check (warm) | Yes | 200–400ms |
| intent_route LLM (gpt-4o-mini) | Yes | 400–800ms |
| freeflow_respond LLM (gpt-4o) | Non-crisis turns | 1,000–2,500ms |
| LangGraph AsyncPostgresSaver (Supabase AP-SOUTH-1) | Yes (with DATABASE_URL) | 400–800ms |
| async_translate_to_english (gpt-4o-mini) | Arabic input only | 600–1,000ms |
| async_translate_to_arabic (gpt-4o-mini) | Arabic output only | 600–1,000ms |
| BGE-M3 cold-start (first encode, SAGE_WARMUP_BGE=0) | Once per server restart | 7,000–10,000ms |
| Session summary summarise_history (turn % 10) | Every 10th turn | 500–1,500ms |
| LLM criteria eval (4 skills only) | Certain skill steps | 400ms |
| LLM resistance scoring | Skill turns with resistance rules | 400ms |
| Prior context pgvector retrieval | Each turn with user_id + DB | 100–300ms |
| knowledge_retrieve pgvector (warm) | info_request turns | 100–200ms |

---

## 20. Known Gaps and Pending Items

### 20.1 Safety and Clinical

| ID | Gap | Status | Notes |
|---|---|---|---|
| S2 | MARBERT Arabic crisis classifier | Not implemented | Architecture comment in `safety_check.py`. S3 provides semantic coverage; S2 adds dialectal Arabic coverage without a translation round-trip. |
| S3-AR | S3 on Arabic text | Not implemented | `check_s3` runs on `message_en` only; Arabic crisis phrases may score differently on original text. TODO comment in `safety_check.py` and `s3_semantic.py`. |
| CLF-xsession | Clinical flag cross-session persistence | Infrastructure ready, config decision pending | `flag_lifecycle_config.json` has all 5 flag types = false. Enable by setting values to true per flag once clinician decides which flags persist. |
| FALLBACK | `_VETTED_FALLBACK_RESPONSE` pending clinical review | Placeholder | See `docs/superpowers/reviews/FALLBACK_RESPONSE_REVIEW.md`. |
| Obs-inject | `observations` stored but not injected into prompt | Gap | `record_observation` tool writes to profile; `_build_cross_session_block` does not read it. Injection path not yet built. |
| Dialect-QA | Khaleeji dialect quality not independently validated | Pre-prod gate | Arabic-speaking Gulf-native colleague sign-off required before user exposure. |
| AR-KB-INGEST | Arabic KB articles ingested | **DONE 2026-06-01** | 20 articles → 80 chunks in `knowledge_articles` pgvector table. Total corpus: 137 EN chunks + 80 AR chunks = 217 chunks. All chunks have BGE-M3 embeddings. |
| AR-KB-CRISIS | Arabic pairs for crisis articles | Clinical gate — not yet addressed | crisis-001/002/003/004 require dual-clinician sign-off before Arabic versions may be authored or ingested. Independent of 2026-06-01 general approval. |

### 20.2 Performance

| ID | Improvement | Tier | Expected impact |
|---|---|---|---|
| WARMUP | Enable `SAGE_WARMUP_BGE=1` in production `.env` | Immediate (env var only) | Eliminates 7–10s cold-start spike on first BGE-M3 call per server restart |
| STREAM | Real token streaming — replace `graph.ainvoke()` with `graph.astream(stream_mode=["messages","values"])` | Sprint (2–4h) | Only path to <3s p95. TTFB drops to ~400ms (first intent_route token). Headers buffered until first `values` event. Requires server.py + frontend parser change. |
| CKPT-REGION | Move all data stores off Supabase AP-SOUTH-1 (Mumbai) to UAE-sovereign Postgres | **PDPL hard blocker — fix before any real user touches the system** | Two data classes at risk. (1) *Knowledge corpus* (`knowledge_articles`): clinician-authored content. Lower acuity — defer-with-documentation defensible for POC synthetic/demo runs. (2) *Conversation data* (`LangGraph AsyncPostgresSaver` checkpointer + `session_audit` + `therapeutic_profile`): clinical PII under Absolute Rule 5 ("no clinical user data leaves UAE"). If the Gitex demo uses real Khaleeji users, this is a live PDPL exposure during the POC, not a pre-prod item. Safe only if the demo runs on synthetic / scripted / consented-demo data with no real user turns stored. Latency benefit also applies (400–800ms saved). Only `DATABASE_URL` changes; code unchanged. |
| EMBED-CACHE | Cache BGE-M3 query embedding in state after S3; reuse in skill_select Tier 2 | Small code change | Eliminates duplicate BGE-M3 encode on semantic-match turns (~200–400ms). Both S3 and skill_select encode the same `message_en`. |
| S3-PARALLEL | Run S1 rules-engine and S3 BGE-M3 concurrently in safety_check via `asyncio.gather` | Small code change | S1 is synchronous (~5ms); S3 is ~200–400ms. Currently sequential. Parallelising saves S1 execution time (small, but free). |
| AR-TRANSLATE | Parallelize Arabic S1 rules-engine with input translation in safety_check | Medium code change | S1 can run on original Arabic text while translation proceeds. Saves ~600ms on Arabic turns. Requires splitting safety_check into two concurrent branches. |
| BGE-COLD-TEST | Session-scoped BGE-M3 pre-warm fixture in conftest.py | Test infrastructure | First slow test fails with `embedding_timeout` on 16GB M4. One fixture addition. |

### 20.3 Architecture — Falcon migration path

The current POC uses OpenRouter (gpt-4o / gpt-4o-mini) for all LLM roles. The production target is self-hosted Falcon on UAE-sovereign infrastructure. Latency implications:

| Role | Current (OpenRouter) | Falcon target | Expected gain |
|---|---|---|---|
| Intent classifier | gpt-4o-mini, 400–800ms API | Falcon-3B, 100–300ms GPU | −300–500ms per turn |
| Responder | gpt-4o, 1,000–2,500ms API | Falcon-34B+LoRA, 500–1,500ms GPU | −500ms mean; lower tail variance |
| Arabic translation | gpt-4o-mini, 600–1,000ms per call | MARBERT/AraBERT native (no separate call) | −1,200–2,000ms on Arabic turns |
| P95 tail | High variance (OpenRouter load) | Low variance (dedicated GPU queue) | Eliminates OpenRouter congestion spikes |

Falcon does **not** solve the streaming bottleneck. Even at 300ms inference, two sequential LLM calls = 600ms minimum, plus S3 and checkpoint. Streaming (STREAM above) is still required for sub-1s TTFB. The correct migration sequence is: **STREAM first → then Falcon**, not the reverse.

A combined classify+respond single-call architecture becomes possible with self-hosted Falcon: a single model call that emits structured intent + response in one pass, eliminating one entire LLM round-trip (~400–800ms saving).

### 20.4 Other pending items

| ID | Gap | Status | Notes |
|---|---|---|---|
| CUO-missing | Empty `cultural_overrides` in 4 skills | P2 | `box_breathing`, `mood_check_in`, `stop_technique`, `worry_time` have empty `cultural_overrides`. |
| BGE-revision | BGE-M3 model revision pinned | Maintenance | `_REVISION = "5617a9f6..."` in skill_select.py. Model promotion requires: update `_REVISION`, delete old cache, ANE compile, determinism check, recalibrate both thresholds. |
| SK-025–028 | 4 proposed future skills not yet authored | Proposed — scoping required | `emotion_regulation`, `thought_defusion`, `behavioural_experiment`, `problem_solving`. Require clinical scoping session before authoring. See `docs/SageAI_Skills_Knowledge_Base.md`. |
| TIER2-DUALIDX | Tier 2 semantic matching embeds `semantic_description` only | §4.3 evaluation required | `target_presentations` (symptom language) is Tier 1 only. Novel symptom phrasings not in any skill's `target_presentations` fall through both tiers. Proposed fix: dual-index (separate BGE-M3 embedding + threshold for `target_presentations`). Requires: novel-variant test set, calibrate_threshold.py extended for second index, Rule 1 approval. Do not concatenate fields — two semantic objectives require separate thresholds. |
| L2-AUTHORITY | L2 templates delivered as user-role | Open architectural review | All L2 templates (including `L2_new_skill_unmatched`) are assembled into `user_parts` in `compose_prompt`. Control instructions in L2 share the injection surface with user turns, which weakens instruction authority relative to system-role placement. Not fixed in this template — changing one template unilaterally would create inconsistency worse than the systemic issue. Requires a review of L2's authority tier across all templates. |
| EMOTIONS-FIELD | `emotions_disclosed` SageState field (Phase 2) | Blocked on §5 clinical decision | Phase 1 (2026-05-31) ships the structural constraint prose in `L2_new_skill_unmatched`. Phase 2 adds a session-scoped `list[str]` field written deterministically at Node 1 via Rules Service, read by the L2 binding to make the suppression concrete. Schema proposal at `docs/superpowers/proposals/2026-05-31-emotions-disclosed-schema.md`. Blocked on clinical decision: permanent within-thread suppression (persisted field) vs immediate-following-turn only (transient, no field). |
