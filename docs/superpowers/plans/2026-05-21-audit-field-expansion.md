# Audit Field Expansion (R-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the LangGraph runtime audit trail from 2 fields (model, node_path) to 8 fields (adding skill_id, step_id, gate_path, crisis_flags, clinical_flags, emotional_intensity) so that every focus-group session can be replayed and mapped to graph behaviour at the field level.

**Architecture:** All six new fields are already present in the `SageState` TypedDict after every graph run. They are extracted in `server.py`'s `/chat` handler and set as HTTP response headers on the `StreamingResponse` — metadata never touches the body stream. `route.ts` reads the headers before `tee()`-ing the body to the client, and stores them alongside the existing traceability columns in the Supabase `messages` table. No graph node changes are required.

**Tech Stack:** FastAPI + LangGraph (`sage-poc/`), Next.js 15 API route (`cdai/apps/web/`), Supabase (postgres + REST), pytest, TypeScript.

---

## Repository layout

This plan touches two codebases in the same workspace:

| Repo | Root |
|---|---|
| Sage backend | `/Users/knowledgebase/Documents/Sage/sage-poc/` |
| CDAi frontend | `/Users/knowledgebase/Documents/Sage/cdai/` |

All `pytest` commands run from `sage-poc/`. All `supabase` CLI commands run from `cdai/`.

---

## Field mapping

| SageState field | Header name | Header encoding | DB column | DB type |
|---|---|---|---|---|
| `active_skill_id` | `X-Sage-Skill-Id` | plain string, `""` if None | `skill_id` | `text` |
| `executed_step_id` | `X-Sage-Step-Id` | plain string, `""` if None | `step_id` | `text` |
| `gate_path` | `X-Sage-Gate-Path` | plain string, `""` if None | `gate_path` | `text` |
| `crisis_flags` | `X-Sage-Crisis-Flags` | JSON array | `crisis_flags` | `jsonb` |
| `clinical_flags` | `X-Sage-Clinical-Flags` | JSON array | `clinical_flags` | `jsonb` |
| `emotional_intensity` | `X-Sage-Emotional-Intensity` | decimal string | `emotional_intensity` | `integer` |

**Encoding rules:**
- Optional string fields: send value as-is; send empty string `""` when None. Consumer does `header || null` → JS null.
- List fields: always JSON-encoded, minimum `"[]"`. Consumer does `JSON.parse(header || "[]")`.
- Int field: `str(value or 0)`. Consumer does `parseInt(header, 10) || null`.

**Population rules by message type:**

| message.role | skill_id | step_id | gate_path | crisis_flags | clinical_flags | emotional_intensity |
|---|---|---|---|---|---|---|
| `user` | null | null | null | null | null | null |
| `ai` (freeflow) | null | null | `"standard"` | `[]` | `[]` or populated | 1-10 |
| `ai` (skill step) | `"cbt_thought_record"` | `"step_1"` | `"standard"` | `[]` | `[]` or populated | 1-10 |
| `crisis` | null | null | null or `""` | `["keyword_x"]` | `[]` or populated | 1-10 |
| `ai` (scope/jailbreak) | null | null | `"scope_refusal"` or `"jailbreak"` | `[]` | `[]` | 1-10 |

Note: `gate_path` is set by `output_gate` (last graph node). Crisis responses route to `crisis_response_node` which may bypass `output_gate`, so `gate_path` will be `None → ""` on crisis rows.

---

## File structure

**Files modified:**

```
sage-poc/
  server.py                             # add 6 new headers to StreamingResponse
  tests/test_server.py                  # add 5 tests (TDD: written before server.py change)

cdai/
  supabase/migrations/002_audit_fields.sql   # CREATE new file — consolidates + expands columns
  apps/web/app/api/chat/route.ts        # parse 6 new headers, add to messages.insert()
```

No changes to graph nodes, `SageState`, or any other files.

---

## Task 1: Write failing tests, then expand server.py headers

