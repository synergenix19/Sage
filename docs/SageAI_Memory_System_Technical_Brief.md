# SageAI — Memory System Technical Brief

**Classification:** Confidential — Technical Review  
**Version:** 1.0 | **Date:** 2026-06-03  
**Ground truth:** Validated against `sage-poc/` source code, migration files, and `docs/SageAI_architecture_current.md`  
**Purpose:** Present the implemented memory architecture to domain experts for feedback

---

## How to Read This Document

This brief describes exactly what has been built — not what was originally planned. Where the implementation differs from the original v7 design specification, those deviations are explicitly called out. Where there are open gaps (things designed but not yet activated, or things not yet built), they are flagged at the end.

The system has two distinct categories of memory:

| Category | Scope | Where stored |
|---|---|---|
| **Short-term memory** | Within a single conversation session | PostgreSQL (LangGraph checkpoint tables) |
| **Long-term memory** | Across multiple sessions | PostgreSQL (three separate tables) |

---

## 1. Short-Term Memory — Within a Session

### What it is

Short-term memory preserves the full conversation state between each message a user sends. Without it, every message would start from a blank slate.

### How it works

Every user turn in SageAI flows through a processing graph (9 sequential stages). After the graph completes each turn, the entire session state is written to a PostgreSQL database keyed by `session_id`. On the next turn, the state is loaded back before processing begins.

This is managed by **LangGraph's `AsyncPostgresSaver`** — a persistence layer designed specifically for stateful AI workflows. It uses a dedicated database connection pool (separate from all other operations) and writes to four internal LangGraph tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_migrations`, `checkpoint_writes`).

### What the short-term memory holds

| What is remembered | Why it matters |
|---|---|
| Full conversation history (all turns) | Enables contextual responses; the last 8 turns are directly included in every prompt |
| Rolling conversation summary | At every 10th turn, an LLM summarises the conversation (key situation, emotional themes, daily routines, commitments made). This summary travels forward in place of the older full turns. |
| Which therapeutic skill is in progress | A user mid-way through a CBT Thought Record is not interrupted — the system knows exactly which step they're on and picks up from there across any number of turns |
| Which step within the skill is next | The step the user will see on the *next* turn is stored, not re-computed |
| Crisis state | Whether the user is currently "none", "monitoring" (post-crisis), or "resolved". This state is preserved across the entire session. |
| Clinical flags | Substance use mentions, trauma indicators, eating concerns, medication mentions. Once detected in a session, these never reset within that session. |
| Emotional intensity and engagement trends | Rolling 4-turn windows of both signals, used for escalation detection |
| Resistance history | Rolling 3-turn window of user resistance scores (used by step policy rules) |
| Session gap detection timestamp | If a user returns after 4+ hours, the system detects the gap and handles the "stale skill" case — offering a warm re-entry rather than abruptly resuming mid-step |
| Turn counter | Triggers the rolling summary generation at every 10th turn |

### Fallback behaviour

If no `DATABASE_URL` is configured, the system runs without the checkpoint. Sessions work normally but all state resets between messages — no memory of previous turns within the same conversation.

---

## 2. Long-Term Memory — Across Sessions

Long-term memory has three components, each stored in a separate database table.

---

### 2.1 Therapeutic Profile

**Database table:** `public.user_therapeutic_profiles`  
**One row per user** (created on first extraction, updated on subsequent sessions)

#### What it holds

| Column | Type | Description |
|---|---|---|
| `effective_techniques` | list of text | Techniques this user explicitly said helped |
| `ineffective_techniques` | list of text | Approaches the user resisted or said didn't work |
| `distortion_patterns` | list of text | Cognitive distortion patterns observed across sessions |
| `disclosed_concerns` | list of text | Life areas or concerns the user has mentioned |
| `communication_style` | text | One sentence on how this user communicates (e.g. "Uses indirect language; responds better to open-ended questions than structured prompts") |
| `cultural_preferences` | structured object | `{religious_framing: yes/no, family_context: yes/no, gender_address: "he"/"she"/null}` |
| `mood_trajectory` | list of {session, score} | End-of-session mood estimate (1–5) for each of the last 20 sessions |
| `total_skills_completed` | integer | Cumulative count of therapeutic skills the user has fully completed |
| `session_count` | integer | Number of sessions extracted so far |
| `observations` | list of structured observations | Real-time clinical observations written mid-session (see §2.1.2 below) |
| `persisted_clinical_flags` | list of text | Clinical flags eligible for carry-over between sessions (currently disabled — see §4) |

