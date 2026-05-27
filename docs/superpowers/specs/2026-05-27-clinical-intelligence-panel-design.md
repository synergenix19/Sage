# Clinical Intelligence Panel — Design Spec

**Date:** 2026-05-27
**Status:** Approved, ready for implementation plan
**Scope:** Cross-project (sage-poc backend + cdai/apps/web frontend)
**Demo target:** Gitex split-screen presentation

---

## 1. Problem Statement

The Gitex demo runs a 6-turn narrative through the real cdai chat UI. The system produces rich clinical reasoning per turn (intent classification, skill routing, safety checks, RAG retrieval, output gating) but none of it is visible to the audience. The demo proves the system works but hides the architecture that makes it credible to CDA leadership, clinicians, and regulators.

The gap: no second screen surface showing the system's reasoning in real time.

---

## 2. Goal

Add a `/live` route to the cdai frontend that displays a live clinical intelligence panel. After each message the presenter sends in the chat UI, the panel updates automatically showing which graph nodes fired, the current clinical state, and a scrollable audit trail of all turns in the session.

This is simultaneously:
- The Gitex demo surface (right half of split screen)
- The v7 audit trail (output_gate §8) made visible
- The MVP admin analytics view (Technical Scoping Brief §4.1)
- The foundation row schema for Social Observation 2.0 population aggregation

---

## 3. Architecture and Data Flow

```
[cdai chat UI]  POST /chat {session_id, messages}
                      |
         [sage-poc FastAPI :8765]
                      |
         [LangGraph 8-node graph]
              |               |
     [crisis_response]   [output_gate]          ← two write points
              |               |
       asyncio.create_task(write_session_audit(state))
              |               |
              └───────┬───────┘
                      |
          [Supabase session_audit table]
                      |   (Postgres Realtime websocket)
          [/live — Next.js panel]
           follow-latest OR ?session= lock
```

Crisis path: `safety_check → crisis_response → END` (bypasses output_gate)
Normal path: all other routes terminate at `output_gate → END`

**Key invariant:** The audit write is fire-and-forget. `output_gate` does not await it. The user receives the response at normal latency; the panel update arrives 50-200ms later via the Supabase realtime channel.

**Session ID flow:** The cdai chat UI sends `session_id` in each `/chat` request body. That value propagates through `SageState` to `output_gate` and into every audit row. The panel subscribes filtered on `session_id`, either locked via `?session=` or following whichever `session_id` most recently inserted a row.

---

## 4. Database: Migration 009

**File:** `cdai/supabase/migrations/009_session_audit.sql`

> Note: `008_secondary_intent.sql` already exists. The migration was renumbered from the spec draft.

```sql
create table session_audit (
  id                    uuid        primary key default gen_random_uuid(),
  inserted_at           timestamptz not null    default now(),
  session_id            text        not null,
  turn_number           integer     not null,
  node_path             text[]      not null    default '{}',
  primary_intent        text,
  secondary_intent      text,
  intent_confidence     numeric,
  active_skill_id       text,
  active_step_id        text,
  skill_match_method    text,
  knowledge_source      text,
  knowledge_passage_ids text[]               default '{}',
  knowledge_abstain     boolean,
  crisis_state          text,
  crisis_flags          text[]               default '{}',
  clinical_flags        text[]               default '{}',
  engagement            integer,
  emotional_intensity   integer,
  model_version         text,
  latency_ms            integer,
  user_id               uuid        references auth.users(id)
);

-- RLS: admin read only; writes use service role key from sage-poc
alter table session_audit enable row level security;

create policy "admin_read" on session_audit
  for select using (
    exists (
      select 1 from user_roles
      where user_id = auth.uid() and role = 'admin'
    )
  );

-- Realtime subscription performance
create index session_audit_session_turn on session_audit (session_id, turn_number);
create index session_audit_recent      on session_audit (inserted_at desc);

-- Enable realtime
alter publication supabase_realtime add table session_audit;
```