**Files:**
- Modify: `sage-poc/tests/test_server.py` (add 5 new test functions after line 126)
- Modify: `sage-poc/server.py` (expand headers dict in the `chat` handler, ~lines 60-72)

### Step 1.1 — Write the 5 failing tests

Add the following 5 functions at the end of `sage-poc/tests/test_server.py`:

```python
def test_all_audit_headers_present():
    """All 8 metadata headers must be present on every response, including crisis paths."""
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.status_code == 200
    for header in [
        "x-sage-model", "x-sage-node-path",
        "x-sage-skill-id", "x-sage-step-id", "x-sage-gate-path",
        "x-sage-crisis-flags", "x-sage-clinical-flags", "x-sage-emotional-intensity",
    ]:
        assert header in res.headers, f"Missing header: {header}"


def test_crisis_path_crisis_flags_non_empty():
    """Crisis keyword match → x-sage-crisis-flags is a non-empty JSON array."""
    import json as _json
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    flags = _json.loads(res.headers["x-sage-crisis-flags"])
    assert isinstance(flags, list)
    assert len(flags) > 0


def test_crisis_path_no_skill_fields():
    """Crisis responses must have empty skill_id and step_id (no active skill during crisis)."""
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.headers.get("x-sage-skill-id") == ""
    assert res.headers.get("x-sage-step-id") == ""


def test_skill_response_audit_headers(monkeypatch):
    """Skill-path response: skill_id and step_id populated, crisis_flags empty."""
    import server as srv
    import json as _json

    async def _mock_skill(state):
        return {
            "path": ["safety_check", "intent_route", "skill_select", "skill_executor", "output_gate"],
            "is_safe": True,
            "response": "Let's try this together.",
            "active_skill_id": "cbt_thought_record",
            "executed_step_id": "step_1",
            "gate_path": "standard",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 7,
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_mock_skill)})())
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to try a CBT exercise"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert res.headers.get("x-sage-skill-id") == "cbt_thought_record"
    assert res.headers.get("x-sage-step-id") == "step_1"
    assert res.headers.get("x-sage-gate-path") == "standard"
    assert _json.loads(res.headers["x-sage-crisis-flags"]) == []
    assert _json.loads(res.headers["x-sage-clinical-flags"]) == []
    assert res.headers.get("x-sage-emotional-intensity") == "7"


def test_freeflow_response_audit_headers(monkeypatch):
    """Freeflow response: skill_id/step_id empty, clinical_flags and intensity populated."""
    import server as srv
    import json as _json

    async def _mock_freeflow(state):
        return {
            "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
            "is_safe": True,
            "response": "That sounds really hard.",
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
            "crisis_flags": [],
            "clinical_flags": ["trauma_indicator"],
            "emotional_intensity": 8,
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_mock_freeflow)})())
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I feel overwhelmed by everything"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert res.headers.get("x-sage-skill-id") == ""
    assert res.headers.get("x-sage-step-id") == ""
    assert res.headers.get("x-sage-gate-path") == "standard"
    assert _json.loads(res.headers["x-sage-clinical-flags"]) == ["trauma_indicator"]
    assert res.headers.get("x-sage-emotional-intensity") == "8"
```

- [ ] **Step 1.2 — Run to confirm 5 new tests fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_server.py -v -k "audit or crisis_flags or skill_response or freeflow_response"
```

Expected: 5 FAILED with `KeyError` or `AssertionError` (headers not yet present).

- [ ] **Step 1.3 — Expand the headers dict in server.py**

The current `chat` handler in `server.py` ends with a `StreamingResponse` that only sets 2 headers. Replace that entire `return StreamingResponse(...)` block (the one that creates the final response) with:

```python
    return StreamingResponse(
        _body(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Sage-Node-Path":           json.dumps(path),
            "X-Sage-Model":               RESPONDER_MODEL,
            "X-Sage-Skill-Id":            result.get("active_skill_id") or "",
            "X-Sage-Step-Id":             result.get("executed_step_id") or "",
            "X-Sage-Gate-Path":           result.get("gate_path") or "",
            "X-Sage-Crisis-Flags":        json.dumps(result.get("crisis_flags") or []),
            "X-Sage-Clinical-Flags":      json.dumps(result.get("clinical_flags") or []),
            "X-Sage-Emotional-Intensity": str(result.get("emotional_intensity") or 0),
        },
    )