#### How the profile is built — two write paths

##### Path 1: Post-session batch extraction

After a session ends, a `POST /extract-profile` call is made (triggered from the frontend). The system:

1. Fetches the session's conversation history from the checkpoint
2. Skips under two conditions: (a) fewer than 5 new turns since `last_extraction_turn`, or (b) fewer than 4 delta messages in the conversation slice — both must pass for extraction to proceed
3. Sends only the new turns (delta since last extraction) to an LLM with a strict instruction: *"Extract only what was explicitly stated"*
4. The LLM returns a structured JSON object with these 8 keys: effective techniques, ineffective techniques, distortion patterns, disclosed concerns, communication style, cultural preferences, end-of-session mood score, skills completed count
5. The extracted data is merged with the existing profile:
   - Technique and pattern lists are **union-merged** (`set` union — previous sessions are not lost)
   - Mood trajectory **appends** (capped at last 20 sessions)
   - Session count increments
   - Communication style: **prefer new** — uses the new session's value if present, otherwise keeps the existing value
   - Cultural preferences: **dict-merge** — new session values take precedence for any key present in both; keys not mentioned in the new extraction are preserved from the existing profile
6. Before writing, a full snapshot of the current profile is written to the audit history table (PDPL requirement — see §5)

> **Important: `observations` are NOT preserved by this path.** The merged dict passed to the database write does not include the `observations` field. If `record_observation` tool wrote observations during the session, post-session extraction will overwrite them with an empty list. This is a confirmed code gap — see §8.

##### Path 2: In-session real-time observations (LLM tool)

The system also captures momentary events that a post-session batch would miss. During a conversation turn, the LLM has access to a tool called `record_observation`. It calls this tool when it notices something worth preserving — for example, a user identifying their own cognitive distortion without being prompted.

The LLM provides:

| Parameter | Options | Meaning |
|---|---|---|
| `observation` | free text (1–2 sentences) | What was observed — factual, not interpretive |
| `observation_type` | `insight` / `progress` / `agency` / `context_update` / `concern` | Category of the observation |
| `confidence` | `high` / `medium` / `low` | How certain the LLM is of its observation |

Observation types:
- **insight** — user identified their own cognitive distortion or pattern without prompting
- **progress** — a technique worked or mood shifted measurably
- **agency** — user set a goal, made a commitment, or took initiative
- **context_update** — a life circumstance changed (new job, relationship change, etc.)
- **concern** — something the LLM noticed that warrants clinical attention

Observations are stored immediately in the profile's `observations` array (capped at the last 50). The profile write happens mid-session, so the observation is available in subsequent turns within the same session. However, see the gap note above — observations written during a session are erased when post-session extraction runs.

**Safety gate:** Low-confidence observations and all observations of type `concern` additionally trigger a clinician review notification (see §3). The LLM cannot silently persist clinically consequential facts without a human review checkpoint.

#### How the profile is used at runtime

At the start of every `/chat` turn, the therapeutic profile is loaded fresh from the database. The following fields are injected into the LLM prompt (the L5 "user context" block):

- **Effective techniques** — framed as "Techniques that have helped this user"
- **Ineffective techniques** — framed as "Approaches to avoid"
- **Distortion patterns** — framed as "Common thought patterns to be aware of"
- **Disclosed concerns** — the life areas the user has previously shared
- **Communication style** — injected as a one-line style guide
- **Religious framing preference** — if `true`, the LLM is told the user is comfortable with religious framing
- **Family context preference** — if `true`, the LLM is told the user discusses things in terms of family impact