**Schema constraints:**
- No `content` or `response_text` columns. This table holds clinical metadata only, not conversation text. PII boundary is preserved.
- `user_id` is nullable. The POC may run unauthenticated sessions during the demo; the column is present for production use.
- `node_path` stores the array as-is from `state["path"]`. The frontend derives which of the 8 nodes fired by comparing against the fixed ordered node list.
- Writes bypass RLS via the service role key held only in `sage-poc/.env`. The service key never reaches the browser.
- Verify the Supabase project's existing publication before applying. If `supabase_realtime` already exists, add the table to it rather than creating a duplicate.

---

## 5. Backend Changes

### 5a. `sage-poc/src/sage_poc/state.py`

Add one field to `SageState`:

```python
turn_number: int  # default 0; incremented by safety_check_node on every message
```

### 5b. `safety_check_node`

`safety_check_node` is the first node every message hits. Include `turn_number` in its returned partial state dict:

```python
"turn_number": state.get("turn_number", 0) + 1,
```

No other node touches this field. It flows read-only through the rest of the graph.

### 5c. New module: `sage-poc/src/sage_poc/audit.py`

Uses `httpx` (existing dependency) to POST to Supabase's PostgREST endpoint. No new Python package required.

```python
import logging
import os
import httpx
from sage_poc.state import SageState

logger = logging.getLogger(__name__)

_URL = os.environ.get("SUPABASE_URL")
_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
_HEADERS = {
    "apikey": _KEY or "",
    "Authorization": f"Bearer {_KEY or ''}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


async def write_session_audit(state: SageState) -> None:
    if not _URL or not _KEY:
        return  # audit disabled, no Supabase credentials in this environment

    row = {
        "session_id":             state.get("session_id", ""),
        "turn_number":            state.get("turn_number", 0),
        "node_path":              state.get("path") or [],
        "primary_intent":         state.get("primary_intent"),
        "secondary_intent":       state.get("secondary_intent"),
        "intent_confidence":      state.get("intent_confidence"),
        "active_skill_id":        state.get("active_skill_id") or None,
        "active_step_id":         state.get("active_step_id") or None,
        "skill_match_method":     state.get("skill_match_method") or None,
        "knowledge_source":       state.get("knowledge_source") or None,
        "knowledge_passage_ids":  state.get("knowledge_passage_ids") or [],
        "knowledge_abstain":      state.get("knowledge_abstain"),
        "crisis_state":           state.get("crisis_state"),
        "crisis_flags":           state.get("crisis_flags") or [],
        "clinical_flags":         state.get("clinical_flags") or [],
        "engagement":             state.get("engagement"),
        "emotional_intensity":    state.get("emotional_intensity"),
        "model_version":          state.get("model_version"),
        "latency_ms":             state.get("latency_ms"),
        "user_id":                state.get("user_id") or None,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{_URL}/rest/v1/session_audit",
                headers=_HEADERS,
                json=row,
            )
            r.raise_for_status()
    except Exception as exc:
        logger.error("session_audit write failed: %s", exc)
```

**Environment additions to `sage-poc/.env`:**
```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
```
These already exist in the cdai environment. Copy from there, same Supabase project.

**`latency_ms` gap:** `output_gate` does not currently have access to total turn latency. Ship as `None` for the demo. Post-Gitex: `server.py` measures `time.monotonic()` delta from request receipt and stores it in `SageState` before invoking the graph.

### 5d. Audit write locations — `output_gate` and `crisis_response`

**Why two locations:** `crisis_response` routes directly to `END` (`graph.py:136`), bypassing `output_gate`. Both crisis entry points (from `safety_check` and from `intent_route`) share this edge. If the write were only in `output_gate`, Turn 6 (third-party concern, the most safety-critical turn in the demo) would produce no audit row and the panel would go dark at exactly the wrong moment.

