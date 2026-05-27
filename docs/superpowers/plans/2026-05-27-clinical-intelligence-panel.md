# Clinical Intelligence Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live `/live` route to the cdai frontend that displays clinical reasoning (node path, intent, skill, safety state, RAG retrieval) in real time after each message, powered by a `session_audit` Supabase table written to by `output_gate` and `crisis_response` in the sage-poc backend.

**Architecture:** `output_gate` and `crisis_response` fire-and-forget an async write to Supabase (`session_audit`) after each turn. The `/live` Next.js route subscribes to new rows via Supabase Realtime and renders three components: `NodePathVisualizer`, `ClinicalStateCard`, and `AuditLog`. Default mode follows the latest session; `?session=` URL param locks to a specific session.

**Tech Stack:** Python/FastAPI (sage-poc), LangGraph, httpx, Supabase (Postgres + Realtime), Next.js 15, React 19, TypeScript, Vitest + React Testing Library, Playwright.

> **Migration correction:** The spec draft said "Migration 008" but `008_secondary_intent.sql` already exists. This plan uses **009**.

---

## File Map

**sage-poc (backend):**
- Create: `cdai/supabase/migrations/009_session_audit.sql`
- Modify: `sage-poc/src/sage_poc/state.py` — add `turn_number: int`
- Modify: `sage-poc/src/sage_poc/nodes/safety_check.py` — increment `turn_number` in return dict
- Create: `sage-poc/src/sage_poc/audit.py` — `write_session_audit()` async function
- Modify: `sage-poc/src/sage_poc/nodes/output_gate.py` — add `asyncio.create_task(write_session_audit(...))`
- Modify: `sage-poc/src/sage_poc/graph.py` — add `asyncio.create_task(write_session_audit(...))` in `_crisis_response_node`
- Create: `sage-poc/tests/test_audit.py` — unit tests for `audit.py`
- Modify: `sage-poc/tests/test_nodes.py` — add `turn_number` to `make_state()` defaults, add increment test
- Modify: `sage-poc/tests/test_state.py` — add `turn_number` to existing inline state dicts

**cdai/apps/web (frontend):**
- Create: `cdai/apps/web/lib/types/session-audit.ts` — `AuditRow` type
- Modify: `cdai/apps/web/middleware.ts` — protect `/live` with `is_admin` check
- Create: `cdai/apps/web/components/clinical-live/use-session-audit.ts` — realtime hook
- Create: `cdai/apps/web/components/clinical-live/node-path-visualizer.tsx`
- Create: `cdai/apps/web/components/clinical-live/clinical-state-card.tsx`
- Create: `cdai/apps/web/components/clinical-live/audit-log.tsx`
- Create: `cdai/apps/web/app/(clinical)/live/layout.tsx`
- Create: `cdai/apps/web/app/(clinical)/live/page.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/node-path-visualizer.test.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/clinical-state-card.test.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/audit-log.test.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/use-session-audit.test.ts`

---

### Task 1: Database migration 009

**Files:**
- Create: `cdai/supabase/migrations/009_session_audit.sql`

- [ ] **Step 1: Create migration file**

```sql
-- 009_session_audit.sql
-- Per-turn clinical audit trail. Written by output_gate and crisis_response in sage-poc.
-- No conversation text — clinical metadata only. PII boundary preserved.
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

alter table session_audit enable row level security;

create policy "admin_read" on session_audit
  for select using (
    exists (
      select 1 from user_roles
      where user_id = auth.uid() and role = 'admin'
    )
  );

create index session_audit_session_turn on session_audit (session_id, turn_number);
create index session_audit_recent      on session_audit (inserted_at desc);

alter publication supabase_realtime add table session_audit;
```

- [ ] **Step 2: Apply migration**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
supabase db push
```

Expected: migration applies without error. If `supabase_realtime` publication does not exist, replace the last line with `create publication supabase_realtime for table session_audit;`.

- [ ] **Step 3: Verify table exists**

```bash
supabase db diff --schema public 2>/dev/null | grep session_audit || echo "check supabase dashboard"
```

- [ ] **Step 4: Commit**

```bash
git add cdai/supabase/migrations/009_session_audit.sql
git commit -m "feat: add session_audit migration 009 for clinical intelligence panel"
```

---

### Task 2: Add `turn_number` to SageState and safety_check_node

**Files:**
- Modify: `sage-poc/src/sage_poc/state.py`
- Modify: `sage-poc/src/sage_poc/nodes/safety_check.py`
- Modify: `sage-poc/tests/test_nodes.py`
- Modify: `sage-poc/tests/test_state.py`

- [ ] **Step 1: Write the failing test for turn_number increment**

In `sage-poc/tests/test_nodes.py`, add to the bottom:

```python
@pytest.mark.asyncio
async def test_safety_check_increments_turn_number():
    state = make_state(raw_message="I feel stressed", turn_number=0)
    result = await safety_check_node(state)
    assert result["turn_number"] == 1

@pytest.mark.asyncio
async def test_safety_check_increments_turn_number_from_existing():
    state = make_state(raw_message="I feel stressed", turn_number=3)
    result = await safety_check_node(state)
    assert result["turn_number"] == 4
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py::test_safety_check_increments_turn_number tests/test_nodes.py::test_safety_check_increments_turn_number_from_existing -v
```

Expected: FAIL — `KeyError: 'turn_number'` or `AssertionError`.

- [ ] **Step 3: Add `turn_number` to `make_state()` defaults in test_nodes.py**

In the `make_state()` function defaults dict, add:

```python
"turn_number": 0,
```

(Add it after `"turn_count": 0,`)

- [ ] **Step 4: Add `turn_number` to SageState**

In `sage-poc/src/sage_poc/state.py`, add after `turn_count`:

```python
    turn_count: int
    turn_number: int   # incremented by safety_check_node on every message; used for session_audit
```

- [ ] **Step 5: Add `turn_number` to safety_check_node return dict**

In `sage-poc/src/sage_poc/nodes/safety_check.py`, find the `return {` statement (around line 157). Add `"turn_number"` to the returned dict:

```python
    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "third_party_crisis": bool(third_party_flags),
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "engagement_trajectory": engagement_trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
        "turn_number": state.get("turn_number", 0) + 1,
    }