**Known gap:** The `observations` field (real-time clinical observations from Path 2) is stored in the database but is **not currently injected into the LLM prompt**. The LLM cannot see its own past observations when starting a new session. The injection path is designed but not yet built. This is flagged in §4.

---

### 2.2 Session Summaries (Episodic Memory)

**Database table:** `public.session_summaries`  
**One row per session** (one entry overwritten if the session generates multiple summaries before it ends)

#### What it holds

| Column | Type | Description |
|---|---|---|
| `summary_text` | text | 2–3 sentence LLM-generated summary |
| `embedding` | vector(1024) | BGE-M3 mathematical representation of the summary — used for similarity search |
| `safety_level` | text | `"normal"` / `"clinical"` / `"crisis"` — controls whether this session can be recalled |
| `skills_used` | list of text | Which therapeutic skills were active during this session |
| `mood_score` | float | End-of-session mood estimate (1–5) |

#### How summaries are generated

At every 10th turn within a session, the system generates a summary using an LLM with a strict prompt:
> *Summarise in 2–3 sentences: the key life situation described, the main emotional themes, anything shared about daily life or routines, and any commitments or next steps the assistant offered. Be factual. No advice. No identifying details (no names, phone numbers).*

The safety level is assigned based on flags detected during the session:
- `"crisis"` — if any crisis flags were present
- `"clinical"` — if clinical flags (e.g. substance_use, trauma_indicator) were present but no crisis
- `"normal"` — otherwise

**Crisis sessions are permanently tagged** and handled differently during retrieval (see below).

#### How session summaries are retrieved (cross-session recall)

At the start of every turn in `freeflow_respond`, the system automatically looks up relevant prior sessions. This is done by:

1. Embedding the current user message using BGE-M3 (the same AI model used for semantic skill matching)
2. Searching the `session_summaries` table for prior sessions whose embedded summary is semantically similar to the current message
3. **Excluding all sessions tagged `"crisis"`** — past crisis sessions are never surfaced as casual context without a full safety re-check
4. Filtering to only summaries above a similarity threshold of 0.4774 (calibrated; set conservatively so as not to inject irrelevant history)
5. Returning at most 3 prior sessions, capped at 800 characters total
6. Each retrieved session is prefixed: *"In an earlier conversation, you mentioned..."*

This retrieved context is appended to the system prompt on turns that pass through `freeflow_respond` (the main response node). **Crisis turns are an exception** — when the safety check triggers a crisis response, the graph bypasses `freeflow_respond` entirely, so no prior context retrieval occurs on those turns.

**Architecture deviation from original v7 design:** The original specification defined this retrieval as an optional LLM-bound tool — meaning the LLM would decide whether to call it on each turn. The implementation makes it deterministic (always runs when user_id is present and the turn reaches freeflow_respond). The reasoning: in a clinical system, the risk of the LLM skipping a relevant therapeutic context is greater than the risk of occasionally injecting marginally relevant history. The similarity threshold (0.4774) guards against irrelevant injection.

---

## 3. Clinician Review Queue

**Database table:** `public.clinician_review_queue`  
**Notification channel:** `pg_notify('clinician_review', ...)` — real-time delivery to any connected listener

### Purpose

A mechanism for flagging sessions that require human clinical oversight — either because a safety rule fired, or because the LLM itself noticed a pattern that rules didn't catch.

### Three triggers

| Trigger | Source | Mechanism | Severity |
|---|---|---|---|
| **Safety rules fired** | Output gate (deterministic) | Fires automatically after any turn where crisis flags or clinical flags are non-empty | `high` for crisis; `medium` for clinical-only |
| **LLM clinical concern** | `flag_for_review` tool | LLM calls this when it perceives cumulative distress, implicit hopelessness, or ambiguous risk that rules didn't catch | LLM-assigned: `low` / `medium` / `high` |
| **Low-confidence observation** | `record_observation` tool | When the LLM records an observation with `confidence="low"` or type `"concern"` | Forwarded alongside the observation |

