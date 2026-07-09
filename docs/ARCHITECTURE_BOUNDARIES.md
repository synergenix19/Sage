# Architecture Boundaries: POC vs. Production

**Confirmed:** 2026-05-30 (re-verified against live codebase)
**Supersedes:** Prior version confirmed 2026-05-22
**Relevant spec sections:** v7 §5.2 (checkpointing), §6 (enriched state), §8 (audit trail)

---

## Current Architecture

The LangGraph graph is **stateful when `DATABASE_URL` is set** and stateless otherwise. This is a significant change from the 2026-05-22 boundary snapshot, which recorded the graph as entirely stateless. The unified memory layer (implemented 2026-05-23) wired in LangGraph checkpointing, therapeutic profile storage, and session summary persistence.

### What `_build_state()` does (and does not) do

`server_helpers._build_state()` builds only the per-turn slice of `SageState` — signals that are reset each turn (raw message, path, flags, etc.). It explicitly does NOT set persistent fields. These come from the LangGraph checkpoint loaded automatically by the graph when `thread_id` is provided:

```python
# Persistent fields intentionally absent from _build_state (they come from LangGraph checkpoint):
# conversation_history, crisis_state, active_skill_id, active_step_id,
# clinical_flags, distress_trajectory, engagement_trajectory,
# conversation_summary, turn_count, therapeutic_profile.
```

When `DATABASE_URL` is set: `build_graph(checkpointer=AsyncPostgresSaver(...))` — state persists between turns and across sessions.

When `DATABASE_URL` is unset: `build_graph(checkpointer=None)` — graph is effectively stateless (no session continuity). A startup warning is emitted.

### What the ChatRequest contains

```python
class ChatRequest(BaseModel):
    messages:   list[Message]
    session_id: str
    user_id:    str | None = None
    # Ferry fields removed — all cross-turn state lives in the LangGraph checkpoint
```

`_build_state()` takes only `req.messages[-1]` (the current user message). The conversation history injected into the prompt comes from the checkpoint, not from the full message list in the request body.

---

## Revised Production Blocker Status

The three blockers documented in the 2026-05-22 version are now addressed.

### Blocker 1: Enriched state has no home — RESOLVED

**2026-05-22 status:** "LangGraph native checkpointing via Azure Cosmos DB (v7 §5.2) … not implemented. Enriched state lives outside the graph."

**Current status:** LangGraph `AsyncPostgresSaver` is live in `server.py`. `SageState` — including all enriched state signals (`clinical_flags`, `therapeutic_profile`, `crisis_state`, `distress_trajectory`, etc.) — is written to the Postgres checkpoint after every turn and loaded at the start of the next. Session state survives server restarts.

Therapeutic profiles are additionally stored in `user_therapeutic_profiles` (separate from the LangGraph checkpoint tables) to support cross-session longitudinal tracking. Profile extraction runs via `POST /extract-profile` (called by Next.js after sessions).

**Remaining POC note:** The production spec called for Azure Cosmos DB. The current implementation uses Postgres (`AsyncPostgresSaver`). Cosmos DB migration is not yet scheduled; Postgres is the production-viable path through Gitex.

### Blocker 2: Client-side audit trail — RESOLVED

**2026-05-22 status:** "The `output_gate_node` audit payload is currently returned to Next.js and written to Supabase by the frontend route. For a clinical system, this is insufficient."

**Current status:** Audit writes are server-side, initiated inside graph execution as fire-and-forget `asyncio.create_task` calls:
- `output_gate_node` fires `write_session_audit(...)` via `asyncio.create_task` on every turn.
- `crisis_response` node fires `write_session_audit(...)` directly (output_gate is bypassed for crisis turns — the audit still fires).
- Both `write_session_audit` and `write_identity_substitution_audit` write to **Supabase** via httpx REST API (`SUPABASE_URL` + `SUPABASE_SERVICE_KEY`). Supabase is the POC audit store — production will migrate to secure cloud infrastructure.
- Clinician review queue entries are written by `memory/notification.PostgresNotifier` (asyncpg pool, `clinician_review_queue` table + `pg_notify`).

The writes are non-blocking (the graph response returns to the caller before the audit network request completes). They are server-initiated, not client-written — that is the key distinction from v7. If `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` are unset, audit writes silently no-op.

The frontend no longer receives audit payloads for persistence. The `X-Sage-*` response headers carry display metadata only.