```

The full `chat` endpoint in `server.py` after this change looks like:

```python
@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    state = _build_state(req)

    try:
        result = await _graph.ainvoke(state)
    except Exception as exc:
        logging.getLogger(__name__).error("[sage/graph] invoke failed: %s", exc)
        async def _err() -> AsyncGenerator[bytes, None]:
            yield b"\n[[SERVER_ERROR]]"
        return StreamingResponse(_err(), media_type="text/plain; charset=utf-8")

    path: list[str] = result.get("path") or []
    is_safe: bool = result.get("is_safe", True)
    response_text: str = result.get("response") or ""

    async def _body() -> AsyncGenerator[bytes, None]:
        if not is_safe:
            yield (CRISIS_SIGNAL + "\n").encode()
        async for chunk in _stream_words(response_text):
            yield chunk

    return StreamingResponse(
        _body(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Sage-Node-Path":           json.dumps(path),
            "X-Sage-Model":               RESPONDER_MODEL,
            "X-Sage-Skill-Id":            result.get("active_skill_id") or "",
            "X-Sage-Step-Id":             result.get("executed_step_id") or "",
            "X-Sage-Gate-Path":           result.get("gate_path") or "",
            "X-Sage-Crisis-Flags":        json.dumps(result.get("crisis_flags") or []),
            "X-Sage-Clinical-Flags":      json.dumps(result.get("clinical_flags") or []),
            "X-Sage-Emotional-Intensity": str(result.get("emotional_intensity") or 0),
        },
    )
```

- [ ] **Step 1.4 — Run all server tests to confirm 5 new tests pass and nothing regressed**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_server.py -v
```

Expected: all 16 tests pass. The 5 new tests should show PASSED. The existing 11 tests must not regress.

If any existing test fails, stop and investigate before proceeding.

- [ ] **Step 1.5 — Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add sage_poc/server.py tests/test_server.py   # adjust if package is at src/
git add src/sage_poc/server.py 2>/dev/null || true
git add server.py 2>/dev/null || true
git commit -m "feat(audit): emit 6 new traceability headers in /chat response

Adds X-Sage-Skill-Id, X-Sage-Step-Id, X-Sage-Gate-Path,
X-Sage-Crisis-Flags, X-Sage-Clinical-Flags, X-Sage-Emotional-Intensity
as response headers. All values sourced directly from graph state dict
after ainvoke() completes. Tests verify all three response paths:
crisis (keyword match), skill-driven (monkeypatched), freeflow (monkeypatched)."
```

---

## Task 2: Supabase migration — add 6 new columns

**Files:**
- Create: `cdai/supabase/migrations/002_audit_fields.sql`

The live pilot DB has `model`, `latency_ms`, `node_path` applied ad-hoc (not via a migration file). This migration consolidates all 9 traceability columns using `ADD COLUMN IF NOT EXISTS` so it is safe to apply to both fresh instances and the pilot DB.

- [ ] **Step 2.1 — Write the migration file**

Create `cdai/supabase/migrations/002_audit_fields.sql` with this exact content:

```sql
-- supabase/migrations/002_audit_fields.sql
-- Runtime audit trail columns for the messages table.
--
-- model, latency_ms, node_path were applied ad-hoc to the pilot DB and are
-- included here with IF NOT EXISTS so this migration is idempotent on both
-- fresh instances (all 9 columns created) and the live pilot DB (3 skipped).

ALTER TABLE public.messages
  ADD COLUMN IF NOT EXISTS model               text,
  ADD COLUMN IF NOT EXISTS latency_ms          integer,
  ADD COLUMN IF NOT EXISTS node_path           jsonb,
  ADD COLUMN IF NOT EXISTS skill_id            text,
  ADD COLUMN IF NOT EXISTS step_id             text,
  ADD COLUMN IF NOT EXISTS gate_path           text,
  ADD COLUMN IF NOT EXISTS crisis_flags        jsonb,
  ADD COLUMN IF NOT EXISTS clinical_flags      jsonb,
  ADD COLUMN IF NOT EXISTS emotional_intensity integer;