**`output_gate` node** — covers all non-crisis paths:

```python
import asyncio
from sage_poc.audit import write_session_audit

# Last statement before return:
asyncio.create_task(write_session_audit(state))
```

**`_crisis_response_node` in `graph.py`** — covers crisis short-circuit paths. The node already sets `gate_path: "crisis"` and `crisis_state: "monitoring"` in its return dict. Pass a merged state that includes the updated path so the audit row reflects the actual traversal:

```python
import asyncio
from sage_poc.audit import write_session_audit

# After composing the return dict, before returning:
asyncio.create_task(write_session_audit({**state, "path": path, "gate_path": "crisis", "crisis_state": "monitoring"}))
```

`turn_number` is already correct here — `safety_check_node` increments it before any routing decision is made.

The panel will show `node_path: ["safety_check", "crisis_response"]` for crisis turns, with only Safety and Crisis nodes lit up in `NodePathVisualizer`. This is the correct visualization: the short-circuit path tells the safety story more clearly than a full 8-node traversal would.

---

## 6. Frontend

### 6a. File structure

```
cdai/apps/web/
  app/
    (clinical)/
      live/
        layout.tsx              # minimal full-screen layout, no sidebar
        page.tsx                # "use client", reads ?session= param
  components/
    clinical-live/
      node-path-visualizer.tsx
      clinical-state-card.tsx
      audit-log.tsx
      use-session-audit.ts      # realtime subscription hook
  lib/
    types/session-audit.ts      # shared AuditRow type
```

The `(clinical)` route group places `/live` outside of `app/admin/`, so it does not inherit the admin sidebar layout. The existing auth middleware protects it with the same `is_admin` check.

### 6b. AuditRow type (`lib/types/session-audit.ts`)

```typescript
export type AuditRow = {
  id: string;
  inserted_at: string;
  session_id: string;
  turn_number: number;
  node_path: string[];
  primary_intent: string | null;
  secondary_intent: string | null;
  intent_confidence: number | null;
  active_skill_id: string | null;
  active_step_id: string | null;
  skill_match_method: string | null;
  knowledge_source: string | null;
  knowledge_passage_ids: string[];
  knowledge_abstain: boolean | null;
  crisis_state: string | null;
  crisis_flags: string[];
  clinical_flags: string[];
  engagement: number | null;
  emotional_intensity: number | null;
  model_version: string | null;
  latency_ms: number | null;
};
```

### 6c. `use-session-audit` hook

Manages Supabase realtime subscription and exposes `{ rows, latestRow, activeSessionId, status }`.

**Session mode logic:**

```
On mount:
  if ?session= present (lockedSessionId)
    → fetch all rows for that session ordered by turn_number ASC
    → status = "locked"
  else (follow-latest)
    → fetch last 20 rows DESC, infer latest session_id from rows[0]
    → filter to only that session's rows, reverse to ASC
    → status = "live"

On INSERT event:
  if locked
    → reject rows where session_id !== lockedSessionId
    → append matching row to rows
  if follow-latest
    → same session_id as activeSessionRef.current
        → append row
    → new session_id
        → reset rows to [newRow]
        → update activeSessionRef.current and setActiveSessionId

On subscription status change:
  SUBSCRIBED     → status = "live" or "locked"
  CHANNEL_ERROR  → status = "reconnecting"
```

A `useRef` tracks `activeSessionId` inside the subscription closure to avoid stale closure bugs when a new session arrives.

**Exported shape:**
```typescript
{
  rows: AuditRow[];
  latestRow: AuditRow | null;
  activeSessionId: string | null;
  status: "waiting" | "live" | "locked" | "reconnecting";
}
```

### 6d. `NodePathVisualizer`

**Correct 8-node ordered list:**
```
safety_check → intent_route → low_confidence → skill_select →
skill_executor → knowledge_retrieve → freeflow_respond → output_gate
```