```

- [ ] **Step 6: Update inline state dicts in test_state.py**

In `sage-poc/tests/test_state.py`, add `"turn_number": 0,` to each of the two inline state dicts (in `test_state_has_required_fields` and `test_state_path_is_list`). Add after `"turn_count": 0,` in each.

- [ ] **Step 7: Run the new tests to verify they pass**

```bash
uv run pytest tests/test_nodes.py::test_safety_check_increments_turn_number tests/test_nodes.py::test_safety_check_increments_turn_number_from_existing -v
```

Expected: both PASS.

- [ ] **Step 8: Run full test suite to verify no regressions**

```bash
uv run pytest tests/ -x --ignore=tests/test_embedding.py -q
```

Expected: all existing tests pass. If `test_state.py` fails due to missing `turn_number` key in a dict, add `"turn_number": 0` to the relevant dict.

- [ ] **Step 9: Commit**

```bash
git add sage-poc/src/sage_poc/state.py sage-poc/src/sage_poc/nodes/safety_check.py sage-poc/tests/test_nodes.py sage-poc/tests/test_state.py
git commit -m "feat: add turn_number to SageState, increment in safety_check_node"
```

---

### Task 3: Create `audit.py`

**Files:**
- Create: `sage-poc/src/sage_poc/audit.py`
- Create: `sage-poc/tests/test_audit.py`

- [ ] **Step 1: Write the failing tests**

Create `sage-poc/tests/test_audit.py`:

```python
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_audit_state(**kwargs):
    defaults = {
        "session_id": "test-session-001",
        "turn_number": 1,
        "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.92,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "engagement": 7,
        "emotional_intensity": 4,
        "model_version": "claude-sonnet-4-6",
        "latency_ms": None,
        "user_id": None,
        "gate_path": "standard",
    }
    return {**defaults, **kwargs}


@pytest.mark.asyncio
async def test_write_skips_when_url_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    # Re-import forces module-level vars to re-read env
    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)
    # Should return without error, no HTTP call
    await audit_mod.write_session_audit(make_audit_state())


@pytest.mark.asyncio
async def test_write_posts_correct_row(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    posted_json = {}

    class MockResponse:
        def raise_for_status(self): pass

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers, json):
            posted_json.update(json)
            return MockResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        await audit_mod.write_session_audit(make_audit_state(
            session_id="sess-abc",
            turn_number=2,
            primary_intent="new_skill",
            active_skill_id="box_breathing",
            crisis_state="none",
            crisis_flags=[],
            clinical_flags=[],
        ))

    assert posted_json["session_id"] == "sess-abc"
    assert posted_json["turn_number"] == 2
    assert posted_json["primary_intent"] == "new_skill"
    assert posted_json["active_skill_id"] == "box_breathing"
    assert posted_json["node_path"] == ["safety_check", "intent_route", "freeflow_respond", "output_gate"]
    assert posted_json["crisis_state"] == "none"
    assert posted_json["crisis_flags"] == []
    assert posted_json["clinical_flags"] == []
    assert isinstance(posted_json["knowledge_passage_ids"], list)


@pytest.mark.asyncio
async def test_write_extracts_passage_ids(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    posted_json = {}

    class MockResponse:
        def raise_for_status(self): pass

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers, json):
            posted_json.update(json)
            return MockResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        await audit_mod.write_session_audit(make_audit_state(
            knowledge_passages=[
                {"source_id": "cbt-001-en-000", "text": "...", "citation": "x", "relevance_score": 0.9},
                {"source_id": "cbt-001-en-001", "text": "...", "citation": "x", "relevance_score": 0.8},
            ],
            knowledge_source="node_6",
        ))

    assert posted_json["knowledge_passage_ids"] == ["cbt-001-en-000", "cbt-001-en-001"]
    assert posted_json["knowledge_source"] == "node_6"


@pytest.mark.asyncio
async def test_write_swallows_network_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    class BrokenClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            raise ConnectionError("network down")

    with patch("httpx.AsyncClient", return_value=BrokenClient()):
        # Must not raise
        await audit_mod.write_session_audit(make_audit_state())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_audit.py -v
```

Expected: ImportError or ModuleNotFoundError for `sage_poc.audit`.

- [ ] **Step 3: Create `audit.py`**

Create `sage-poc/src/sage_poc/audit.py`:

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
        return

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
        "knowledge_passage_ids":  [p.get("source_id", "") for p in state.get("knowledge_passages") or []],
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_audit.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sage-poc/src/sage_poc/audit.py sage-poc/tests/test_audit.py
git commit -m "feat: add audit.py with write_session_audit fire-and-forget"
```

---

### Task 4: Wire audit write into output_gate and crisis_response

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/output_gate.py`
- Modify: `sage-poc/src/sage_poc/graph.py`

- [ ] **Step 1: Write the failing test for output_gate**

In `sage-poc/tests/test_audit.py`, add:

```python
@pytest.mark.asyncio
async def test_output_gate_schedules_audit_write(monkeypatch):
    """output_gate must schedule a write_session_audit task."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    write_calls = []

    async def mock_write(state):
        write_calls.append(state)

    monkeypatch.setattr("sage_poc.audit.write_session_audit", mock_write)

    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.tests.test_nodes import make_state  # reuse existing helper

    state = make_state(
        raw_message="hello",
        response_en="I hear you.",
        gate_path="standard",
        path=["safety_check", "intent_route", "freeflow_respond"],
        turn_number=1,
        session_id="test-sess",
        user_id=None,
    )

    await output_gate_node(state)
    # Give the event loop a tick to run the task
    await asyncio.sleep(0)
    assert len(write_calls) == 1
    assert write_calls[0].get("session_id") == "test-sess"
```

Run to see it fail:

```bash
uv run pytest tests/test_audit.py::test_output_gate_schedules_audit_write -v
```

Expected: FAIL — no audit write call recorded.

- [ ] **Step 2: Add import and create_task to output_gate.py**

In `sage-poc/src/sage_poc/nodes/output_gate.py`, the function already imports `asyncio` at the top. Add `write_session_audit` import at the top:

```python
from sage_poc.audit import write_session_audit
```

Then find the `return {` block at the end of `output_gate_node` (around line 217). Insert the `create_task` call immediately before the `return`:

```python
    asyncio.create_task(write_session_audit({**state, "path": path, "gate_path": gate_path or "standard"}))

    return {
        "response": final_response,
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": next_turn,
        "conversation_history": new_history,
        "conversation_summary": new_summary,
        "cultural_output_violations": cultural_output_violations,
    }
```

- [ ] **Step 3: Write the failing test for crisis_response**

In `sage-poc/tests/test_audit.py`, add:

```python
@pytest.mark.asyncio
async def test_crisis_response_schedules_audit_write(monkeypatch):
    """crisis_response must schedule a write_session_audit task on crisis paths."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    write_calls = []

    async def mock_write(state):
        write_calls.append(state)

    monkeypatch.setattr("sage_poc.audit.write_session_audit", mock_write)

    # Import graph to access _crisis_response_node
    from sage_poc import graph as graph_mod

    state = {
        "path": ["safety_check"],
        "session_id": "crisis-sess",
        "turn_number": 2,
        "detected_language": "en",
        "crisis_flags": ["S1_keyword"],
        "clinical_flags": [],
        "active_skill_id": None,
        "crisis_state": "none",
        "conversation_history": [],
        "raw_message": "I want to end it",
        "message_en": "I want to end it",
    }

    graph_mod._crisis_response_node(state)
    await asyncio.sleep(0)
    assert len(write_calls) == 1
    assert write_calls[0].get("session_id") == "crisis-sess"
    assert "crisis_response" in write_calls[0].get("path", [])
    assert write_calls[0].get("crisis_state") == "monitoring"