### What the LLM provides when flagging

When the LLM calls `flag_for_review`, it provides:
- **reason** — what it noticed (e.g. "cumulative hopelessness expressed across 3 turns without direct crisis language")
- **severity** — `low` (daily batch review), `medium` or `high` (within 4 hours)
- **turn_context** — an optional 1–2 sentence excerpt showing the pattern
- **evidence_turns** — optional list of which turn numbers support the concern

The LLM provides its reasoning, not a clinical decision. The clinician makes the clinical determination.

### Queue accumulation

If the same session generates multiple flag events (e.g. rules fire on turn 5, LLM flags on turn 12), each event is appended to a `flags_timeline` array rather than overwriting the record. Clinicians see the full progression of how flags evolved across the session.

### Data in the queue

The queue stores: `user_id` (UUID only — no PII), `session_id`, `reason`, `source`, `severity`, `payload` (structured JSON), `status` (`pending` by default), `flags_timeline`.

No names, emails, or identifying text appear in the queue record. Access is restricted by row-level security to admin users.

### Fire-and-forget architecture

All clinician review writes are asynchronous (`asyncio.create_task`) — they run alongside the response without delaying it. Failures in the notification system are logged as warnings and do not affect the user-facing response.

---

## 4. Clinical Flag Cross-Session Persistence

### Design intent

Clinical flags detected in one session — substance use mentions, trauma indicators, eating concern signals, medication mentions — were designed to carry forward to future sessions. Without this, the system loses a clinically significant signal the moment a session ends and the user returns the next day.

### Current status: infrastructure built, not activated

The full infrastructure is in place:
- The column `persisted_clinical_flags` exists in `user_therapeutic_profiles`
- Read and write methods are implemented and tested
- `safety_check` reads the persisted flags at the start of each turn and seeds them into the session's active flag set
- `output_gate` writes eligible flags to the database at the end of each turn

**However:** The configuration file that controls which flags are eligible (`flag_lifecycle_config.json`) currently has all 5 flag types set to `false`. Nothing carries across sessions today.

Enabling cross-session persistence for any flag type is a single-line configuration change per flag. The decision of which flags should persist (and what clinical criteria govern their expiry or removal) is a clinical governance question, not a technical one.

Current within-session behaviour is unchanged: once a flag fires within a session, it stays active for the entire session (regardless of the cross-session setting).

### Intentional exclusion: `domestic_situation`

`domestic_situation` flags are intentionally excluded from the cross-session design. The reasoning: a domestic situation is a situational safety concern tied to a specific disclosure. Carrying it forward as a persistent clinical colouring of future sessions — without the user re-disclosing — was judged as a misapplication of the clinical signal. This exclusion was made at design time.

---

## 5. PDPL Compliance and Audit Trail

### Profile history

Every write to `user_therapeutic_profiles` — whether from post-session extraction or a real-time observation — first inserts a full snapshot of the profile into `public.therapeutic_profile_history` with:
- `user_id`, `session_id`, `extraction_source` (`'llm_extraction'` for all current writes; `'clinician_edit'` and `'user_correction'` are defined in the schema for future use)
- Full JSONB snapshot of the profile state at that point in time

This means every change to a user's profile is versioned and attributable. The right to access, correct, and challenge stored data is structurally supported.

### Row-level security

Both `user_therapeutic_profiles` and `therapeutic_profile_history` have PostgreSQL row-level security (RLS) enabled. A user can only access their own row. Clinicians with admin access are granted via a separate admin policy.

### Identity substitution audit

