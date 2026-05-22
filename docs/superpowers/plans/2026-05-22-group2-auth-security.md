# Group 2: Auth & API Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 7 security findings (FE-C1, FE-C4×2, FE-H5, FE-C2, FE-C3, FE-H1, FE-C7) across three sequenced sub-groups: unauthenticated API surface (2A), broken auth flows (2B), and onboarding forward-skip (2C).

**Architecture:** Two repos. Sub-group 2A gates every `/api/chat` POST behind Supabase `getUser()`, verifies session ownership for both the chat and feedback routes, and adds a shared secret between route.ts and sage-poc. Sub-group 2B completes the auth flow: upgrade middleware to server-verified tokens, add the missing PKCE callback route so email links actually work, add the missing password reset page. Sub-group 2C is a standalone one-line fix to StepGuard.

**Tech stack:** Next.js 15 App Router, `@supabase/ssr ^0.10`, FastAPI, Vitest 4, pytest, Zustand.

**Note on reset-password error display (out of scope):** `{error.message}` in the reset-password page (Task 7) is rendered inside JSX, which auto-escapes HTML — React cannot execute scripts through this path. This is a lower-risk pattern than FE-H3's `dangerouslySetInnerHTML` concern. Flag for review in Group 3 if the threat model changes.

---

## File Structure

**Modified (cdai `apps/web/`):**
- `app/api/chat/route.ts` — auth check (FE-C1), session ownership (FE-C4), secret header (FE-H5)
- `app/api/chat/__tests__/route.test.ts` — update auth mock, new tests for Tasks 1–3
- `app/api/feedback/route.ts` — messageId ownership check (FE-C4)
- `app/api/feedback/__tests__/route.test.ts` — expand mock, new ownership tests
- `middleware.ts` — `getUser()` (FE-H1), add `/auth/callback` (FE-C2), add `/reset-password` (FE-C3) to AUTH_PATHS
- `app/(auth)/forgot-password/page.tsx` — update `redirectTo` URL (FE-C3)
- `components/onboarding/step-guard.tsx` — forward-skip guard (FE-C7)

**Created (cdai `apps/web/`):**
- `app/auth/callback/route.ts` — Supabase PKCE callback handler (FE-C2)
- `app/auth/__tests__/callback.test.ts` — callback route tests
- `app/(auth)/reset-password/page.tsx` — new password form (FE-C3)
- `middleware.test.ts` — middleware unit tests (FE-H1)
- `components/onboarding/__tests__/step-guard.test.tsx` — StepGuard tests (FE-C7)

**Modified (sage-poc):**
- `server.py` — `X-Sage-Api-Key` header validation (FE-H5)
- `tests/test_server.py` — 4 new API key tests

---

## Sub-group 2A: API Security

---

### Task 1: FE-C1 — Auth check at /api/chat

**Repo:** `cdai`
**Finding:** `POST /api/chat` is callable without a Supabase session. The middleware protects browser pages via cookie inspection but Next.js route handlers do not inherit middleware auth — they must check independently. Any unauthenticated HTTP client can call `/api/chat` directly, bypassing middleware entirely.
**Fix:** Call `supabase.auth.getUser()` at the top of the handler (before OpenRouter intent classification or any Supabase write) and return 401 if no user.

**Files:**
- Modify: `apps/web/app/api/chat/__tests__/route.test.ts`
- Modify: `apps/web/app/api/chat/route.ts`

- [ ] **Step 1: Rewrite the top of route.test.ts to add the auth mock, then add 3 new tests**

Open `apps/web/app/api/chat/__tests__/route.test.ts`.

Replace the top section (everything before the `function makeSageResponse` declaration, including `import { POST } from '../route'`) with:

```typescript
// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockInsert = vi.fn().mockResolvedValue({ error: null })
const mockSelect = vi.fn().mockReturnThis()
const mockEq = vi.fn().mockReturnThis()
const mockSingle = vi.fn().mockResolvedValue({ data: { name: null } })
const mockUpdate = vi.fn().mockReturnValue({ eq: vi.fn().mockResolvedValue({ error: null }) })
const mockGetUser = vi.fn().mockResolvedValue({
  data: { user: { id: 'test-user-id' } },
  error: null,
})

vi.mock('ai', () => ({
  generateText: vi.fn().mockResolvedValue({ text: 'emotional' }),
}))
vi.mock('@ai-sdk/openai', () => ({ createOpenAI: vi.fn(() => vi.fn()) }))
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
    from: () => ({
      insert: mockInsert,
      select: mockSelect,
      eq: mockEq,
      single: mockSingle,
      update: mockUpdate,
    }),
  }),
}))

import { POST } from '../route'
```

Replace the `beforeEach` block with:

```typescript
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetUser.mockResolvedValue({ data: { user: { id: 'test-user-id' } }, error: null })
    mockSingle.mockResolvedValue({ data: { name: null } })
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(makeSageResponse())
  })
```

Add these 3 tests inside the `describe` block (after the existing `'returns a streaming response'` test):

```typescript
  // ── FE-C1: authenticated access required ──────────────────────────────
  it('returns 401 when getUser returns no user', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('returns 401 when getUser returns an auth error', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: null },
      error: { message: 'JWT expired' },
    })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('does not call sage-poc when auth fails', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
      }),
    })
    await POST(req)
    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeUndefined()
  })
```

- [ ] **Step 2: Run tests to verify the 3 new tests fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run app/api/chat/__tests__/route.test.ts
```

Expected: 3 new FE-C1 tests FAIL. All 8 existing tests PASS.

- [ ] **Step 3: Implement the auth check in route.ts**

In `apps/web/app/api/chat/route.ts`, find:

```typescript
  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage).catch(() => 'emotional' as Intent)

  const supabase = await createClient()
  await supabase.from('messages').insert({
```

Replace with:

```typescript
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) return new Response('Unauthorized', { status: 401 })

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage).catch(() => 'emotional' as Intent)

  await supabase.from('messages').insert({
```

- [ ] **Step 4: Run tests to verify all pass**

```bash
npx vitest run app/api/chat/__tests__/route.test.ts
```

Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts apps/web/app/api/chat/__tests__/route.test.ts
git commit -m "security(FE-C1): require authenticated user on POST /api/chat"
```

---

### Task 2: FE-C4 — Session ownership verification in /api/chat

**Repo:** `cdai`
**Finding:** After auth passes, the handler accepts any `sessionId` in the request body including one belonging to another user. An authenticated attacker can inject messages into another user's session. RLS on `messages` may block the final insert, but we need an explicit 403 before any write or sage-poc call.
**Fix:** Double-eq query on `chat_sessions` (id + user_id) to verify ownership. Return 403 if the session doesn't belong to the authenticated user.

**Files:**
- Modify: `apps/web/app/api/chat/__tests__/route.test.ts`
- Modify: `apps/web/app/api/chat/route.ts`

- [ ] **Step 1: Add 2 failing ownership tests to route.test.ts**

Add inside the `describe` block:

```typescript
  // ── FE-C4: session ownership ───────────────────────────────────────────
  it('returns 403 when sessionId does not belong to the authenticated user', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'other-users-session',
      }),
    })
    const res = await POST(req)
    expect(res.status).toBe(403)
  })

  it('proceeds when session belongs to the authenticated user', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
  })
```

Note: `mockSingle` returns `{ data: { name: null } }` by default (set in `beforeEach`). `{ name: null }` is a truthy object, so the happy-path ownership check passes without extra setup. `mockResolvedValueOnce({ data: null })` simulates the RLS-blocked case.

- [ ] **Step 2: Run tests to verify the 2 new tests fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run app/api/chat/__tests__/route.test.ts
```

Expected: 2 new ownership tests FAIL. All 11 existing tests PASS.

- [ ] **Step 3: Implement the ownership check in route.ts**

In `apps/web/app/api/chat/route.ts`, after the `getUser()` check and before `supabase.from('messages').insert`, add:

```typescript
  const { data: ownedSession } = await supabase
    .from('chat_sessions')
    .select('id')
    .eq('id', sessionId)
    .eq('user_id', user.id)
    .single()
  if (!ownedSession) return new Response('Forbidden', { status: 403 })
```

The complete reordered block now reads:

```typescript
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()
  if (authError || !user) return new Response('Unauthorized', { status: 401 })

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage).catch(() => 'emotional' as Intent)

  const { data: ownedSession } = await supabase
    .from('chat_sessions')
    .select('id')
    .eq('id', sessionId)
    .eq('user_id', user.id)
    .single()
  if (!ownedSession) return new Response('Forbidden', { status: 403 })

  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })
```

- [ ] **Step 4: Run all route tests**

```bash
npx vitest run app/api/chat/__tests__/route.test.ts
```

Expected: All 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts apps/web/app/api/chat/__tests__/route.test.ts
git commit -m "security(FE-C4): verify sessionId ownership before inserting messages"
```

---

### Task 2b: FE-C4 — messageId ownership verification in /api/feedback

**Repo:** `cdai`
**Finding:** `feedback/route.ts` already has `getUser()` (FE-C1 is done). But it accepts any `messageId` — an authenticated user can submit feedback for messages belonging to another user's session, corrupting quality metrics used for model evaluation. The gap is the same pattern as Task 2.
**Fix:** Before upserting, verify `messageId` belongs to a message in a session owned by the authenticated user. Two queries: `messages` → get `session_id`, then `chat_sessions` → confirm `user_id` matches.