```

- [ ] **Step 2.2 — Apply the migration to the pilot DB**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
supabase db query --linked < supabase/migrations/002_audit_fields.sql
```

Expected: no output (ALTER TABLE is silent on success). An error like `column already exists` means `IF NOT EXISTS` is not supported by your Supabase CLI version — if that happens, run: `supabase db query --linked "ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS skill_id text, ADD COLUMN IF NOT EXISTS step_id text, ADD COLUMN IF NOT EXISTS gate_path text, ADD COLUMN IF NOT EXISTS crisis_flags jsonb, ADD COLUMN IF NOT EXISTS clinical_flags jsonb, ADD COLUMN IF NOT EXISTS emotional_intensity integer"`

- [ ] **Step 2.3 — Verify all 12 columns exist**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
supabase db query --linked "
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'messages'
ORDER BY ordinal_position
"
```

Expected output — 12 rows in this order:

```
column_name          | data_type                   | is_nullable
---------------------+-----------------------------+------------
id                   | uuid                        | NO
session_id           | uuid                        | NO
role                 | text                        | NO
content              | text                        | NO
intent               | text                        | YES
created_at           | timestamp with time zone    | NO
model                | text                        | YES
latency_ms           | integer                     | YES
node_path            | jsonb                       | YES
skill_id             | text                        | YES
step_id              | text                        | YES
gate_path            | text                        | YES
crisis_flags         | jsonb                       | YES
clinical_flags       | jsonb                       | YES
emotional_intensity  | integer                     | YES
```

If any of the 6 new columns are missing, re-run step 2.2.

- [ ] **Step 2.4 — Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add supabase/migrations/002_audit_fields.sql
git commit -m "feat(db): add 6 audit trail columns to messages table

Adds skill_id, step_id, gate_path, crisis_flags (jsonb),
clinical_flags (jsonb), emotional_intensity to messages.
All nullable — populated only on ai/crisis role rows.
Consolidates model/latency_ms/node_path with IF NOT EXISTS
for idempotency against the pilot DB where they were applied ad-hoc."
```

---

## Task 3: Parse new headers in route.ts and persist to DB

**Files:**
- Modify: `cdai/apps/web/app/api/chat/route.ts` (two sections: header parsing block, messages.insert call)

The current `route.ts` has a header parsing block (after the `sageRes.ok` check) that reads only `X-Sage-Model` and `X-Sage-Node-Path`. It also has a `supabase.from('messages').insert(...)` call inside the fire-and-forget persist closure.

- [ ] **Step 3.1 — Replace the header parsing block**

Find this block in `route.ts` (currently lines 60-66):

```typescript
  // Metadata is in response headers — never in the body stream.
  const sageModel = sageRes.headers.get('X-Sage-Model')
  const nodePathRaw = sageRes.headers.get('X-Sage-Node-Path')
  let sageNodePath: string[] | null = null
  if (nodePathRaw) {
    try { sageNodePath = JSON.parse(nodePathRaw) } catch { /* malformed header */ }
  }
```

Replace with:

```typescript
  // Metadata is in response headers — never in the body stream.
  const sageModel   = sageRes.headers.get('X-Sage-Model')
  const skillId     = sageRes.headers.get('X-Sage-Skill-Id') || null
  const stepId      = sageRes.headers.get('X-Sage-Step-Id') || null
  const gatePath    = sageRes.headers.get('X-Sage-Gate-Path') || null

  let sageNodePath: string[] | null = null
  let crisisFlags:  string[] | null = null
  let clinicalFlags: string[] | null = null
  try { sageNodePath  = JSON.parse(sageRes.headers.get('X-Sage-Node-Path')  || '[]') } catch {}
  try { crisisFlags   = JSON.parse(sageRes.headers.get('X-Sage-Crisis-Flags')   || '[]') } catch {}
  try { clinicalFlags = JSON.parse(sageRes.headers.get('X-Sage-Clinical-Flags') || '[]') } catch {}

  const intensityStr = sageRes.headers.get('X-Sage-Emotional-Intensity')
  const emotionalIntensity = intensityStr ? (parseInt(intensityStr, 10) || null) : null
```

