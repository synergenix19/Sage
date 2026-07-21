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

**⚠️ Audit-trail incident (2026-07-07): `identity_substitution_audit` table never created.** `write_identity_substitution_audit` has POSTed to `/rest/v1/identity_substitution_audit` since 2026-05-27 (`ade88cb`), but **no migration in any ledger creates that table** — the write returns a PostgREST error, which the function swallows (`except … logger.error`). Confirmed **silent loss, not a serving-path throw** (output_gate is safe). Every identity-substitution's `original_response_text` has been dropped since 2026-05-27; the error log records the exception, not the row, so the original text is unrecoverable. PDPL Art. 6 right-to-challenge control has had no backing store for ~6 weeks. Remediation: create the table in the owning ledger **with the full restricted posture below in the creation migration**, plus a test asserting the write succeeds against the real schema. Loss-window count (turns that invoked it) to be quantified from prod logs / `identity_substitution_rule_id` audit rows — "unknown" is itself a compliance finding.

**STANDING CONVENTION (data-security) — established 2026-07-07 after two instances in one audit (`shadow_register_eval`, `session_audit`):** any table holding **clinical or restricted text ships with RLS `ENABLE`d + `FORCE`d and default client grants (`anon`, `authenticated`) revoked as part of the same branch that creates it** — in the creation migration, or in an immediate follow-up migration that ships and applies together with it (e.g. `shadow_register_eval`: `009` creates, `010` hardens, both in one branch). It is never left as a separate later task. `service_role` (used by all backend writers) bypasses RLS, so this never affects legitimate writers; SELECT grants/policies for legitimate readers are preserved explicitly. **A table whose branch lands without this posture does not merge.** Reference remediations: `shadow_register_eval` (sage-poc migration 010, `ENABLE`+`FORCE`+`REVOKE`); `session_audit` write-exposure ([synergenix19/Sage#137](https://github.com/synergenix19/Sage/issues/137), routed to cdai ledger).

**STANDING CONVENTION (audit-write integrity) — established 2026-07-07 (third instance of the class):** a write to a **mandated** audit trail (the checklist requires "every response traceable") MUST be observable — it either **succeeds or raises an alert**. A silent no-op or swallowed error is never an acceptable failure mode. Fire-and-forget `asyncio.create_task` audit writes that log-and-discard turn a mandated trail into *best-effort*, which is a compliance-posture problem, not a bug. Concretely: (a) audit writers **surface** failure — a metric/alert on audit-write failure or persistence lag, not only a swallowed `logger.error`; (b) input that will make the write fail (e.g. a malformed or non-existent `user_id` FK) is validated **loudly at the API boundary (400)**, not silently dropped downstream. **Three instances of this class in one window:** `identity_substitution_audit` missing-table silent loss (above); `SUPABASE_*` unset → silent no-op (above); `session_audit`/profile writes swallow a `user_id` UUID-cast error and FK-409 on bad input (found 2026-07-07 in the native-Arabic shadow smoke — the "17:11 audit stop" that was **fake-user FK rejection, not an outage**). **Folded remediation (one ticket, one owner):** create `identity_substitution_audit` + make all audit-path writes alert-or-fail + validate `user_id` at the boundary. Adjacent but distinct: #137 (write-*exposure* vs silent write-*failure*).

**STANDING CONVENTION (disarmed alarm) — established 2026-07-13:** a safety test that exists and asserts the right thing but is **excluded from the merge gate is a DISARMED CONTROL** — the same class as the CRITICAL-with-no-sink and the label-or-fail miss. Extending alert-or-fail: **excluding a safety test from CI requires the same justification as disabling the rule it guards.** A present-but-unwired assertion reads as protection while providing none. Caught 2026-07-13: `test_harm_to_others_node1_backstop` asserted `active is True`, was excluded from `unit-gate` CANDIDATES, and so failed **invisibly** when #218 reverted the #219 activation — the alarm that would have blocked the clobber was itself unwired. Concretely: (a) every safety-surface test lives in the gate's CANDIDATES list, and the visibility guard already warns on an absent covered suite; (b) removing one is a reviewed, justified act, not a silent omission. Also see the signed-fields manifest (`signed_clinical_fields.json`) which pins the rules' active state so a flip fails CI even if a test is missing — belt to the alarm's suspenders.

**STANDING CONVENTION (fix classification) — established 2026-07-13:** **restoring a signed, clinician-approved control to its approved state after an accidental clobber is a REGRESSION FIX requiring no new sign-off** — the signature attaches to the *content*, which was never re-decided; reverting a revert is not a new clinical decision. (Precedent: SK-EN-HTO-001 restored 2026-07-13 to its Vee-approved `b41a03d` state after #218's stale-base clobber, signature cited, no re-approval sought.) The bar for "restore" is proving the pre-clobber state was itself signed+verified — then restore it; do not re-run the approval clock.

**STANDING CONVENTION (deploy safety) — established 2026-07-07:** deploy candidates are validated by **ancestry, not recency**. While a safety hotfix is load-bearing, `git merge-base --is-ancestor <safety-commit> <tree>` is a **mandatory pre-deploy check** for any tree going to either environment — a branch tip is presumed unsafe until its ancestry is verified against the current safety-critical commits. Caught 2026-07-07: `46840ce` (a docs-branch tip) would have silently reverted the live OCD-compulsion veto (`bc3cb4b`) on prod. This belongs next to the SHA-pinning rule in the deploy runbook.

**COROLLARY (ancestry ≠ field value) — established 2026-07-13:** the ancestry check is **necessary but NOT sufficient for a safety FIELD.** `git merge-base --is-ancestor` proves a commit is *present*; it says nothing about whether a *later* present commit *reverted a value* that commit set. Caught 2026-07-13: the `7cbc77c` bypass deploy passed "ancestry-verified, contains #218/#219" while `#218` inside it had reverted SK-EN-HTO-001 `active:true→false` — ancestry saw both commits present and called it clean; it silently disarmed a live backstop. **A safety field's VALUE must be pinned, not just its commit's presence** — `signed_clinical_fields.json` + the deploy clinical-surface diff (control #6) are the value-level check that ancestry cannot be.

**STANDING CONVENTION (crisis-probe attribution) — established 2026-07-13:** a crisis/safety probe MUST assert **which control fired** — the firing rule named in `X-Sage-Crisis-Flags` (and the node path) — **not just that crisis was reached.** Outcomes have redundant causes: "reaches crisis_response" is satisfied by the deterministic backstop OR the LLM intent layer, so an outcome-only probe cannot verify a *specific* control — it verifies an outcome, and a disarmed control hides behind a working redundant one (exactly how this incident stayed invisible: the disarmed deterministic rule was covered by the LLM layer). Concretely: (a) a probe records `X-Sage-Crisis-Flags` + path and asserts the *expected firing layer*, not just `[[CRISIS_DETECTED]]`; (b) any deploy carrying a change to a safety rule file **re-probes with attribution after** — a control verified once can be silently reverted by a later deploy (see the ancestry corollary above), so verification is per-deploy, not once-ever.

**STANDING CONVENTION (prod-state claims must cite) — established 2026-07-13:** **any claim in a report about what production is running or did MUST cite the provenance entry or the live-endpoint read it derives from. No citation → no claim; write "unverified" instead.** This is the mechanical fix for a demonstrated PATTERN, not a one-off: twice in four days a confident negative — "prod held on 762" (2026-07-10) and "active:true never deployed" (2026-07-13) — was asserted from *absence of a memory of deploying* rather than from the record, and the second came ONE TURN after the lesson was set. That proves resolve doesn't fix it; a citation requirement does — it makes the miss impossible to commit *silently* rather than relying on remembering not to. A prod-state sentence without a `/health/version` read, a provenance Entry, or an ancestry check behind it is a hypothesis, and must be written as one.

**STANDING CONVENTION (credential handling) — established 2026-07-10:** deploy and introspection tooling never writes credentials to a shared temp path (`/tmp`, `/private/tmp`). Railway `variables` dumps, `DATABASE_URL`, service keys, and `SAGE_API_KEY` must not land in a world-readable shared location, even transiently. Use process substitution, environment injection, or a `0600` file inside the session's own workspace (the scratchpad), removed in the same command block that created it. Caught 2026-07-10: during the #272 deploy, prod `SAGE_API_KEY` + `DATABASE_URL` + `SUPABASE_SERVICE_KEY` were written to `/private/tmp/rw*.json` at umask 022 (mode 644, world-readable) for 15-40 minutes on a shared multi-session box; the read exposure could not be bounded after the fact, so the credentials were flagged for precautionary rotation. This is the same class as the out-of-band-psql rule: low-probability, high-consequence, and preventable by construction. The fix is structural (never write the secret to shared disk), not procedural (remember to delete it afterward).

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

## The test-harness / runtime boundary (harness must mirror the runtime)

**Rule:** *A test that constructs the state it asserts on cannot verify the state's transport.* Any mechanism
whose correctness depends on a framework boundary (a LangGraph channel merge, a JSON→prompt render, a
serialize→deserialize hop) MUST be driven ACROSS that boundary, on the compiled artifact — or it is untested,
regardless of test count.

**Why this is an architecture boundary, not a testing footnote:** the runtime has seams the unit test does not
reproduce. When the harness constructs state directly and asserts on it, it silently stubs out the exact
transport layer where the bug lives. Every green test then attests to logic that is correct in a world the
runtime is not.

**Three incarnations (this class recurs — it is the shape, not the instance):**
1. **Fixtures scoring synthetic candidates** — the eval harness scored hand-built candidates, not the ones the
   real generator produced; the metric was green on inputs the system never emits.
2. **The re-verdict driver missing a veto** — the driver reconstructed the decision state without the veto
   layer the runtime applies, so it verdicted a path the runtime cannot reach.
3. **D1 unit tests bypassing the channel layer (2026-07-20)** — `screen_question_text` was set inline in the
   test dict and asserted on directly; the one graph test drove crisis-mid-hold, never serve→answer. The
   undeclared-channel drop (skill_select→router) was invisible to every test and shipped to prod, caught only
   by the live behavioral probe. Fix: declare the channel, harden `check_state_channels` to see helper-module
   writes, and add `test_flip_probe_branches_on_compiled_graph` — the same branch list as the live probe,
   driven on the compiled graph via the real `_build_state` per-turn contract. When the automated test and the
   live probe assert the same things across the same boundary, a green suite finally means what the probe means.

**Operationally:** for any channel/seam-dependent mechanism, the acceptance test builds its input through the
real per-turn contract (`_build_state`), invokes the **compiled** graph (`build_graph(checkpointer=...)`), and
asserts on the state the runtime produces — not a state the test authored. `check_state_channels` is the static
half of this rule; the compiled-graph drive is the dynamic half. Neither alone is sufficient.

## Dark verification must run at PROD FLAG PARITY (a dark drive at different flags proves a config that isn't shipping)

**Rule (standing property of the dark-drive procedure):** a dark verification is only valid against
**prod-representative flag state.** The dark drive MUST snapshot prod's flag set and run against it. A dark
drive with different flags than prod verifies a *configuration that is not shipping* — and its "proven"
carries the same overclaim the word carried in the 2026-07-20 incident.

**Incarnation (2026-07-21 re-flip #2):** the D1 dark compiled-graph drive ran with
`MEDICAL_REDFLAG_GUARD_ENABLED` **off** (test default); prod has it **on**. An explicit-keyword red-flag
answer that prod catches at the SAFETY layer (`medical_response`, 998) instead fell through to the screen's
own `medical_guard` branch in the dark drive. The dark drive passed `[4]`; the live probe diverged. No user
was harmed (halt-first posture, zero exposure), but the dark drive's green was against a config prod doesn't
run. Fix: the enforce-graph test helper now sets `MEDICAL_REDFLAG_GUARD_ENABLED=True` to mirror prod; the
standing procedure is to mirror the full prod flag posture, not just the flag under test.

**Corollary — assert OUTCOMES, not ROUTES, where supremacy layers can pre-empt.** When more than one layer can
satisfy a safety property (a red-flag answer's 998 can arrive via the safety-layer guard OR the screen's own
backstop, depending on flag state), the acceptance assertion must check the **outcome** (998 delivered), not a
specific **route** (a particular `screen_branch_taken`). Asserting the route couples the test to a config-
dependent implementation path and produces a false red when a *stronger* path pre-empts. This is a small
generalization of the layer-attribution rule: attribute the guarantee to the property, and drive each layer's
own path with a case that actually reaches it (the subtle-red-flag case keeps the screen's backstop driven even
when the safety layer would otherwise pre-empt every obvious test — else that branch rots undriven, the
"disarmed by never being exercised" pattern).