**Files:**
- Modify: `apps/web/app/api/feedback/__tests__/route.test.ts`
- Modify: `apps/web/app/api/feedback/route.ts`

- [ ] **Step 1: Expand the mock and add failing tests**

Open `apps/web/app/api/feedback/__tests__/route.test.ts`.

Replace the top section (mocks + `vi.mock` calls, before `import { POST }`) with:

```typescript
// apps/web/app/api/feedback/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockUpsert, mockGetUser, mockSelect, mockEq, mockSingle } = vi.hoisted(() => ({
  mockUpsert: vi.fn().mockResolvedValue({ error: null }),
  mockGetUser: vi.fn().mockResolvedValue({
    data: { user: { id: 'user-abc' } },
    error: null,
  }),
  mockSelect: vi.fn().mockReturnThis(),
  mockEq: vi.fn().mockReturnThis(),
  mockSingle: vi.fn(),
}))

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
    from: () => ({
      select: mockSelect,
      eq: mockEq,
      single: mockSingle,
      upsert: mockUpsert,
    }),
  }),
}))

import { POST } from '../route'
```

Replace `beforeEach` with:

```typescript
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-abc' } }, error: null })
    // Default: message exists in a session owned by the user.
    // single() is called twice: once for messages (returns session_id), once for
    // chat_sessions (returns any truthy object = ownership confirmed).
    mockSingle.mockResolvedValue({ data: { session_id: 'session-123' }, error: null })
  })
```

Add 2 new tests inside the `describe` block (after the existing tests):

```typescript
  // ── FE-C4: messageId ownership ────────────────────────────────────────
  it('returns 404 when messageId does not exist', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'nonexistent', value: 1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(404)
  })

  it('returns 403 when messageId belongs to another user', async () => {
    mockSingle
      .mockResolvedValueOnce({ data: { session_id: 'other-session' }, error: null })
      .mockResolvedValueOnce({ data: null, error: null })
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'other-msg', value: 1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(403)
  })
```

- [ ] **Step 2: Run tests to verify the 2 new tests fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run app/api/feedback/__tests__/route.test.ts
```

Expected: 2 new ownership tests FAIL. All 4 existing tests PASS.

- [ ] **Step 3: Implement the ownership check in feedback/route.ts**

In `apps/web/app/api/feedback/route.ts`, after the `getUser()` check and before the `upsert`, add:

```typescript
  const { data: msg } = await supabase
    .from('messages')
    .select('session_id')
    .eq('id', messageId)
    .single()
  if (!msg) return new Response('Not Found', { status: 404 })

  const { data: ownedSession } = await supabase
    .from('chat_sessions')
    .select('id')
    .eq('id', msg.session_id)
    .eq('user_id', user.id)
    .single()
  if (!ownedSession) return new Response('Forbidden', { status: 403 })
```

The complete file now reads:

```typescript
// apps/web/app/api/feedback/route.ts
import { createClient } from '@/lib/supabase/server'

export async function POST(req: Request) {
  const { messageId, value } = await req.json() as {
    messageId: string
    value: unknown
  }

  if (value !== 1 && value !== -1) {
    return new Response('value must be 1 or -1', { status: 400 })
  }

  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    return new Response('Unauthorized', { status: 401 })
  }

  const { data: msg } = await supabase
    .from('messages')
    .select('session_id')
    .eq('id', messageId)
    .single()
  if (!msg) return new Response('Not Found', { status: 404 })

  const { data: ownedSession } = await supabase
    .from('chat_sessions')
    .select('id')
    .eq('id', msg.session_id)
    .eq('user_id', user.id)
    .single()
  if (!ownedSession) return new Response('Forbidden', { status: 403 })

  const { error } = await supabase
    .from('message_feedback')
    .upsert(
      { message_id: messageId, user_id: user.id, value: value as 1 | -1 },
      { onConflict: 'message_id,user_id' }
    )

  if (error) {
    console.error('[feedback] upsert failed:', error)
    return new Response('Internal Server Error', { status: 500 })
  }

  return new Response('OK', { status: 200 })
}
```

- [ ] **Step 4: Run all feedback tests**

```bash
npx vitest run app/api/feedback/__tests__/route.test.ts
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/feedback/route.ts apps/web/app/api/feedback/__tests__/route.test.ts
git commit -m "security(FE-C4): verify messageId ownership in feedback route before upsert"
```

---

### Task 3: FE-H5 — Shared secret between route.ts and sage-poc

**Finding:** Any process on the server network can POST to `sage-poc /chat` directly, bypassing the auth added in Tasks 1–2. A shared `SAGE_API_KEY` env var prevents direct callers.
**Fix:** sage-poc reads `SAGE_API_KEY` per-request and rejects callers whose `X-Sage-Api-Key` header doesn't match. route.ts injects the header. The check is skipped when the env var is absent (backward-compatible for local dev with no key configured).

**This task touches two repos. Do 3a (sage-poc) then 3b (cdai).**

---

#### 3a — sage-poc: validate X-Sage-Api-Key

**Files:**
- Modify: `sage-poc/tests/test_server.py`
- Modify: `sage-poc/server.py`

- [ ] **Step 1: Add 4 failing tests to test_server.py**

Append to `sage-poc/tests/test_server.py`:

```python
# ── FE-H5: shared secret validation ───────────────────────────────────────
def test_chat_rejects_missing_api_key(monkeypatch):
    """Requests without X-Sage-Api-Key must be rejected when SAGE_API_KEY is configured."""
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test",
    })
    assert res.status_code == 401


