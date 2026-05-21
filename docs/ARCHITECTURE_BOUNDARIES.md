# Architecture Boundaries: POC vs. Production

**Confirmed:** 2026-05-22  
**Relevant spec sections:** v7 §5.2 (checkpointing), §6 (enriched state), §8 (audit trail)

---

## Current POC Architecture

The LangGraph graph is **stateless with respect to sessions**. `server.py` receives `session_id` from the client but explicitly discards it before graph invocation:

```python
# session_id is received from the client but intentionally not stored in SageState —
# the graph has no concept of sessions; persistence is the frontend's responsibility.
session_id: str
```

`_build_state()` rebuilds the full conversation history from `req.messages` on every invocation. Supabase is the sole persistence layer, written by the Next.js `/api/chat` route after each turn. There is no LangGraph checkpoint store.

This is correct for the POC. It is not suitable for production.

---

## Three Production Blockers

### 1. Enriched state has no home

The six §6 components (User Therapeutic Profile, Active Issues List, Clinical Flags, Engagement Scoring, Risk Trajectory, Cultural Context) are computed incrementally across turns. A stateless graph that rebuilds from raw messages each turn means either:

- **(a)** Full recomputation of all state signals every turn: expensive and non-deterministic across LLM calls, or  
- **(b)** Enriched state lives in Supabase alongside messages but outside the graph: creates split-brain between what the graph "knows" and what is persisted.

**Production requirement:** LangGraph native checkpointing via Azure Cosmos DB (v7 §5.2), where `SageState` including all enriched state is persisted after each turn and loaded at the start of the next. "Session state survives days" is a hard requirement, not a nice-to-have.

### 2. Client-side audit trail

The output_gate (Node 8) audit payload `{path, skill, step, model_version, flags, latency}` is currently returned to Next.js and written to Supabase by the frontend route. For a clinical system, this is insufficient: audit writes must happen server-side within the graph invocation, to a store the frontend cannot read or modify. A frontend that can write its own audit records cannot produce tamper-evident logs.

**Production requirement:** Node 8 writes audit records directly to a server-side store (Cosmos DB or equivalent) before the response leaves the graph. The frontend receives metadata headers for display purposes only, not as the source of record.

### 3. History-as-payload breaks at scale

Sending the full conversation on every request works at roughly 10 turns in English. At 30+ turns in Khaleeji Arabic (longer token sequences than English), this consumes context window budget that the 6-layer prompt composition (L1-L6) needs for its own operation.

**Production requirement:** Windowed history -- last 5-8 turns verbatim, older turns summarised into a persistent summary block. This requires persistent state to track what has already been summarised, which loops back to blocker 1: the graph must hold state between turns.

---

## Cross-Session Contamination Risk

This was identified during the Fix B investigation (2026-05-22). If stale messages from a prior session survive a soft navigation into a new session (the bug Fix B addresses), they are sent to the LangGraph backend under the new `session_id`. The Next.js route persists them to Supabase against the wrong session permanently.

That corrupted Supabase record feeds forward into `check_user_history` (Tool 2), causing the LLM to reference therapeutically wrong context in future sessions. The contamination propagates forward across sessions.

Fix B (`key={activeSession.id}` on `ChatFadeIn` in `apps/web/app/(app)/chat/page.tsx`) prevents this by forcing a full React remount -- and therefore a full state reset -- whenever the active session ID changes. This is a clinical safety fix, not a UI polish fix.

---

## Migration Path

When the POC transitions to the stateful production graph:

| Layer | POC (current) | Production target |
|---|---|---|
| Session state | Rebuilt from `req.messages` each turn | LangGraph checkpoint loaded at turn start |
| Persistence store | Supabase (written by Next.js route) | Azure Cosmos DB (written by graph, v7 §5.2) |
| Audit writes | Frontend route, after response | Node 8, server-side, before response exits graph |
| Conversation history | Full payload per request | Windowed: last 5-8 turns + summary block |
| Enriched state | Not implemented | Loaded from checkpoint, updated per turn |

The transition is already scoped in the v7 spec. The stateless pattern is fit for purpose while the POC validates routing architecture and skill execution before the Falcon self-hosting stack is ready (Experiment 4.1, Week 6-8).