When the output gate substitutes a response (e.g. because a cultural rule flagged the LLM's output as inappropriate), the original response text is written to a restricted table (`identity_substitution_audit`) accessible only to the Data Protection Officer and clinician_admin. The main audit log records only a SHA-256 hash of the original — the full text is never in the general audit trail.

### Session audit

Every turn produces a per-turn audit row written to a `session_audit` table (currently via Supabase REST API; production will move to UAE-hosted infrastructure). The audit includes: node path taken, intent classification, skill active, clinical flags, crisis state, knowledge source, response hash. It is written before the response exits the graph.

---

## 6. What the AI Model Can and Cannot Do With Memory

This section clarifies the boundaries — what memory the LLM can read, what it can write, and what it cannot touch.

### What the LLM reads

| Data | Via | LLM influence |
|---|---|---|
| Last 8 turns of conversation history | L1 prompt layer | Direct — LLM sees verbatim turns |
| Rolling conversation summary | L1 prompt layer | Direct — LLM sees the summary |
| Prior session context (semantic recall) | Retrieved before the LLM call | Direct — LLM sees prefixed summary snippets |
| Therapeutic profile: techniques, patterns, concerns, style, cultural preferences | L5 prompt layer | Direct — influences tone, technique selection, framing |
| Therapeutic profile: `observations` field | **Not injected (current gap)** | LLM cannot see its own past observations |

### What the LLM can write (via tools)

| Tool | What it writes | Clinical safeguard |
|---|---|---|
| `record_observation` | Appends to `observations` array in the profile | Low-confidence writes and `concern` type also trigger clinician review |
| `flag_for_review` | Creates or updates a record in clinician_review_queue | Clinician sees LLM reasoning; clinician makes the clinical determination |

### What the LLM cannot touch

- Effective/ineffective technique lists (read-only for the LLM — only modified by post-session batch extraction)
- Distortion patterns, disclosed concerns, communication style, cultural preferences (same — extraction-only)
- Session summaries (only the output gate writes these, at the 10th turn)
- Clinical flags (only deterministic safety rules write these — the LLM has no write path to crisis_flags or clinical_flags)
- Crisis state machine (only deterministic nodes control state transitions — no LLM tool can set crisis_state)

---

## 7. Database Infrastructure Summary

| Table | One row per | Written by | Read by | Notes |
|---|---|---|---|---|
| LangGraph checkpoint (4 tables) | Checkpoint event | LangGraph `AsyncPostgresSaver` | `AsyncPostgresSaver` at turn start | Short-term memory |
| `user_therapeutic_profiles` | User | Post-session extraction; `record_observation` tool | `server.py` at every turn start | Long-term profile |
| `therapeutic_profile_history` | Profile write event | Every call to `upsert_therapeutic_profile` | DPO / clinician audit only | PDPL audit trail |
| `session_summaries` | Session | `output_gate` (every 10th turn) | `freeflow_respond` (prior context retrieval) | Episodic memory |
| `clinician_review_queue` | Session (with timeline appending) | `output_gate` (flag detection); `flag_for_review` tool; `record_observation` tool | Clinician dashboard (pg_notify) | Real-time clinical alerts |
| `session_audit` | Turn | `output_gate` and `crisis_response` | PDPL compliance, clinical audit | POC: Supabase REST; production: UAE-hosted |
| `identity_substitution_audit` | Substitution event | `output_gate` (CUO-ID-001 substitutions only) | DPO + clinician_admin (RLS restricted) | Full original response text |

Two separate database connection pools serve different parts of the system:
- **psycopg `AsyncConnectionPool`** (`psycopg_pool`) — for LangGraph's `AsyncPostgresSaver`. LangGraph checkpointing requires psycopg; the pool is opened after a one-time autocommit setup connection that creates the four LangGraph tables (`AsyncPostgresSaver.setup()` must run outside a transaction).
- **asyncpg pool** (`asyncpg.create_pool`) — for all other memory operations (profile, summaries, clinician queue). `min_size=1, max_size=5`, idle connections recycled after 5 minutes.

---

## 8. Gaps and Open Items

The following are items that are designed, partially built, or explicitly deferred. They are listed here so domain experts can inform prioritisation.

| Gap | Status | Clinical implication |
|---|---|---|
| **`observations` erased by post-session extraction** | Confirmed code bug | The `/extract-profile` endpoint's merge dict does not include the `observations` field. When extraction runs after a session ends, it calls `upsert_therapeutic_profile` with `observations=[]`, overwriting all observations the `record_observation` tool wrote during the session. Observations are lost as soon as extraction runs. Fix: preserve `existing.get("observations", [])` in the merged dict. |
| **`observations` not injected into future session prompts** | Not yet built (separate from above) | Even once the erasure bug is fixed, there is no injection path. The LLM cannot see its own past observations in future sessions. The `_build_cross_session_block` function in `composer.py` reads 6 fields from the profile but `observations` is not one of them. |
| **Cross-session clinical flag persistence disabled** | Infrastructure complete; config set to false | Clinically significant signals (substance_use, trauma_indicator, eating_concern, medication_mention) do not carry across sessions. Each new session starts without awareness of prior clinical flags. Enabling requires clinical sign-off on which flags should persist and under what conditions they should expire or be cleared. |
| **No flag expiry or category differentiation model** | Design gap | There is no mechanism to age out stale flags (e.g. a substance_use flag from 6 months ago) or differentiate a historical flag from an active one. Before enabling cross-session persistence, a flag lifecycle model (active vs. historical, expiry conditions) is required. |
| **L4 escalation: 3+ crises in 30 days** | Not built | The v7 escalation matrix includes a human handoff trigger when a user has had 3 or more crisis events within 30 days. This requires cross-session crisis counting, which is not implemented. The clinician review queue exists for manual escalation in the interim. |
| **BGE-reranker-v2-m3 not active** | Deferred | The knowledge retrieval system uses reciprocal rank fusion (RRF) of vector and text search. A re-ranking pass with BGE-reranker-v2-m3 would improve retrieval quality but is deferred until the knowledge corpus exceeds 100 articles (currently 50). A marked insertion point exists in the code. |
| **Arabic orthographic normalisation not wired** | Accepted POC risk | ~4–5% of Arabic word forms in the knowledge corpus have orthographic variants (e.g. hamza forms) that are not normalised during search. BGE-M3 semantic search handles these gracefully, but full-text search quality degrades for these forms. A symmetric fix (corpus re-ingestion + query normalisation in one atomic change) is required pre-production. |

---

## 9. What Was Envisioned vs. What Is Built

| v7 Design Spec | Implemented | Notes |
|---|---|---|
| Session state checkpointed to Postgres | ✅ Yes | `AsyncPostgresSaver`, same as designed |
| Cross-session therapeutic profile | ✅ Yes | Two write paths (batch extraction + real-time tools) |
| Session summary episodic memory | ✅ Yes | Every 10th turn, BGE-M3 embedded |
| Prior context retrieval | ✅ Yes | Deterministic rather than LLM-bound tool (see §2.2) |
| `check_user_history` as LLM-callable tool | ❌ Changed | Deterministic pre-retrieval — LLM always gets the context rather than deciding whether to request it |
| Clinician review queue with `pg_notify` | ✅ Yes | Two trigger paths (Layer 1 deterministic + LLM tool) |
| `record_observation` LLM tool | ✅ Yes | Five observation types; clinician review gate on low confidence |
| `flag_for_review` LLM tool | ✅ Yes | Severity levels, evidence turns, reason text |
| Crisis detection as an LLM tool | ❌ Intentionally not implemented | Crisis detection is entirely deterministic (rules + BGE-M3 semantic). The LLM has no write path to crisis_flags. |
| Cross-session clinical flag persistence | ⚠️ Partial | Infrastructure complete; currently disabled pending clinical governance |
| Observations injected into future sessions | ❌ Not yet (two bugs) | (1) Post-session extraction erases observations written mid-session — bug in merge dict. (2) Even when present, observations are not injected into the L5 prompt — path not built. |
| L4 escalation: cross-session crisis count | ❌ Not built | Deferred post-Gitex |

---

*Document prepared 2026-06-03. Validated against `sage-poc/src/`, `sage-poc/migrations/`, and `sage-poc/docs/SageAI_architecture_current.md` (last updated 2026-05-31).*