def test_chat_rejects_wrong_api_key(monkeypatch):
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test",
    }, headers={"X-Sage-Api-Key": "wrong-key"})
    assert res.status_code == 401


def test_chat_accepts_correct_api_key(monkeypatch):
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test",
    }, headers={"X-Sage-Api-Key": "test-secret"})
    assert res.status_code == 200


def test_chat_bypasses_key_check_when_sage_api_key_unset():
    """No SAGE_API_KEY in env → check is disabled. Preserves backward compatibility
    for local dev where the key is not configured.
    """
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test",
    })
    assert res.status_code == 200
```

Note: the crisis message triggers a keyword match with no LLM call — these tests run fast without OpenRouter credentials.

- [ ] **Step 2: Run tests to verify 3 fail and 1 passes**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
pytest tests/test_server.py::test_chat_rejects_missing_api_key \
       tests/test_server.py::test_chat_rejects_wrong_api_key \
       tests/test_server.py::test_chat_accepts_correct_api_key \
       tests/test_server.py::test_chat_bypasses_key_check_when_sage_api_key_unset -v
```

Expected: 3 FAIL, 1 PASS (`test_chat_bypasses_key_check_when_sage_api_key_unset`).

- [ ] **Step 3: Implement in server.py**

Add `import os` after `import re as _re` in the imports block:

```python
import os
```

Add `Header` to the fastapi import:

```python
from fastapi import FastAPI, Header, HTTPException
```

Modify the `chat` endpoint signature and add the key check as the first line of the handler body:

```python
@app.post("/chat")
async def chat(req: ChatRequest, x_sage_api_key: str | None = Header(default=None)) -> StreamingResponse:
    _expected_key = os.environ.get("SAGE_API_KEY", "")
    if _expected_key and x_sage_api_key != _expected_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")
```

FastAPI maps `x_sage_api_key` to the HTTP header `X-Sage-Api-Key` (underscore↔hyphen, case-insensitive). `os.environ.get` is called per-request, so `monkeypatch.setenv` works correctly in tests.

- [ ] **Step 4: Run all 4 API key tests**

```bash
pytest tests/test_server.py::test_chat_rejects_missing_api_key \
       tests/test_server.py::test_chat_rejects_wrong_api_key \
       tests/test_server.py::test_chat_accepts_correct_api_key \
       tests/test_server.py::test_chat_bypasses_key_check_when_sage_api_key_unset -v
```

Expected: All 4 PASS.

- [ ] **Step 5: Run the full non-slow suite to confirm no regressions**

```bash
pytest tests/test_server.py -v -m "not slow"
```

Expected: All non-slow tests PASS (existing tests don't set `SAGE_API_KEY`, so check is bypassed).

- [ ] **Step 6: Commit sage-poc**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git add server.py tests/test_server.py
git commit -m "security(FE-H5): validate X-Sage-Api-Key header on /chat endpoint"
```

---

#### 3b — cdai: send X-Sage-Api-Key header from route.ts

**Files:**
- Modify: `apps/web/app/api/chat/__tests__/route.test.ts`
- Modify: `apps/web/app/api/chat/route.ts`

- [ ] **Step 7: Add 1 failing test to route.test.ts**

Add inside the `describe` block:

```typescript
  // ── FE-H5: X-Sage-Api-Key forwarded to sage-poc ───────────────────────
  it('sends X-Sage-Api-Key header to sage-poc when SAGE_API_KEY env is set', async () => {
    vi.stubEnv('SAGE_API_KEY', 'test-secret')
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
      }),
    })
    await POST(req)
    vi.unstubAllEnvs()

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeDefined()
    expect(sageCall![1].headers['X-Sage-Api-Key']).toBe('test-secret')
  })