- [ ] **Step 3.2 — Replace the messages.insert call**

Find this block inside the persist closure (currently lines 91-99):

```typescript
        await supabase.from('messages').insert({
          session_id: sessionId,
          role:       isCrisis ? 'crisis' : 'ai',
          content,
          intent,
          model:      sageModel,
          latency_ms: latencyMs,
          node_path:  sageNodePath,
        })
```

Replace with:

```typescript
        await supabase.from('messages').insert({
          session_id:          sessionId,
          role:                isCrisis ? 'crisis' : 'ai',
          content,
          intent,
          model:               sageModel,
          latency_ms:          latencyMs,
          node_path:           sageNodePath,
          skill_id:            skillId,
          step_id:             stepId,
          gate_path:           gatePath,
          crisis_flags:        crisisFlags,
          clinical_flags:      clinicalFlags,
          emotional_intensity: emotionalIntensity,
        })
```

- [ ] **Step 3.3 — Verify the TypeScript compiles**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter web exec tsc --noEmit
```

Expected: no errors. If TypeScript reports that `skill_id` is not a known property of the insert type, the project is using Supabase generated types. In that case, regenerate them: `supabase gen types typescript --linked > packages/types/src/database.types.ts` and rebuild the types package before re-running.

- [ ] **Step 3.4 — Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts
git commit -m "feat(audit): parse and persist 6 new audit headers from Sage

Reads X-Sage-Skill-Id, X-Sage-Step-Id, X-Sage-Gate-Path,
X-Sage-Crisis-Flags, X-Sage-Clinical-Flags, X-Sage-Emotional-Intensity
response headers from the Sage backend and writes them to the
matching columns in messages table on every ai/crisis row."
```

---

## Task 4: Integration verification

Both servers must be running for these steps:
- Sage backend: `cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run uvicorn server:app --reload --port 8000`
- Next.js: `cd /Users/knowledgebase/Documents/Sage/cdai && pnpm --filter web dev`

- [ ] **Step 4.1 — Obtain a session cookie for the test user**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
SESSION_JSON=$(node --input-type=module << 'EOF'
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)
const { data } = await supabase.auth.signInWithPassword({
  email: 'sage@cdai.ae', password: 'TestPass123!'
})
process.stdout.write(JSON.stringify(data.session))
EOF
)
echo "Session acquired, length: ${#SESSION_JSON}"
```

Expected: `Session acquired, length: 1900+`

Note: `sage@cdai.ae`'s password was temporarily set to `TestPass123!` during the traceability audit session. Reset it in the Supabase dashboard after this verification step.

- [ ] **Step 4.2 — Send a freeflow test message**

```bash
SESSION_ID="dc0a250c-1ee8-4f4a-a40c-8dcdba0c4d15"   # sage@cdai.ae's session
curl -s -N -X POST "http://localhost:3000/api/chat" \
  -H "Content-Type: application/json" \
  --cookie "sb-jrfrficjdwguqbvumdyo-auth-token=${SESSION_JSON}" \
  -d "{\"sessionId\": \"${SESSION_ID}\", \"messages\": [{\"role\": \"user\", \"content\": \"I've been feeling overwhelmed lately\"}]}" \
  | head -c 200
echo ""
```

Expected: a multi-word supportive response (not `{"error":"Unauthorized"}` or `[[SERVER_ERROR]]`).

- [ ] **Step 4.3 — Verify DB row has all 6 new columns populated**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
supabase db query --linked "
SELECT
  role,
  model,
  latency_ms,
  node_path,
  skill_id,
  step_id,
  gate_path,
  crisis_flags,
  clinical_flags,
  emotional_intensity,
  LEFT(content, 60) AS content_preview
FROM messages
ORDER BY created_at DESC
LIMIT 4
"
```