**Three visual states:**
- **Fired (teal/bright):** node appears in `latestRow.node_path`
- **Skipped (dim gray):** node not in `node_path`
- **Connectors:** drawn only between consecutive fired nodes, not across skipped nodes

This makes branching paths visible. Turn 1 (freeflow) lights: `safety_check → intent_route → freeflow_respond → output_gate`. Turn 5 (knowledge) lights: `safety_check → intent_route → skill_select → knowledge_retrieve → freeflow_respond → output_gate`. The audience sees the path change per message and understands the graph is not linearly traversed.

Node labels for display:
```typescript
const NODE_LABELS: Record<string, string> = {
  safety_check:       "Safety",
  intent_route:       "Intent",
  low_confidence:     "Low Conf.",
  skill_select:       "Skill Select",
  skill_executor:     "Skill Exec",
  knowledge_retrieve: "Knowledge",
  freeflow_respond:   "Respond",
  output_gate:        "Gate",
};
```

### 6e. `ClinicalStateCard`

Two-column card showing `latestRow` state. A conditional third column appears only when `knowledge_source` is non-empty.

**Standard layout (Turns 1-4, Turn 6):**
```
Left                      Right
────────────────────────  ───────────────────────
Intent   new_skill         Skill    grounding_5_4_3_2_1
Crisis   none              Step     step_2
Engage   ████░  7/10       Match    semantic (0.89)
Intensity███░░  5/10       Gate     standard
Flags    —                 Model    claude-sonnet-4-6
                           Latency  —
```

**With knowledge column (Turn 5 only):**
```
Left            Right            Knowledge
──────────────  ───────────────  ─────────────────────────
Intent  info    Skill    —       Source    node_6
Crisis  none    Step     —       Passages  cbt-001-en-000
Engage  ████░   Gate     std               cbt-001-en-001
Intensity███░   Model    ...     Abstain   false
Flags   —       Latency  —
```

The knowledge column's appearance on Turn 5 is itself the story: a visible structural change shows the system pivoting from therapeutic delivery to grounded knowledge retrieval.

**Crisis color coding:**
- `crisis_state = "none"` → green indicator
- `crisis_state = "monitoring"` → amber indicator
- `crisis_state = "active"` → red indicator
- `crisis_flags` non-empty → rendered as pill badges next to the indicator
- `clinical_flags` non-empty → rendered as smaller pill badges in their own row

Empty arrays render as "—" not blank.

### 6f. `AuditLog`

Scrollable table, newest turn at top. Columns:

```
Turn | Intent | Skill | Step | Crisis | Eng | Int | Gate | ms
```

Each row is one `AuditRow`. The table grows with each realtime insert. No pagination needed at demo scale (6 turns). With `?session=`, the full session history loads on mount.

### 6g. Page layout

```
┌─────────────────────────────────────────────────────┐
│  ● LIVE  SAGE Clinical Intelligence  [session-id]   │
├─────────────────────────────────────────────────────┤
│  NODE PATH (Turn N)                                 │
│  [Safety]─[Intent]───────────[Respond]─[Gate]       │
│              (Skill Sel, Exec, Knowledge: dim)       │
├────────────────────────┬────────────────────────────┤
│  CLINICAL STATE        │  TURN DETAIL               │
│  (left col)            │  (right col, ±knowledge)   │
├────────────────────────┴────────────────────────────┤
│  AUDIT LOG                                          │
│  T3 · new_skill · grounding · step_2 · none · 843ms │
│  T2 · new_skill · grounding · step_1 · none · 912ms │
│  T1 · general_chat · — · — · none · 622ms           │
└─────────────────────────────────────────────────────┘
```

Header shows: live/locked indicator dot, session ID (truncated to 20 chars), "Waiting for session..." placeholder until first row arrives.

---

## 7. Error Handling

### Backend