```

- [ ] **Step 8: Run test to verify it fails**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run app/api/chat/__tests__/route.test.ts -t "X-Sage-Api-Key"
```

Expected: FAIL.

- [ ] **Step 9: Implement in route.ts**

In `apps/web/app/api/chat/route.ts`, find the sage fetch call:

```typescript
  const sageRes = await fetch(`${SAGE_API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
```

Replace with:

```typescript
  const sageRes = await fetch(`${SAGE_API_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(process.env.SAGE_API_KEY ? { 'X-Sage-Api-Key': process.env.SAGE_API_KEY } : {}),
    },
    body: JSON.stringify({
```

- [ ] **Step 10: Run all route tests**

```bash
npx vitest run app/api/chat/__tests__/route.test.ts
```

Expected: All 14 tests PASS.

- [ ] **Step 11: Commit cdai**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/api/chat/route.ts apps/web/app/api/chat/__tests__/route.test.ts
git commit -m "security(FE-H5): forward X-Sage-Api-Key header to sage-poc"
```

---

## Sub-group 2B: Auth Flows

---

### Task 4: FE-H1 — Replace getSession() with getUser() in middleware

**Repo:** `cdai`
**Finding:** `supabase.auth.getSession()` validates the JWT locally — it reads and parses the cookie without a network call. A revoked token passes until its `exp` claim lapses. `supabase.auth.getUser()` validates against the Supabase auth server on every request.
**Fix:** Replace `getSession()` with `getUser()` throughout middleware.ts. Update all `session` variable references to `user`.

**⚠ Pre-check required:** The plan replaces the entire `middleware.ts`. Before replacing, read the current file and confirm it matches the content shown in Step 2 below. The only logic blocks that should be present are: Supabase client init, auth gate, root redirect, admin check, and onboarding gate. If ANY additional logic is present (locale detection, RTL direction cookie, A/B flags, etc.), preserve it in the replacement. As of 2026-05-22, the current file contains none of these — but verify before replacing.

**Files:**
- Create: `apps/web/middleware.test.ts`
- Modify: `apps/web/middleware.ts`

- [ ] **Step 1: Write failing tests in middleware.test.ts**

Create `apps/web/middleware.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

const mockGetUser = vi.fn()
const mockGetSession = vi.fn()

vi.mock('@supabase/ssr', () => ({
  createServerClient: vi.fn(() => ({
    auth: { getUser: mockGetUser, getSession: mockGetSession },
    from: () => ({
      select: () => ({ eq: () => ({ single: () => Promise.resolve({ data: null }) }) }),
    }),
  })),
}))

import { middleware } from './middleware'

describe('middleware', () => {
  beforeEach(() => {
    mockGetUser.mockResolvedValue({ data: { user: null } })
    mockGetSession.mockResolvedValue({ data: { session: null } })
  })

  it('calls getUser() not getSession() to validate the session', async () => {
    const req = new NextRequest('http://localhost/chat')
    await middleware(req)
    expect(mockGetUser).toHaveBeenCalledTimes(1)
    expect(mockGetSession).not.toHaveBeenCalled()
  })

  it('redirects to /sign-in when user is null', async () => {
    const req = new NextRequest('http://localhost/chat')
    const res = await middleware(req)
    expect(res.status).toBe(307)
    expect(res.headers.get('location')).toContain('/sign-in')
  })

  it('returns 401 for /api routes when unauthenticated', async () => {
    const req = new NextRequest('http://localhost/api/chat')
    const res = await middleware(req)
    expect(res.status).toBe(401)
  })

  it('allows access to /sign-in without a session', async () => {
    const req = new NextRequest('http://localhost/sign-in')
    const res = await middleware(req)
    expect(res.status).not.toBe(307)
    expect(res.status).not.toBe(401)
  })
})
```

- [ ] **Step 2: Run tests to verify the getUser test fails**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run middleware.test.ts
```

Expected: `'calls getUser() not getSession()'` FAILS. Others may pass or fail depending on Next.js mock resolution.

- [ ] **Step 3: Read current middleware.ts and confirm pre-check**

Read `apps/web/middleware.ts`. Confirm its complete content is exactly:

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (toSet) => toSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        ),
      },
    }
  )

  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    if (pathname.startsWith('/api/')) {
      return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    if (!AUTH_PATHS.some(p => pathname.startsWith(p))) {
      return NextResponse.redirect(new URL('/sign-in', request.url))
    }
  }

  if (session && pathname === '/') {
    return NextResponse.redirect(new URL('/chat', request.url))
  }

  if (session && !AUTH_PATHS.some(p => pathname.startsWith(p)) && pathname !== '/') {
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('is_admin, onboarding_complete, onboarding_step')
      .eq('id', session.user.id)
      .single()

    if (pathname.startsWith('/admin') && !profile?.is_admin) {
      return new NextResponse(null, { status: 403 })
    }

    const isOnboardingStep = /^\/step-[1-6]$/.test(pathname)
    const needsOnboarding = !profile || !profile.onboarding_complete
    if (!pathname.startsWith('/admin') && !isOnboardingStep && needsOnboarding) {
      const step = profile?.onboarding_step
      const target = step && step > 0 ? `/step-${step}` : '/step-1'
      return NextResponse.redirect(new URL(target, request.url))
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|offline.html).*)'],
}
```

If the file contains anything beyond this — stop and preserve it in the replacement below before proceeding.

- [ ] **Step 4: Replace middleware.ts**

Replace the entire contents of `apps/web/middleware.ts` with:

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (toSet) => toSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        ),
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  // Unauthenticated → sign-in (skip auth routes themselves)
  if (!user) {
    if (pathname.startsWith('/api/')) {
      return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    if (!AUTH_PATHS.some(p => pathname.startsWith(p))) {
      return NextResponse.redirect(new URL('/sign-in', request.url))
    }
  }

  // Root redirect
  if (user && pathname === '/') {
    return NextResponse.redirect(new URL('/chat', request.url))
  }

  // Single profile fetch — used for both admin check and onboarding gate.
  // Never make two round-trips to Supabase per middleware call.
  if (user && !AUTH_PATHS.some(p => pathname.startsWith(p)) && pathname !== '/') {
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('is_admin, onboarding_complete, onboarding_step')
      .eq('id', user.id)
      .single()

    if (pathname.startsWith('/admin') && !profile?.is_admin) {
      return new NextResponse(null, { status: 403 })
    }

    const isOnboardingStep = /^\/step-[1-6]$/.test(pathname)
    const needsOnboarding = !profile || !profile.onboarding_complete
    if (!pathname.startsWith('/admin') && !isOnboardingStep && needsOnboarding) {
      const step = profile?.onboarding_step
      const target = step && step > 0 ? `/step-${step}` : '/step-1'
      return NextResponse.redirect(new URL(target, request.url))
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|offline.html).*)'],
}
```