```

Run to see it fail:

```bash
uv run pytest tests/test_audit.py::test_crisis_response_schedules_audit_write -v
```

Expected: FAIL — no write call recorded.

- [ ] **Step 4: Add import and create_task to graph.py**

In `sage-poc/src/sage_poc/graph.py`, add to the top-level imports (after the existing imports):

```python
import asyncio
from sage_poc.audit import write_session_audit
```

Then in `_crisis_response_node`, after the line `path = state["path"] + ["crisis_response"]` (line 37) and before the `if AUDIT_LOG_ENABLED:` block, add:

```python
    asyncio.create_task(write_session_audit({
        **state,
        "path": path,
        "gate_path": "crisis",
        "crisis_state": "monitoring",
    }))
```

- [ ] **Step 5: Run all audit tests**

```bash
uv run pytest tests/test_audit.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 6: Run full suite to verify no regressions**

```bash
uv run pytest tests/ -x --ignore=tests/test_embedding.py -q
```

Expected: all existing tests pass.

- [ ] **Step 7: Commit**

```bash
git add sage-poc/src/sage_poc/nodes/output_gate.py sage-poc/src/sage_poc/graph.py sage-poc/tests/test_audit.py
git commit -m "feat: wire session_audit writes into output_gate and crisis_response"
```

---

### Task 5: Backend integration test

**Files:**
- Create: `sage-poc/tests/test_session_audit_integration.py`

This test requires `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in the environment. It is skipped automatically in CI when those vars are absent.

- [ ] **Step 1: Create the integration test**

```python
# tests/test_session_audit_integration.py
import os
import asyncio
import pytest
import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="SUPABASE_URL and SUPABASE_SERVICE_KEY required for integration test",
)
@pytest.mark.asyncio
async def test_session_audit_row_written_after_turn():
    """Full turn through the POC server produces a session_audit row with correct fields."""
    import time
    session_id = f"integration-test-{int(time.time())}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "http://localhost:8765/chat",
            json={
                "messages": [{"role": "user", "content": "I feel a bit stressed today"}],
                "session_id": session_id,
            },
        )
        assert resp.status_code == 200

    # Wait for the async write to complete
    await asyncio.sleep(1.0)

    # Query Supabase directly to verify the row
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/session_audit",
            headers=headers,
            params={"session_id": f"eq.{session_id}", "select": "*"},
        )
        assert r.status_code == 200
        rows = r.json()

    assert len(rows) == 1, f"Expected 1 audit row, got {len(rows)}"
    row = rows[0]
    assert row["session_id"] == session_id
    assert row["turn_number"] == 1
    assert len(row["node_path"]) > 0, "node_path must not be empty"
    assert row["primary_intent"] is not None, "primary_intent must be set"
    assert row["crisis_state"] is not None, "crisis_state must be set"
    assert row["crisis_state"] == "none", f"Expected crisis_state=none, got {row['crisis_state']}"
```

- [ ] **Step 2: Run the integration test (requires running server + SUPABASE_* env vars)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
SUPABASE_URL=<your-url> SUPABASE_SERVICE_KEY=<your-key> uv run pytest tests/test_session_audit_integration.py -v -m integration
```

Expected: PASS. The row appears in `session_audit` with correct `session_id`, `turn_number=1`, non-empty `node_path`, non-null `primary_intent`, and `crisis_state="none"`.

- [ ] **Step 3: Commit**

```bash
git add sage-poc/tests/test_session_audit_integration.py
git commit -m "test: add integration test for session_audit write after POC turn"
```

---

### Task 6: Frontend type + middleware protection

**Files:**
- Create: `cdai/apps/web/lib/types/session-audit.ts`
- Modify: `cdai/apps/web/middleware.ts`

- [ ] **Step 1: Create AuditRow type**

Create `cdai/apps/web/lib/types/session-audit.ts`:

```typescript
export type AuditRow = {
  id: string
  inserted_at: string
  session_id: string
  turn_number: number
  node_path: string[]
  primary_intent: string | null
  secondary_intent: string | null
  intent_confidence: number | null
  active_skill_id: string | null
  active_step_id: string | null
  skill_match_method: string | null
  knowledge_source: string | null
  knowledge_passage_ids: string[]
  knowledge_abstain: boolean | null
  crisis_state: string | null
  crisis_flags: string[]
  clinical_flags: string[]
  engagement: number | null
  emotional_intensity: number | null
  model_version: string | null
  latency_ms: number | null
}
```

- [ ] **Step 2: Add `/live` to admin-protected paths in middleware.ts**

In `cdai/apps/web/middleware.ts`, the existing admin check is:

```typescript
if (pathname.startsWith('/admin') && !profile?.is_admin) {
  return new NextResponse(null, { status: 403 })
}
```

Replace with:

```typescript
const isAdminRoute = pathname.startsWith('/admin') || pathname.startsWith('/live')
if (isAdminRoute && !profile?.is_admin) {
  return new NextResponse(null, { status: 403 })
}
```

Also update the onboarding gate condition to exclude `/live`:

```typescript
if (!pathname.startsWith('/admin') && !pathname.startsWith('/live') && !isOnboardingStep && needsOnboarding) {
```

- [ ] **Step 3: Run the frontend test suite to verify no regressions**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
pnpm test
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add cdai/apps/web/lib/types/session-audit.ts cdai/apps/web/middleware.ts
git commit -m "feat: add AuditRow type, protect /live with admin middleware"
```

---

### Task 7: `use-session-audit` hook

**Files:**
- Create: `cdai/apps/web/components/clinical-live/use-session-audit.ts`
- Create: `cdai/apps/web/components/clinical-live/__tests__/use-session-audit.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/components/clinical-live/__tests__/use-session-audit.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import type { AuditRow } from '@/lib/types/session-audit'

const mockRow = (overrides: Partial<AuditRow> = {}): AuditRow => ({
  id: '1',
  inserted_at: '2026-05-27T10:00:00Z',
  session_id: 'sess-001',
  turn_number: 1,
  node_path: ['safety_check', 'intent_route', 'freeflow_respond', 'output_gate'],
  primary_intent: 'general_chat',
  secondary_intent: null,
  intent_confidence: 0.9,
  active_skill_id: null,
  active_step_id: null,
  skill_match_method: null,
  knowledge_source: null,
  knowledge_passage_ids: [],
  knowledge_abstain: null,
  crisis_state: 'none',
  crisis_flags: [],
  clinical_flags: [],
  engagement: 7,
  emotional_intensity: 4,
  model_version: 'claude-sonnet-4-6',
  latency_ms: null,
  ...overrides,
})

let realtimeCallback: ((payload: { new: AuditRow }) => void) | null = null

function makeMockSupabase(initialRows: AuditRow[] = []) {
  return {
    from: () => ({
      select: () => ({
        eq: () => ({
          order: () => ({
            limit: () => Promise.resolve({ data: initialRows, error: null }),
            then: (f: Function) => Promise.resolve({ data: initialRows, error: null }).then(f),
          }),
          then: (f: Function) => Promise.resolve({ data: initialRows, error: null }).then(f),
        }),
        order: () => ({
          limit: () => Promise.resolve({ data: initialRows, error: null }),
        }),
      }),
    }),
    channel: () => ({
      on: (_event: string, _filter: object, cb: (payload: { new: AuditRow }) => void) => {
        realtimeCallback = cb
        return {
          subscribe: (statusCb: (s: string) => void) => {
            statusCb('SUBSCRIBED')
            return {}
          },
        }
      },
    }),
    removeChannel: vi.fn(),
  }
}

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(),
}))

describe('useSessionAudit — follow-latest mode', () => {
  it('loads initial rows from most recent session', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit(null))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))
    expect(result.current.activeSessionId).toBe('sess-001')
    expect(result.current.status).toBe('live')
  })

  it('appends new rows from the same session', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit(null))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))

    act(() => {
      realtimeCallback?.({ new: mockRow({ turn_number: 2, id: '2' }) })
    })

    expect(result.current.rows).toHaveLength(2)
  })

  it('resets rows when a new session_id arrives', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit(null))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))

    act(() => {
      realtimeCallback?.({ new: mockRow({ session_id: 'sess-002', turn_number: 1, id: '3' }) })
    })

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.rows[0].session_id).toBe('sess-002')
    expect(result.current.activeSessionId).toBe('sess-002')
  })
})

describe('useSessionAudit — locked mode', () => {
  it('rejects rows from other sessions', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit('sess-001'))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))

    act(() => {
      realtimeCallback?.({ new: mockRow({ session_id: 'sess-other', turn_number: 2, id: '9' }) })
    })

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.status).toBe('locked')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
pnpm test components/clinical-live/__tests__/use-session-audit.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `use-session-audit.ts`**

Create `cdai/apps/web/components/clinical-live/use-session-audit.ts`:

```typescript
'use client'

import { useEffect, useRef, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { AuditRow } from '@/lib/types/session-audit'

export type SessionAuditStatus = 'waiting' | 'live' | 'locked' | 'reconnecting'

export function useSessionAudit(lockedSessionId: string | null) {
  const [rows, setRows] = useState<AuditRow[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(lockedSessionId)
  const [status, setStatus] = useState<SessionAuditStatus>('waiting')
  const activeSessionRef = useRef<string | null>(lockedSessionId)

  useEffect(() => {
    const supabase = createClient()

    async function bootstrap() {
      if (lockedSessionId) {
        const { data } = await supabase
          .from('session_audit')
          .select('*')
          .eq('session_id', lockedSessionId)
          .order('turn_number', { ascending: true })
        if (data?.length) {
          setRows(data as AuditRow[])
          setActiveSessionId(lockedSessionId)
          setStatus('locked')
        }
      } else {
        const { data } = await supabase
          .from('session_audit')
          .select('*')
          .order('inserted_at', { ascending: false })
          .limit(20)
        if (data?.length) {
          const latestSession = (data as AuditRow[])[0].session_id
          const sessionRows = (data as AuditRow[])
            .filter(r => r.session_id === latestSession)
            .reverse()
          activeSessionRef.current = latestSession
          setRows(sessionRows)
          setActiveSessionId(latestSession)
          setStatus('live')
        }
      }
    }

    bootstrap()

    const channel = supabase
      .channel('session_audit_live')
      .on(
        'postgres_changes' as never,
        { event: 'INSERT', schema: 'public', table: 'session_audit' },
        (payload: { new: AuditRow }) => {
          const newRow = payload.new
          if (lockedSessionId) {
            if (newRow.session_id !== lockedSessionId) return
            setRows(prev => [...prev, newRow])
          } else {
            if (!activeSessionRef.current || newRow.session_id === activeSessionRef.current) {
              activeSessionRef.current = newRow.session_id
              setActiveSessionId(newRow.session_id)
              setRows(prev => [...prev, newRow])
              setStatus('live')
            } else {
              activeSessionRef.current = newRow.session_id
              setActiveSessionId(newRow.session_id)
              setRows([newRow])
              setStatus('live')
            }
          }
        }
      )
      .subscribe((s: string) => {
        if (s === 'SUBSCRIBED') setStatus(lockedSessionId ? 'locked' : 'live')
        if (s === 'CHANNEL_ERROR') setStatus('reconnecting')
      })

    return () => { supabase.removeChannel(channel) }
  }, [lockedSessionId])

  return { rows, latestRow: rows[rows.length - 1] ?? null, activeSessionId, status }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pnpm test components/clinical-live/__tests__/use-session-audit.test.ts
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cdai/apps/web/components/clinical-live/use-session-audit.ts cdai/apps/web/components/clinical-live/__tests__/use-session-audit.test.ts
git commit -m "feat: add use-session-audit hook with follow-latest and locked modes"
```