| Failure | Behaviour |
|---|---|
| `SUPABASE_URL` or `SUPABASE_SERVICE_KEY` absent | `write_session_audit` returns immediately; no write, no log |
| Network error or 5s timeout | `logger.error(...)`, coroutine exits; no propagation to the turn |
| HTTP 4xx/5xx from PostgREST | `raise_for_status()` raises, caught by outer `except Exception`, logged |

The `asyncio.create_task` wrapper ensures a failure in `write_session_audit` cannot propagate to the turn response. The inner `try/except` ensures Python does not emit an unhandled-exception-in-task warning.

### Frontend

| State | Panel behaviour |
|---|---|
| `status = "waiting"` | Full-panel placeholder: "Waiting for session, start a conversation in the chat window" |
| `status = "reconnecting"` | Header shows amber dot + "Reconnecting..."; last known data stays visible |
| `?session=` present, no rows found | "Session not found" message with link to `/live` (follow-latest) |
| Supabase realtime channel error | Auto-resubscribes once; subsequent failures use Supabase client built-in backoff |

---

## 8. Testing

### Backend

**Unit tests (`audit.py`):**
- Mock `httpx.AsyncClient.post`. Verify row dict maps every `SageState` field correctly.
- Verify early-return when env vars are absent (no mock needed, just omit the vars).
- Verify a network exception is caught and logged without raising.

**Unit test (`turn_number`):**
- In existing `safety_check_node` tests, assert `state["turn_number"]` increments 0→1 on first call, 1→2 on second.

**Integration test (marked `pytest.mark.integration`):**
- Run a single turn through the POC server using the existing `httpx` test pattern.
- Assert a row appears in `session_audit` with correct `session_id`, `turn_number = 1`, a non-empty `node_path` array, a non-null `primary_intent`, and `crisis_state` matching the expected value for the test message.
- Gate with `pytest.mark.integration`; CI without credentials skips cleanly.

**Existing 982 tests:** Unaffected. The `os.environ.get()` guard means importing `audit.py` in any environment without credentials is a no-op.

### Frontend

**Vitest unit tests per component:**
- `NodePathVisualizer`: all 8 nodes fired, 4-node path (freeflow), 3-node path (crisis short-circuit), connector gaps between non-consecutive fired nodes.
- `ClinicalStateCard`: knowledge column visible, knowledge column hidden, `crisis_state = "active"` (red indicator), `crisis_flags` non-empty (pill badges), all null fields (renders "—" not blank).
- `AuditLog`: single row, multiple rows, empty state.

**Hook unit test (`use-session-audit`):**
- Mock Supabase client. Verify follow-latest fetches and sets `activeSessionId` from the most recent row.
- Verify locked mode rejects rows from other sessions.
- Verify a new `session_id` in follow-latest mode resets `rows` to `[newRow]`.

**Playwright integration test:**
- POST a chat message to the POC server, wait for a new row in `session_audit`, assert the `/live` panel updates with correct intent and node path.
- Requires POC server running; marked as Playwright integration test.

---

## 9. Known Gaps and Deferred Items

| Item | Disposition |
|---|---|
| `latency_ms` in `SageState` | Ship as `null` for demo. Post-Gitex: `server.py` measures `time.monotonic()` delta from request receipt, stores in state. |
| Session picker UI for clinician review | Deferred. Post-demo, `/live?session=<id>` is the review surface. A session list page is a separate feature. |
| Population aggregation queries on `session_audit` | Deferred to Social Observation 2.0 sprint. The schema supports it today. |
| Arabic detection indicator (translator removed from node list) | Arabic turns show `detected_language` if surfaced via future addition to `session_audit` schema. Not needed for demo. |
| Crisis path audit write | Resolved in spec: `_crisis_response_node` in `graph.py` gets a second `write_session_audit` call with merged state. Crisis turns produce `node_path: ["safety_check", "crisis_response"]`. |
| Rate limiting on PostgREST inserts | Not needed at demo scale. Production volume will determine if batching or a dedicated ingest service is required. |