- [ ] **Step 5: Run tests**

```bash
npx vitest run middleware.test.ts
```

Expected: All 4 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/middleware.ts apps/web/middleware.test.ts
git commit -m "security(FE-H1): replace getSession() with getUser() in middleware for server-side token validation"
```

---

### Task 5: FE-C2 — Auth callback route

**Repo:** `cdai`
**Finding:** Email confirmation and password reset links redirect to `/auth/callback?code=xxx`. The middleware sees `/auth/callback` as a protected route — no session exists yet because the code hasn't been exchanged — so it redirects to `/sign-in`. The callback is never reached; email confirmation silently fails.
**Fix:** Add `/auth/callback` to `AUTH_PATHS`. Create the PKCE callback handler. Validate the `next` parameter to prevent open redirect — `//evil.com` passes a simple `startsWith('/')` check, so use `startsWith('/') && !startsWith('//')`.

**Files:**
- Create: `apps/web/app/auth/callback/route.ts`
- Create: `apps/web/app/auth/__tests__/callback.test.ts`
- Modify: `apps/web/middleware.ts`

- [ ] **Step 1: Create the test directory and write failing tests**

Create `apps/web/app/auth/__tests__/callback.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

const mockExchangeCode = vi.fn()
const mockCookieStore = { getAll: vi.fn(() => []), set: vi.fn() }

vi.mock('next/headers', () => ({
  cookies: vi.fn().mockResolvedValue(mockCookieStore),
}))
vi.mock('@supabase/ssr', () => ({
  createServerClient: vi.fn(() => ({
    auth: { exchangeCodeForSession: mockExchangeCode },
  })),
}))

import { GET } from '../callback/route'

describe('GET /auth/callback', () => {
  beforeEach(() => {
    mockExchangeCode.mockResolvedValue({ error: null })
    mockCookieStore.getAll.mockClear()
    mockCookieStore.set.mockClear()
  })

  it('exchanges code and redirects to /chat by default', async () => {
    const req = new NextRequest('http://localhost/auth/callback?code=test-code')
    const res = await GET(req)
    expect(mockExchangeCode).toHaveBeenCalledWith('test-code')
    expect(res.status).toBe(307)
    expect(res.headers.get('location')).toContain('/chat')
  })

  it('redirects to the next param path after successful exchange', async () => {
    const req = new NextRequest(
      'http://localhost/auth/callback?code=test-code&next=/reset-password'
    )
    const res = await GET(req)
    expect(res.headers.get('location')).toContain('/reset-password')
  })

  it('redirects to /sign-in with error on exchange failure', async () => {
    mockExchangeCode.mockResolvedValue({ error: { message: 'invalid code' } })
    const req = new NextRequest('http://localhost/auth/callback?code=bad-code')
    const res = await GET(req)
    expect(res.headers.get('location')).toContain('/sign-in')
    expect(res.headers.get('location')).toContain('error=callback-failed')
  })

  it('redirects to /sign-in when no code param is present', async () => {
    const req = new NextRequest('http://localhost/auth/callback')
    const res = await GET(req)
    expect(res.headers.get('location')).toContain('/sign-in')
    expect(mockExchangeCode).not.toHaveBeenCalled()
  })

  it('rejects non-relative next paths to prevent open redirect', async () => {
    const req = new NextRequest(
      'http://localhost/auth/callback?code=test-code&next=https://evil.com'
    )
    const res = await GET(req)
    expect(res.headers.get('location')).not.toContain('evil.com')
    expect(res.headers.get('location')).toContain('/chat')
  })

  it('rejects protocol-relative next paths to prevent open redirect', async () => {
    const req = new NextRequest(
      'http://localhost/auth/callback?code=test-code&next=//evil.com'
    )
    const res = await GET(req)
    expect(res.headers.get('location')).not.toContain('evil.com')
    expect(res.headers.get('location')).toContain('/chat')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run app/auth/__tests__/callback.test.ts
```