---

### Task 8: `NodePathVisualizer`

**Files:**
- Create: `cdai/apps/web/components/clinical-live/node-path-visualizer.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/node-path-visualizer.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/components/clinical-live/__tests__/node-path-visualizer.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NodePathVisualizer } from '../node-path-visualizer'

describe('NodePathVisualizer', () => {
  it('renders all 8 nodes', () => {
    render(<NodePathVisualizer firedNodes={[]} turnNumber={0} />)
    expect(screen.getByText('Safety')).toBeDefined()
    expect(screen.getByText('Intent')).toBeDefined()
    expect(screen.getByText('Low Conf.')).toBeDefined()
    expect(screen.getByText('Skill Select')).toBeDefined()
    expect(screen.getByText('Skill Exec')).toBeDefined()
    expect(screen.getByText('Knowledge')).toBeDefined()
    expect(screen.getByText('Respond')).toBeDefined()
    expect(screen.getByText('Gate')).toBeDefined()
  })

  it('marks fired nodes with data-fired="true"', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'intent_route', 'freeflow_respond', 'output_gate']}
        turnNumber={1}
      />
    )
    const fired = container.querySelectorAll('[data-fired="true"]')
    expect(fired).toHaveLength(4)
  })

  it('marks unfired nodes with data-fired="false"', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'intent_route', 'freeflow_respond', 'output_gate']}
        turnNumber={1}
      />
    )
    const unfired = container.querySelectorAll('[data-fired="false"]')
    expect(unfired).toHaveLength(4) // low_confidence, skill_select, skill_executor, knowledge_retrieve
  })

  it('renders connectors only between consecutive fired nodes', () => {
    // Turn 5 knowledge path: safety_check → intent_route → skill_select → knowledge_retrieve → freeflow_respond → output_gate
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'intent_route', 'skill_select', 'knowledge_retrieve', 'freeflow_respond', 'output_gate']}
        turnNumber={5}
      />
    )
    // Connectors are rendered between consecutive fired nodes
    const connectors = container.querySelectorAll('[data-connector="true"]')
    expect(connectors.length).toBeGreaterThan(0)
    // All connectors should be between nodes that are both fired
    connectors.forEach(c => {
      expect(c.getAttribute('data-both-fired')).toBe('true')
    })
  })

  it('shows crisis short-circuit path correctly', () => {
    const { container } = render(
      <NodePathVisualizer
        firedNodes={['safety_check', 'crisis_response']}
        turnNumber={6}
      />
    )
    // safety_check fired, others not
    const fired = container.querySelectorAll('[data-fired="true"]')
    expect(fired).toHaveLength(1) // only safety_check from the 8-node list
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pnpm test components/clinical-live/__tests__/node-path-visualizer.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `node-path-visualizer.tsx`**

Create `cdai/apps/web/components/clinical-live/node-path-visualizer.tsx`:

```tsx
'use client'

const NODES = [
  { id: 'safety_check',       label: 'Safety' },
  { id: 'intent_route',       label: 'Intent' },
  { id: 'low_confidence',     label: 'Low Conf.' },
  { id: 'skill_select',       label: 'Skill Select' },
  { id: 'skill_executor',     label: 'Skill Exec' },
  { id: 'knowledge_retrieve', label: 'Knowledge' },
  { id: 'freeflow_respond',   label: 'Respond' },
  { id: 'output_gate',        label: 'Gate' },
] as const

type Props = {
  firedNodes: string[]
  turnNumber: number
}