Expected for the most recent AI row:
- `role` = `ai`
- `model` = `anthropic/claude-sonnet-4-6` (not null)
- `latency_ms` = positive integer (not null)
- `node_path` = JSON array like `["safety_check","intent_route","freeflow_respond","output_gate"]`
- `skill_id` = null (freeflow, no active skill)
- `step_id` = null (freeflow, no skill step)
- `gate_path` = `standard`
- `crisis_flags` = `[]` (empty array, not null)
- `clinical_flags` = `[]` or a populated array
- `emotional_intensity` = 1–10 (not null)

Expected for the preceding user row:
- `role` = `user`
- All 9 traceability columns = null ✓

If `gate_path` is null instead of `"standard"` on freeflow messages, that means `output_gate` is not setting `gate_path` in the current graph. This is not a bug in this plan — the column will be null for those messages and populated when the routing graph explicitly sets it. Do not fix this here.

If `crisis_flags` or `clinical_flags` is null (not `[]`) on freeflow messages, it means `_build_state` is initialising them as `None` instead of `[]` in a code path. Check the graph result dict and update the route.ts parsing to use `|| []` instead of relying on the header always being present.

- [ ] **Step 4.4 — Verify no sentinel leakage in stored content**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
supabase db query --linked "
SELECT id, LEFT(content, 100) AS content_preview
FROM messages
WHERE content LIKE '%META%' OR content LIKE '%[[%'
ORDER BY created_at DESC
LIMIT 5
"
```

Expected: 0 rows. Any rows here means the body contains metadata — stop and investigate.

- [ ] **Step 4.5 — Commit verification note (no code change)**

No commit needed for this task — it is verification only. If step 4.3 shows all columns populated correctly, the implementation is complete.

---

## Self-review

**1. Spec coverage against user-specified scope:**

| Requirement | Covered by |
|---|---|
| `X-Sage-Skill-Id` header in server.py | Task 1 step 1.3 |
| `X-Sage-Step-Id` header in server.py | Task 1 step 1.3 |
| `X-Sage-Gate-Path` header in server.py | Task 1 step 1.3 |
| `X-Sage-Crisis-Flags` header in server.py | Task 1 step 1.3 |
| `X-Sage-Clinical-Flags` header in server.py | Task 1 step 1.3 |
| `X-Sage-Emotional-Intensity` header in server.py | Task 1 step 1.3 |
| Matching nullable Supabase columns | Task 2 |
| Parsing in route.ts | Task 3 |
| Tests: skill-driven responses have skill_id populated | Task 1 step 1.1 (`test_skill_response_audit_headers`) |
| Tests: crisis responses have crisis_flags populated | Task 1 step 1.1 (`test_crisis_path_crisis_flags_non_empty`) |
| Tests: standard freeflow has skill_id and step_id null | Task 1 step 1.1 (`test_freeflow_response_audit_headers`) |
| Integration DB verification | Task 4 |

**2. Placeholder scan:** No TBDs or "implement later" present. All code blocks are complete.

**3. Type consistency:**
- `skill_id`, `step_id`, `gate_path`: `str | None` in Python → `string | null` in TS → `text` in Postgres. Consistent across all 3 tasks.
- `crisis_flags`, `clinical_flags`: `list[str]` in Python → `string[]` in TS → `jsonb` in Postgres. Consistent.
- `emotional_intensity`: `int` in Python → `number | null` in TS → `integer` in Postgres. Consistent.
- The monkeypatch mocks in tests return the exact field names from `SageState` (`active_skill_id`, `executed_step_id`, `gate_path`, `crisis_flags`, `clinical_flags`, `emotional_intensity`) matching `server.py`'s `result.get(...)` calls.

**4. Known limitation:**
`gate_path` will be `null`/`""` on crisis responses if `crisis_response_node` bypasses `output_gate`. This is expected behaviour — the column is nullable. No test asserts a specific value for `gate_path` on crisis paths.

---