Expected: All 6 FAIL (route doesn't exist yet).

- [ ] **Step 3: Create the callback route handler**

Create `apps/web/app/auth/callback/route.ts`:

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const rawNext = searchParams.get('next') ?? '/chat'
  // Reject absolute URLs and protocol-relative paths (e.g. //evil.com) — both
  // would be resolved by new URL() to an external domain.
  const next = (rawNext.startsWith('/') && !rawNext.startsWith('//')) ? rawNext : '/chat'

  if (code) {
    const cookieStore = await cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll: () => cookieStore.getAll(),
          setAll: (cookiesToSet) =>
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            ),
        },
      }
    )
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(new URL(next, origin))
    }
  }

  return NextResponse.redirect(new URL('/sign-in?error=callback-failed', origin))
}
```

- [ ] **Step 4: Add `/auth/callback` to AUTH_PATHS in middleware.ts**

In `apps/web/middleware.ts`, replace:

```typescript
const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password']
```

With:

```typescript
const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password', '/auth/callback']
```

- [ ] **Step 5: Run all affected tests**

```bash
npx vitest run app/auth/__tests__/callback.test.ts middleware.test.ts
```

Expected: All 10 PASS (6 callback + 4 middleware).

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/auth/callback/route.ts \
        apps/web/app/auth/__tests__/callback.test.ts \
        apps/web/middleware.ts
git commit -m "security(FE-C2): add /auth/callback PKCE handler with open-redirect guard"
```

---

### Task 6: FE-C3 — Password reset page

**Repo:** `cdai`
**Finding:** `forgot-password/page.tsx` sets `redirectTo: /sign-in`. Supabase emails a link to `/sign-in` but there's no recovery session handler there — users arrive at the sign-in page with no way to set a new password.
**Fix:** Change `redirectTo` to use the callback route from Task 5. Create the reset-password page. Add `/reset-password` to `AUTH_PATHS` so the middleware doesn't run the onboarding gate on a user mid-recovery-flow (who may have `onboarding_complete = false`).

**Files:**
- Modify: `apps/web/app/(auth)/forgot-password/page.tsx`
- Modify: `apps/web/middleware.ts`
- Create: `apps/web/app/(auth)/reset-password/page.tsx`

- [ ] **Step 1: Update redirectTo in forgot-password/page.tsx**

In `apps/web/app/(auth)/forgot-password/page.tsx`, replace:

```typescript
      redirectTo: `${window.location.origin}/sign-in`,
```

With:

```typescript
      redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
```

- [ ] **Step 2: Add `/reset-password` to AUTH_PATHS in middleware.ts**

In `apps/web/middleware.ts`, replace:

```typescript
const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password', '/auth/callback']
```

With:

```typescript
const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password', '/auth/callback', '/reset-password']
```

- [ ] **Step 3: Create the reset-password page**

Create `apps/web/app/(auth)/reset-password/page.tsx`:

```typescript
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button, Input } from '@cdai/ui'

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const supabase = createClient()
    const { error } = await supabase.auth.updateUser({ password })
    setLoading(false)
    if (error) { setError(error.message); return }
    router.push('/chat')
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">Set new password</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Choose a new password for your account
        </p>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Input
          type="password"
          placeholder="New password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={6}
          required
        />
        {error && <p className="text-xs text-[var(--color-crisis)]">{error}</p>}
        <Button type="submit" disabled={loading}>
          {loading ? 'Updating...' : 'Update password'}
        </Button>
      </form>
    </div>
  )
}
```