export function NodePathVisualizer({ firedNodes, turnNumber }: Props) {
  const firedSet = new Set(firedNodes)

  return (
    <div className="w-full">
      {turnNumber > 0 && (
        <p className="text-xs text-slate-500 mb-2">Turn {turnNumber}</p>
      )}
      <div className="flex items-center gap-0 overflow-x-auto">
        {NODES.map((node, i) => {
          const isFired = firedSet.has(node.id)
          const prevFired = i > 0 && firedSet.has(NODES[i - 1].id)
          const bothFired = isFired && prevFired
          return (
            <div key={node.id} className="flex items-center">
              {i > 0 && (
                <div
                  data-connector="true"
                  data-both-fired={String(bothFired)}
                  className={`w-4 h-px flex-shrink-0 ${bothFired ? 'bg-teal-400' : 'bg-slate-700'}`}
                />
              )}
              <div
                data-fired={String(isFired)}
                className={`
                  flex-shrink-0 px-2 py-1 rounded text-xs font-mono whitespace-nowrap
                  ${isFired
                    ? 'bg-teal-500 text-white ring-1 ring-teal-300'
                    : 'bg-slate-800 text-slate-500'
                  }
                `}
              >
                {node.label}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pnpm test components/clinical-live/__tests__/node-path-visualizer.test.tsx
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cdai/apps/web/components/clinical-live/node-path-visualizer.tsx cdai/apps/web/components/clinical-live/__tests__/node-path-visualizer.test.tsx
git commit -m "feat: add NodePathVisualizer with three visual states"
```

---

### Task 9: `ClinicalStateCard`

**Files:**
- Create: `cdai/apps/web/components/clinical-live/clinical-state-card.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/clinical-state-card.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/components/clinical-live/__tests__/clinical-state-card.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ClinicalStateCard } from '../clinical-state-card'
import type { AuditRow } from '@/lib/types/session-audit'

function makeRow(overrides: Partial<AuditRow> = {}): AuditRow {
  return {
    id: '1', inserted_at: '', session_id: '', turn_number: 1,
    node_path: [], primary_intent: 'general_chat', secondary_intent: null,
    intent_confidence: 0.9, active_skill_id: null, active_step_id: null,
    skill_match_method: null, knowledge_source: null, knowledge_passage_ids: [],
    knowledge_abstain: null, crisis_state: 'none', crisis_flags: [],
    clinical_flags: [], engagement: 7, emotional_intensity: 4,
    model_version: 'claude-sonnet-4-6', latency_ms: null,
    ...overrides,
  }
}

describe('ClinicalStateCard', () => {
  it('renders intent', () => {
    render(<ClinicalStateCard row={makeRow({ primary_intent: 'new_skill' })} />)
    expect(screen.getByText('new_skill')).toBeDefined()
  })

  it('shows em dash for null skill fields', () => {
    render(<ClinicalStateCard row={makeRow({ active_skill_id: null })} />)
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThan(0)
  })

  it('shows crisis state as active with red indicator', () => {
    const { container } = render(
      <ClinicalStateCard row={makeRow({ crisis_state: 'active', crisis_flags: ['S1_keyword'] })} />
    )
    const indicator = container.querySelector('[data-crisis="active"]')
    expect(indicator).toBeTruthy()
  })

  it('shows monitoring state with amber indicator', () => {
    const { container } = render(
      <ClinicalStateCard row={makeRow({ crisis_state: 'monitoring' })} />
    )
    const indicator = container.querySelector('[data-crisis="monitoring"]')
    expect(indicator).toBeTruthy()
  })

  it('hides knowledge column when knowledge_source is null', () => {
    render(<ClinicalStateCard row={makeRow({ knowledge_source: null })} />)
    expect(screen.queryByText('Source')).toBeNull()
    expect(screen.queryByText('Passages')).toBeNull()
  })

  it('shows knowledge column when knowledge_source is set', () => {
    render(<ClinicalStateCard row={makeRow({
      knowledge_source: 'node_6',
      knowledge_passage_ids: ['cbt-001-en-000', 'cbt-001-en-001'],
      knowledge_abstain: false,
    })} />)
    expect(screen.getByText('Source')).toBeDefined()
    expect(screen.getByText('node_6')).toBeDefined()
    expect(screen.getByText('cbt-001-en-000')).toBeDefined()
  })

  it('shows clinical flag badges', () => {
    render(<ClinicalStateCard row={makeRow({ clinical_flags: ['substance_use'] })} />)
    expect(screen.getByText('substance_use')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pnpm test components/clinical-live/__tests__/clinical-state-card.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `clinical-state-card.tsx`**

Create `cdai/apps/web/components/clinical-live/clinical-state-card.tsx`:

```tsx
'use client'

import type { AuditRow } from '@/lib/types/session-audit'

const CRISIS_COLORS: Record<string, string> = {
  none:       'bg-green-500',
  monitoring: 'bg-amber-500',
  active:     'bg-red-500',
  resolved:   'bg-slate-500',
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-slate-400 w-20 flex-shrink-0">{label}</span>
      <span className="text-slate-100 font-mono">{value ?? '—'}</span>
    </div>
  )
}

function MeterBar({ value, max = 10 }: { value: number | null; max?: number }) {
  const pct = value != null ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full bg-teal-400 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-300 font-mono">{value ?? '—'}/10</span>
    </div>
  )
}

type Props = { row: AuditRow }

export function ClinicalStateCard({ row }: Props) {
  const crisisColor = CRISIS_COLORS[row.crisis_state ?? 'none'] ?? 'bg-slate-500'
  const hasKnowledge = Boolean(row.knowledge_source)

  return (
    <div className={`grid gap-4 ${hasKnowledge ? 'grid-cols-3' : 'grid-cols-2'}`}>
      {/* Left column — mental state */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Clinical State</p>
        <Field label="Intent" value={row.primary_intent} />
        <div className="flex gap-2 text-xs items-center">
          <span className="text-slate-400 w-20 flex-shrink-0">Crisis</span>
          <span
            data-crisis={row.crisis_state ?? 'none'}
            className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${crisisColor}`}
          />
          <span className="text-slate-100 font-mono">{row.crisis_state ?? 'none'}</span>
        </div>
        {row.crisis_flags && row.crisis_flags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {row.crisis_flags.map(f => (
              <span key={f} className="text-[10px] bg-red-900 text-red-200 px-1.5 py-0.5 rounded">{f}</span>
            ))}
          </div>
        )}
        <div className="flex gap-2 text-xs items-center">
          <span className="text-slate-400 w-20 flex-shrink-0">Engage</span>
          <MeterBar value={row.engagement} />
        </div>
        <div className="flex gap-2 text-xs items-center">
          <span className="text-slate-400 w-20 flex-shrink-0">Intensity</span>
          <MeterBar value={row.emotional_intensity} />
        </div>
        {row.clinical_flags && row.clinical_flags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {row.clinical_flags.map(f => (
              <span key={f} className="text-[10px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">{f}</span>
            ))}
          </div>
        )}
        {(!row.clinical_flags || row.clinical_flags.length === 0) && (
          <Field label="Flags" value="—" />
        )}
      </div>

      {/* Right column — turn detail */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Turn Detail</p>
        <Field label="Skill" value={row.active_skill_id} />
        <Field label="Step" value={row.active_step_id} />
        <Field label="Match" value={
          row.skill_match_method
            ? `${row.skill_match_method}${row.intent_confidence != null ? ` (${row.intent_confidence.toFixed(2)})` : ''}`
            : null
        } />
        <Field label="Gate" value={null} />
        <Field label="Model" value={row.model_version} />
        <Field label="Latency" value={row.latency_ms != null ? `${row.latency_ms}ms` : null} />
      </div>

      {/* Conditional knowledge column */}
      {hasKnowledge && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Knowledge</p>
          <Field label="Source" value={row.knowledge_source} />
          <div className="flex gap-2 text-xs">
            <span className="text-slate-400 w-20 flex-shrink-0">Passages</span>
            <div className="flex flex-col gap-0.5">
              {row.knowledge_passage_ids?.length
                ? row.knowledge_passage_ids.map(p => (
                    <span key={p} className="text-teal-300 font-mono">{p}</span>
                  ))
                : <span className="text-slate-100 font-mono">—</span>
              }
            </div>
          </div>
          <Field label="Abstain" value={row.knowledge_abstain != null ? String(row.knowledge_abstain) : null} />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pnpm test components/clinical-live/__tests__/clinical-state-card.test.tsx
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cdai/apps/web/components/clinical-live/clinical-state-card.tsx cdai/apps/web/components/clinical-live/__tests__/clinical-state-card.test.tsx
git commit -m "feat: add ClinicalStateCard with conditional knowledge column"
```

---

### Task 10: `AuditLog`

**Files:**
- Create: `cdai/apps/web/components/clinical-live/audit-log.tsx`
- Create: `cdai/apps/web/components/clinical-live/__tests__/audit-log.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/components/clinical-live/__tests__/audit-log.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuditLog } from '../audit-log'
import type { AuditRow } from '@/lib/types/session-audit'

function makeRow(n: number, overrides: Partial<AuditRow> = {}): AuditRow {
  return {
    id: String(n), inserted_at: '', session_id: 'sess-001',
    turn_number: n, node_path: [], primary_intent: 'general_chat',
    secondary_intent: null, intent_confidence: null,
    active_skill_id: null, active_step_id: null, skill_match_method: null,
    knowledge_source: null, knowledge_passage_ids: [], knowledge_abstain: null,
    crisis_state: 'none', crisis_flags: [], clinical_flags: [],
    engagement: 7, emotional_intensity: 4, model_version: null, latency_ms: null,
    ...overrides,
  }
}

describe('AuditLog', () => {
  it('renders empty state when no rows', () => {
    render(<AuditLog rows={[]} />)
    expect(screen.getByText(/waiting/i)).toBeDefined()
  })

  it('renders one row per turn', () => {
    render(<AuditLog rows={[makeRow(1), makeRow(2), makeRow(3)]} />)
    expect(screen.getByText('T1')).toBeDefined()
    expect(screen.getByText('T2')).toBeDefined()
    expect(screen.getByText('T3')).toBeDefined()
  })

  it('shows the most recent turn first', () => {
    const { container } = render(<AuditLog rows={[makeRow(1), makeRow(2)]} />)
    const rows = container.querySelectorAll('tr[data-turn]')
    expect(rows[0].getAttribute('data-turn')).toBe('2')
    expect(rows[1].getAttribute('data-turn')).toBe('1')
  })

  it('renders skill_id when active', () => {
    render(<AuditLog rows={[makeRow(1, { active_skill_id: 'box_breathing' })]} />)
    expect(screen.getByText('box_breathing')).toBeDefined()
  })

  it('renders crisis state', () => {
    render(<AuditLog rows={[makeRow(1, { crisis_state: 'monitoring' })]} />)
    expect(screen.getByText('monitoring')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pnpm test components/clinical-live/__tests__/audit-log.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `audit-log.tsx`**

Create `cdai/apps/web/components/clinical-live/audit-log.tsx`:

```tsx
'use client'

import type { AuditRow } from '@/lib/types/session-audit'

const COLS = ['Turn', 'Intent', 'Skill', 'Step', 'Crisis', 'Eng', 'Int', 'ms']

type Props = { rows: AuditRow[] }

export function AuditLog({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <p className="text-xs text-slate-500 text-center py-4">
        Waiting for turns...
      </p>
    )
  }

  const sorted = [...rows].sort((a, b) => b.turn_number - a.turn_number)

  return (
    <div className="overflow-auto max-h-48">
      <table className="w-full text-xs font-mono border-collapse">
        <thead>
          <tr>
            {COLS.map(c => (
              <th key={c} className="text-left text-slate-500 pb-1 pr-3 font-normal">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(row => (
            <tr
              key={row.id}
              data-turn={String(row.turn_number)}
              className="border-t border-slate-800 hover:bg-slate-800/40"
            >
              <td className="py-0.5 pr-3 text-slate-300">T{row.turn_number}</td>
              <td className="py-0.5 pr-3 text-slate-300">{row.primary_intent ?? '—'}</td>
              <td className="py-0.5 pr-3 text-teal-400">{row.active_skill_id ?? '—'}</td>
              <td className="py-0.5 pr-3 text-slate-400">{row.active_step_id ?? '—'}</td>
              <td className="py-0.5 pr-3 text-slate-300">{row.crisis_state ?? '—'}</td>
              <td className="py-0.5 pr-3 text-slate-400">{row.engagement ?? '—'}</td>
              <td className="py-0.5 pr-3 text-slate-400">{row.emotional_intensity ?? '—'}</td>
              <td className="py-0.5 text-slate-500">{row.latency_ms != null ? `${row.latency_ms}` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pnpm test components/clinical-live/__tests__/audit-log.test.tsx
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run full frontend test suite**

```bash
pnpm test
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add cdai/apps/web/components/clinical-live/audit-log.tsx cdai/apps/web/components/clinical-live/__tests__/audit-log.test.tsx
git commit -m "feat: add AuditLog scrollable table, newest-first"
```

---

### Task 11: `/live` route, layout, and page

**Files:**
- Create: `cdai/apps/web/app/(clinical)/live/layout.tsx`
- Create: `cdai/apps/web/app/(clinical)/live/page.tsx`

No new tests here — the components are unit-tested individually and the page is a composition. The Playwright test in Task 12 covers the wired-up route.

- [ ] **Step 1: Create the layout**

Create `cdai/apps/web/app/(clinical)/live/layout.tsx`:

```tsx
import type { ReactNode } from 'react'

export const metadata = { title: 'Clinical Intelligence | SAGE' }

export default function LiveLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {children}
    </div>
  )
}
```

- [ ] **Step 2: Create the page**

Create `cdai/apps/web/app/(clinical)/live/page.tsx`:

```tsx
'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSessionAudit } from '@/components/clinical-live/use-session-audit'
import { NodePathVisualizer } from '@/components/clinical-live/node-path-visualizer'
import { ClinicalStateCard } from '@/components/clinical-live/clinical-state-card'
import { AuditLog } from '@/components/clinical-live/audit-log'

const STATUS_DOT: Record<string, string> = {
  live:         'bg-teal-400 animate-pulse',
  locked:       'bg-blue-400',
  reconnecting: 'bg-amber-400 animate-pulse',
  waiting:      'bg-slate-500',
}

const STATUS_LABEL: Record<string, string> = {
  live:         'LIVE',
  locked:       'LOCKED',
  reconnecting: 'RECONNECTING',
  waiting:      'WAITING',
}

function LivePanel() {
  const params = useSearchParams()
  const lockedSessionId = params.get('session')
  const { rows, latestRow, activeSessionId, status } = useSessionAudit(lockedSessionId)

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700 bg-slate-900 flex-shrink-0">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[status]}`} />
        <span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
          {STATUS_LABEL[status]}
        </span>
        <span className="text-sm font-semibold text-slate-100">SAGE Clinical Intelligence</span>
        {activeSessionId && (
          <span className="ml-auto text-xs text-slate-500 font-mono truncate max-w-[20ch]">
            {activeSessionId}
          </span>
        )}
      </div>

      {/* Node path */}
      <div className="px-4 py-3 border-b border-slate-700 flex-shrink-0">
        <NodePathVisualizer
          firedNodes={latestRow?.node_path ?? []}
          turnNumber={latestRow?.turn_number ?? 0}
        />
      </div>

      {/* Clinical state card */}
      <div className="px-4 py-3 border-b border-slate-700 flex-shrink-0">
        {latestRow ? (
          <ClinicalStateCard row={latestRow} />
        ) : (
          <p className="text-xs text-slate-500">
            Waiting for session — start a conversation in the chat window.
          </p>
        )}
      </div>

      {/* Audit log */}
      <div className="px-4 py-3 flex-1 overflow-hidden">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Audit Log</p>
        <AuditLog rows={rows} />
      </div>
    </div>
  )
}

export default function LivePage() {
  return (
    <Suspense fallback={<div className="p-4 text-slate-500 text-sm">Loading...</div>}>
      <LivePanel />
    </Suspense>
  )
}
```

- [ ] **Step 3: Verify the route resolves**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
pnpm build 2>&1 | grep -E "error|warn|live" | head -20
```

Expected: no TypeScript errors on the new files. The `/live` route appears in the build output.

- [ ] **Step 4: Commit**

```bash
git add cdai/apps/web/app/\(clinical\)/live/layout.tsx cdai/apps/web/app/\(clinical\)/live/page.tsx
git commit -m "feat: add /live route with clinical intelligence panel layout"
```

---

### Task 12: End-to-end Playwright test

**Files:**
- Create: `cdai/apps/web/playwright/clinical-live.spec.ts`

This test requires both the POC server and the Next.js dev server running, and `SUPABASE_*` env vars set. It is not run in standard CI.

- [ ] **Step 1: Create the Playwright test**

Create `cdai/apps/web/playwright/clinical-live.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'

const POC_URL = process.env.POC_URL ?? 'http://localhost:8765'
const SESSION_ID = `playwright-${Date.now()}`

test.describe('Clinical Intelligence Panel (/live)', () => {
  test('panel updates after chat message is sent', async ({ page }) => {
    // Open the /live panel in follow-latest mode
    await page.goto('/live')

    // Expect waiting state initially
    await expect(page.getByText('WAITING')).toBeVisible({ timeout: 5000 })

    // Send a chat message directly to the POC server using Playwright's built-in request API
    const resp = await page.request.post(`${POC_URL}/chat`, {
      data: {
        messages: [{ role: 'user', content: 'I feel a bit stressed today' }],
        session_id: SESSION_ID,
      },
    })
    expect(resp.ok()).toBeTruthy()

    // Panel should switch to LIVE and show the session
    await expect(page.getByText('LIVE')).toBeVisible({ timeout: 10000 })

    // Node path should appear with at least Safety node lit
    await expect(page.locator('[data-fired="true"]').first()).toBeVisible({ timeout: 5000 })

    // Audit log should show Turn 1
    await expect(page.getByText('T1')).toBeVisible({ timeout: 5000 })

    // Intent should be visible
    await expect(page.getByText('general_chat')).toBeVisible()
  })

  test('?session= lock shows specific session', async ({ page }) => {
    // Pre-send a turn to create session data
    const resp = await page.request.post(`${POC_URL}/chat`, {
      data: {
        messages: [{ role: 'user', content: 'What is anxiety?' }],
        session_id: SESSION_ID,
      },
    })
    expect(resp.ok()).toBeTruthy()

    // Small delay for the async write to land
    await page.waitForTimeout(1000)

    // Open panel locked to this session
    await page.goto(`/live?session=${SESSION_ID}`)

    await expect(page.getByText('LOCKED')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('T1')).toBeVisible({ timeout: 5000 })
  })
})
```

- [ ] **Step 2: Run manually (requires both servers)**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
# Terminal 1: start POC server
# uv run python sage-poc/server.py (from sage-poc dir)
# Terminal 2: start Next.js
pnpm dev
# Terminal 3: run Playwright
pnpm exec playwright test playwright/clinical-live.spec.ts --headed
```

Expected: both tests PASS. The panel transitions from WAITING to LIVE, the node path updates, T1 appears in the audit log.

- [ ] **Step 3: Commit**

```bash
git add cdai/apps/web/playwright/clinical-live.spec.ts
git commit -m "test: add Playwright e2e test for /live clinical intelligence panel"
```

---

## Self-Review Checklist

- Migration 009 renaming: corrected from spec draft's "008" throughout the plan. ✓
- `knowledge_passages` → `knowledge_passage_ids` extraction in `audit.py`: handled via list comprehension on `source_id`. ✓
- Crisis path bypass: `_crisis_response_node` in `graph.py` gets its own `create_task` call with merged state including `path`, `gate_path`, `crisis_state`. ✓
- `asyncio` import in `graph.py`: added at top level alongside `write_session_audit`. ✓
- `os.environ.get()` guard: present in `audit.py`; env-less environments return early. ✓
- `turn_number` added to `make_state()` in `test_nodes.py` and inline dicts in `test_state.py`. ✓
- Middleware: `/live` added to admin-protected path check and excluded from onboarding gate. ✓
- Node list: 8 correct nodes (`safety_check`, `intent_route`, `low_confidence`, `skill_select`, `skill_executor`, `knowledge_retrieve`, `freeflow_respond`, `output_gate`) — no translator. ✓
- Knowledge column in `ClinicalStateCard`: conditional on `knowledge_source` being non-null. ✓
- `AuditLog` empty state: shows "Waiting for turns..." not blank. ✓
- Playwright test: uses `?session=` lock mode for the second test case. ✓