**⚠️ Audit-trail incident (2026-07-07): `identity_substitution_audit` table never created.** `write_identity_substitution_audit` has POSTed to `/rest/v1/identity_substitution_audit` since 2026-05-27 (`ade88cb`), but **no migration in any ledger creates that table** — the write returns a PostgREST error, which the function swallows (`except … logger.error`). Confirmed **silent loss, not a serving-path throw** (output_gate is safe). Every identity-substitution's `original_response_text` has been dropped since 2026-05-27; the error log records the exception, not the row, so the original text is unrecoverable. PDPL Art. 6 right-to-challenge control has had no backing store for ~6 weeks. **REMEDIATION (fix/audit-integrity-package, migration `012`):** table created with the restricted posture in its creation migration (RLS `ENABLE`+`FORCE` + `REVOKE` anon/authenticated), plus a schema-conformance test diffing the writer's actually-POSTed payload against the parsed real `CREATE TABLE` columns (fails on drift either direction — not a hand-copied dict). Migration **NOT applied out-of-band** — rides the coordinated deploy. **Loss-window count = BOUNDED UNKNOWN (examined, not unexamined):** unquantifiable from persisted data (`session_audit` never stored `identity_substitution_rule_id` — the field is in `output_gate`'s return but there is no audit column) and from logs (Railway retention < the 6-week window). Recorded bound: window 2026-05-27→remediation; feature = CUO-ID-001 on the `output_gate` cultural-check path. **Adjacent, NOT fixed here:** even post-remediation `session_audit` has no `identity_substitution_rule_id` column, so future substitution counts stay unrecoverable unless that column is added.

**STANDING CONVENTION (data-security) — established 2026-07-07 after two instances in one audit (`shadow_register_eval`, `session_audit`):** any table holding **clinical or restricted text ships with RLS `ENABLE`d + `FORCE`d and default client grants (`anon`, `authenticated`) revoked as part of the same branch that creates it** — in the creation migration, or in an immediate follow-up migration that ships and applies together with it (e.g. `shadow_register_eval`: `009` creates, `010` hardens, both in one branch). It is never left as a separate later task. `service_role` (used by all backend writers) bypasses RLS, so this never affects legitimate writers; SELECT grants/policies for legitimate readers are preserved explicitly. **A table whose branch lands without this posture does not merge.** Reference remediations: `shadow_register_eval` (sage-poc migration 010, `ENABLE`+`FORCE`+`REVOKE`); `session_audit` write-exposure ([synergenix19/Sage#137](https://github.com/synergenix19/Sage/issues/137), routed to cdai ledger).

**STANDING CONVENTION (audit-write integrity) — established 2026-07-07 (third instance of the class):** a write to a **mandated** audit trail (the checklist requires "every response traceable") MUST be observable — it either **succeeds or raises an alert**. A silent no-op or swallowed error is never an acceptable failure mode. Fire-and-forget `asyncio.create_task` audit writes that log-and-discard turn a mandated trail into *best-effort*, which is a compliance-posture problem, not a bug. Concretely: (a) audit writers **surface** failure — a metric/alert on audit-write failure or persistence lag, not only a swallowed `logger.error`; (b) input that will make the write fail (e.g. a malformed or non-existent `user_id` FK) is validated **loudly at the API boundary (400)**, not silently dropped downstream. **Three instances of this class in one window:** `identity_substitution_audit` missing-table silent loss (above); `SUPABASE_*` unset → silent no-op (above); `session_audit`/profile writes swallow a `user_id` UUID-cast error and FK-409 on bad input (found 2026-07-07 in the native-Arabic shadow smoke — the "17:11 audit stop" that was **fake-user FK rejection, not an outage**). **Folded remediation (one ticket, one owner):** create `identity_substitution_audit` + make all audit-path writes alert-or-fail + validate `user_id` at the boundary. Adjacent but distinct: #137 (write-*exposure* vs silent write-*failure*).

**REMEDIATION STATUS (fix/audit-integrity-package, 2026-07-08) — audit of the first fix caught that "fixed in code" ≠ "fixed in posture":** (a) `user_id` pre-check + skip-with-log for test traffic — DONE; (b) all audit-write drop paths (session_audit + identity_substitution, HTTP *and* connection/timeout/serialization) now `logger.critical` with the shared greppable token **`AUDIT FAILURE`** — classification by consequence (row lost), not exception type — DONE; (c) auth-outage pre-check warning de-duplicated (warn-once, reset-on-success; fail-open unchanged) — DONE. **⚠️ THE ALERT HALF IS STILL UNMET:** verified there is **no CRITICAL sink** — no Sentry/monitoring env on prod *or* staging, no monitoring SDK in deps. So `logger.critical` reaches Railway stdout and stops. **Open requirement (owner: infra):** configure a Railway log-match alert on `AUDIT FAILURE` (Sentry is not in the toolchain — do not add it just for this), then **forced-fire test in staging** (trigger the CRITICAL path, confirm a human notification lands) and record the result. Until that is done, "alert-or-fail" is only "**label**-or-fail" — a CRITICAL no one consumes is the same silent drop with a better log line.

**STANDING CONVENTION (compliance-class closure) — established 2026-07-08 after the second premature closure on the audit workstream:** a compliance-class ticket closes **only against its enumerated requirements, each with attached evidence** — never by "code shipped." The failure pattern is closure-by-code-shipped rather than closure-by-requirement-verified (e.g. "engineering phase closed" was true; "nothing left here" was false, with a mandated-trail table missing and an unconsumed CRITICAL). For an audit-integrity ticket the checklist is: **sink named + forced-fire-tested; table exists with RLS posture verified by query on the applied env; a real-schema (payload-vs-columns) test green; loss window quantified or explicitly bounded.** The three-item audit that caught this *is* the closure template, not a post-hoc rescue.

**STANDING CONVENTION (deploy safety) — established 2026-07-07:** deploy candidates are validated by **ancestry, not recency**. While a safety hotfix is load-bearing, `git merge-base --is-ancestor <safety-commit> <tree>` is a **mandatory pre-deploy check** for any tree going to either environment — a branch tip is presumed unsafe until its ancestry is verified against the current safety-critical commits. Caught 2026-07-07: `46840ce` (a docs-branch tip) would have silently reverted the live OCD-compulsion veto (`bc3cb4b`) on prod. This belongs next to the SHA-pinning rule in the deploy runbook.

### Blocker 3: History-as-payload breaks at scale — RESOLVED

**2026-05-22 status:** "Sending the full conversation on every request works at roughly 10 turns in English. At 30+ turns in Khaleeji Arabic, this consumes context window budget that the 6-layer prompt composition needs."

**Current status:** Conversation history does not come from the client request. It comes from the LangGraph checkpoint. `_build_state()` takes only the most recent user message from `req.messages`. The graph loads `conversation_history` from the checkpoint. `output_gate_node` appends the current turn to history and writes it back to state on every turn.

Session summarisation at every 10th turn reduces history footprint for long sessions (summary replaces oldest turns in the L1 history block). Summary is also persisted via pgvector for prior-session context retrieval.

---

## Migration Path — Current State

| Layer | POC / Current | Production target |
|---|---|---|
| Session state | LangGraph checkpoint in Postgres (`AsyncPostgresSaver`) | Same pattern; migrate to Azure Cosmos DB when available |
| Persistence store | Postgres (asyncpg pool for memory, psycopg pool for checkpointer) | Azure Cosmos DB for checkpointing (not yet scheduled) |
| Audit writes | Server-side in `output_gate` and `crisis_response`, before response exits graph | Same — already production-grade |
| Conversation history | From LangGraph checkpoint (not client payload) | Same |
| Enriched state | Loaded from checkpoint and therapeutic_profile at each turn start | Same |
| Profile extraction | `POST /extract-profile` called externally (Next.js) after session | Consider moving to within-graph trigger at session boundary |

---

## Remaining POC Limitations

These are not production blockers but are known tradeoffs accepted for the Gitex POC:

### S2 (MARBERT) not implemented

The v7 spec defined a three-layer OR-fusion safety check: S1 (lexicon) + S2 (MARBERT binary classifier) + S3 (BGE-M3 semantic). S2 is not implemented. Current safety coverage is S1 + S3. The architecture comment in `safety_check.py` documents the intended path. This means dialectal Arabic expressions not in the S1 keyword list that also score below `S3_THRESHOLD` (0.8059) may be missed.

### S3 English-only

`check_s3` runs on `message_en` (translated to English if the user wrote in Arabic). S3 should also run on the original Arabic text for bilingual coverage. TODO comment is in `safety_check.py` and `s3_semantic.py`.

### Inference latency

`freeflow_respond` uses `ainvoke` (collect full response, then stream word-by-word). True streaming (`astream`) was deferred post-POC. Measured p95 = 9.6s. Acceptable for demo; production requires either streaming or sub-1s inference.

### Profile extraction is external

`POST /extract-profile` is called by Next.js after a session ends. This means profile extraction can fail silently if the client does not call the endpoint. A production design would trigger extraction at a well-defined graph boundary (e.g. `output_gate` at session end detection).

### Cross-session contamination risk (historical note)

The 2026-05-22 doc identified a risk of stale message carryover. The `key={activeSession.id}` fix on `ChatFadeIn` in the Next.js route (Fix B) prevents this. The LangGraph checkpointer keying on `session_id` as `thread_id` provides an additional server-side boundary. Consider this resolved at the current POC scope.