- [ ] **Step 4: Run middleware tests to confirm AUTH_PATHS change doesn't break anything**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run middleware.test.ts
```

Expected: All 4 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/(auth)/forgot-password/page.tsx \
        apps/web/app/(auth)/reset-password/page.tsx \
        apps/web/middleware.ts
git commit -m "security(FE-C3): add password reset page and fix forgot-password redirectTo"
```

---

## Sub-group 2C: Onboarding

---

### Task 7: FE-C7 — StepGuard forward-skip prevention

**Repo:** `cdai`
**Finding:** `StepGuard` only prevents backward navigation (`storedStep > pageStep` → redirect to `storedStep`). A user on step 2 can navigate directly to `/step-5` by typing the URL — no redirect occurs.
**Fix:** Add `else if (storedStep < pageStep)` to redirect forward-skippers back to their current step.

**Files:**
- Create: `apps/web/components/onboarding/__tests__/step-guard.test.tsx`
- Modify: `apps/web/components/onboarding/step-guard.tsx`

- [ ] **Step 1: Write failing tests**

Create `apps/web/components/onboarding/__tests__/step-guard.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { StepGuard } from '../step-guard'

const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace: mockReplace }) }))

let mockStep = 1
vi.mock('@/lib/stores/onboarding-store', () => ({
  useOnboardingStore: (sel: (s: { step: number }) => number) => sel({ step: mockStep }),
}))

describe('StepGuard', () => {
  beforeEach(() => {
    mockReplace.mockClear()
    mockStep = 1
  })

  it('renders children without redirecting when storedStep equals pageStep', () => {
    mockStep = 3
    const { getByText } = render(
      <StepGuard pageStep={3}><div>content</div></StepGuard>
    )
    expect(getByText('content')).toBeTruthy()
    expect(mockReplace).not.toHaveBeenCalled()
  })

  it('redirects backward navigator to storedStep when storedStep > pageStep', () => {
    mockStep = 5
    render(<StepGuard pageStep={2}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-5')
  })

  it('caps backward redirect at step 6', () => {
    mockStep = 8
    render(<StepGuard pageStep={1}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-6')
  })

  it('redirects forward-skipper to storedStep when storedStep < pageStep', () => {
    mockStep = 2
    render(<StepGuard pageStep={5}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-2')
  })

  it('does not redirect when storedStep equals pageStep', () => {
    mockStep = 1
    render(<StepGuard pageStep={1}><div /></StepGuard>)
    expect(mockReplace).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run tests to verify the forward-skip test fails**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx vitest run components/onboarding/__tests__/step-guard.test.tsx
```

Expected: `'redirects forward-skipper'` FAILS. All 4 others PASS.

- [ ] **Step 3: Implement the fix in step-guard.tsx**

In `apps/web/components/onboarding/step-guard.tsx`, replace:

```typescript
  useEffect(() => {
    if (storedStep > pageStep) {
      router.replace(`/step-${Math.min(storedStep, 6)}`)
    }
  }, [storedStep, pageStep, router])
```

With:

```typescript
  useEffect(() => {
    if (storedStep > pageStep) {
      router.replace(`/step-${Math.min(storedStep, 6)}`)
    } else if (storedStep < pageStep) {
      router.replace(`/step-${storedStep}`)
    }
  }, [storedStep, pageStep, router])
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run components/onboarding/__tests__/step-guard.test.tsx
```

Expected: All 5 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/components/onboarding/step-guard.tsx \
        apps/web/components/onboarding/__tests__/step-guard.test.tsx
git commit -m "security(FE-C7): prevent forward-skip in StepGuard"
```

---

## Post-implementation

After all tasks are committed, push both repos:

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc && git push origin master
cd /Users/knowledgebase/Documents/Sage/cdai && git push origin main
```

**Environment variables required before production deploy:**
- `SAGE_API_KEY` — same random string in both sage-poc and cdai deployments. Server-side only — never use `NEXT_PUBLIC_` prefix. Set `SAGE_API_KEY=dummy-ci` in CI env for both repos' workflow files.

**Browser QA checklist (manual, after staging deploy):**
1. POST to `/api/chat` without a session (incognito + curl) → expect 401.
2. POST to `/api/feedback` with a `messageId` from a different user → expect 403.
3. Sign up → click email confirmation link → should land on `/chat`, not `/sign-in`.
4. Forgot password → receive email → click link → should land on `/reset-password` → set password → redirect to `/chat`.
5. During onboarding at step 2, type `/step-5` in address bar → should redirect back to step 2.
