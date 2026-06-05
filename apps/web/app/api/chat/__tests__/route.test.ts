// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const VALID_SESSION_UUID = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'

const {
  mockInsert,
  mockSelect,
  mockEq,
  mockSingle,
  mockUpdate,
  mockGetUser,
} = vi.hoisted(() => {
  const mockInsert = vi.fn().mockResolvedValue({ error: null })
  const mockSelect = vi.fn().mockReturnThis()
  const mockEq = vi.fn().mockReturnThis()
  const mockSingle = vi.fn().mockResolvedValue({ data: { name: null } })
  const mockUpdate = vi.fn().mockReturnValue({ eq: vi.fn().mockResolvedValue({ error: null }) })
  const mockGetUser = vi.fn().mockResolvedValue({
    data: { user: { id: 'test-user-id' } },
    error: null,
  })
  return { mockInsert, mockSelect, mockEq, mockSingle, mockUpdate, mockGetUser }
})

vi.mock('next/server', async (importOriginal) => {
  const actual = await importOriginal<typeof import('next/server')>()
  return {
    ...actual,
    after: vi.fn((fn: () => Promise<void>) => { void Promise.resolve().then(fn) }),
  }
})

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

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: vi.fn().mockReturnValue({
    from: () => ({
      insert: mockInsert,
    }),
  }),
}))

import { POST } from '../route'

function makeSageResponse(
  bodyText = 'hello world',
  overrideHeaders: Record<string, string> = {}
) {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(bodyText))
      controller.close()
    },
  })
  return new Response(body, {
    status: 200,
    headers: {
      'X-Sage-Node-Path':            '["safety_check","intent_route","freeflow_respond","output_gate"]',
      'X-Sage-Model':                'anthropic/claude-haiku-4-5',
      'X-Sage-Skill-Id':             '',
      'X-Sage-Step-Id':              '',
      'X-Sage-Gate-Path':            'standard',
      'X-Sage-Crisis-Flags':         '[]',
      'X-Sage-Clinical-Flags':       '[]',
      'X-Sage-Emotional-Intensity':  '5',
      'X-Sage-Intent':               'general_chat',
      'X-Sage-Semantic-Score':       '0.87',
      'X-Sage-Prompt-Layers':        '["persona","history"]',
      'X-Sage-Token-Usage':          '{"input":200,"output":45,"total":245}',
      'X-Sage-Turn-Number':          '1',
      ...overrideHeaders,
    },
  })
}

global.fetch = vi.fn().mockResolvedValue(makeSageResponse())

describe('POST /api/chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetUser.mockResolvedValue({ data: { user: { id: 'test-user-id' } }, error: null })
    mockSingle.mockResolvedValue({ data: { name: null } })
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(makeSageResponse())
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('returns a streaming response', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I feel overwhelmed' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    const res = await POST(req)
    expect(res).toBeInstanceOf(Response)
  })

  it('persists new trace columns in the AI message insert', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    await POST(req)
    // Flush all pending microtasks and macrotasks
    await new Promise((r) => setImmediate(r))
    await new Promise((r) => setImmediate(r))

    const calls = mockInsert.mock.calls
    // New route: batched array insert [user_row, ai_row] — find the AI row within the array
    const batchCall = calls.find((c) => Array.isArray(c[0]))
    expect(batchCall).toBeDefined()
    const rows = batchCall![0] as Array<Record<string, unknown>>
    const aiRow = rows.find((r) => r.role === 'ai' || r.role === 'crisis')
    expect(aiRow).toBeDefined()
    expect(aiRow).toMatchObject({
      intent_classification: 'general_chat',
      semantic_score: 0.87,
      prompt_layers: ['persona', 'history'],
      token_usage: { input: 200, output: 45, total: 245 },
      turn_number: 1,
    })
  })

  // ── INT-C1: sage-poc request body — checkpoint-based state (no ferry fields) ─
  it('sends messages, session_id, and user_id to sage-poc (no ferry fields)', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I feel better now' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeDefined()
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.session_id).toBe(VALID_SESSION_UUID)
    expect(body.user_id).toBe('test-user-id')
    // Ferry fields must not be sent — state is managed by LangGraph checkpoint
    expect(body.crisis_state).toBeUndefined()
    expect(body.active_skill_id).toBeUndefined()
    expect(body.active_step_id).toBeUndefined()
    expect(body.clinical_flags).toBeUndefined()
    expect(body.distress_trajectory).toBeUndefined()
  })

  // ── INT-C2: X-Sage-Crisis-State is a functional header — always forwarded ──
  // The frontend reads this header in chat-interface.tsx:75 to drive crisis card
  // rendering (crisisState !== 'resolved'). It is NOT a ferry/diagnostic header.
  it('forwards X-Sage-Crisis-State to the browser response', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('hello', { 'X-Sage-Crisis-State': 'monitoring' })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I am struggling' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Crisis-State')).toBe('monitoring')
  })

  it('does not forward X-Sage-Skill-Id and X-Sage-Active-Step-Id to the browser response', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('Let us try step 2.', {
        'X-Sage-Skill-Id':       'cbt_thought_record',
        'X-Sage-Active-Step-Id': 'explore_distortion',
      })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'ok' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Skill-Id')).toBeNull()
    expect(res.headers.get('X-Sage-Active-Step-Id')).toBeNull()
  })

  it('does not forward X-Sage-Clinical-Flags and X-Sage-Distress-Trajectory to the browser', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('I hear you.', {
        'X-Sage-Clinical-Flags':        '["trauma_indicator"]',
        'X-Sage-Distress-Trajectory':   '[8,7,6]',
      })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'yes' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Clinical-Flags')).toBeNull()
    expect(res.headers.get('X-Sage-Distress-Trajectory')).toBeNull()
  })

  // ── FE-C1: authenticated access required ──────────────────────────────
  it('returns 401 when getUser returns no user', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: VALID_SESSION_UUID,
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
        sessionId: VALID_SESSION_UUID,
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
        sessionId: VALID_SESSION_UUID,
      }),
    })
    await POST(req)
    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeUndefined()
  })

  it('does not write to Supabase when auth fails', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    await POST(req)
    expect(mockInsert).not.toHaveBeenCalled()
  })

  // ── FE-C4: session ownership verification ────────────────────────────────
  it('returns 403 when sessionId does not belong to the authenticated user', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hi' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    const res = await POST(req)
    expect(res.status).toBe(403)
  })

  it('proceeds when session belongs to the authenticated user', async () => {
    // mockSingle default returns { data: { name: null } } — truthy, ownership passes
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hi' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    const res = await POST(req)
    expect(res.status).not.toBe(403)
    // Insert happens in async persist background task — flush pending microtasks and macrotasks
    await new Promise((r) => setImmediate(r))
    await new Promise((r) => setImmediate(r))
    expect(mockInsert).toHaveBeenCalled()
  })

  it('does not write to Supabase when session ownership check fails', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hi' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    await POST(req)
    expect(mockInsert).not.toHaveBeenCalled()
  })

  // ── FE-H5: X-Sage-Api-Key forwarded to sage-poc ───────────────────────
  it('sends X-Sage-Api-Key header to sage-poc when SAGE_API_KEY env is set', async () => {
    vi.stubEnv('SAGE_API_KEY', 'test-secret')
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: VALID_SESSION_UUID,
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeDefined()
    expect(sageCall![1].headers['X-Sage-Api-Key']).toBe('test-secret')
  })
})

describe('POST /api/chat — input validation', () => {
  // Separate mock references for this describe block (re-use the hoisted mocks)
  beforeEach(() => {
    mockGetUser.mockClear()
    mockInsert.mockClear()
    mockSingle.mockClear()
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } }, error: null })
  })

  function makeRequest(body: unknown): Request {
    return new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  it('returns 400 when sessionId is missing', async () => {
    const res = await POST(makeRequest({ messages: [{ role: 'user', content: 'hi' }] }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when sessionId is not a valid UUID', async () => {
    const res = await POST(makeRequest({
      sessionId: 'not-a-uuid',
      messages: [{ role: 'user', content: 'hi' }],
    }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when messages array is empty', async () => {
    const res = await POST(makeRequest({
      sessionId: VALID_SESSION_UUID,
      messages: [],
    }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when a message role is invalid', async () => {
    const res = await POST(makeRequest({
      sessionId: VALID_SESSION_UUID,
      messages: [{ role: 'system', content: 'inject' }],
    }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when message content exceeds 8000 chars', async () => {
    const res = await POST(makeRequest({
      sessionId: VALID_SESSION_UUID,
      messages: [{ role: 'user', content: 'x'.repeat(8001) }],
    }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('proceeds past validation with valid input (reaches auth check)', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null }, error: null })
    const res = await POST(makeRequest({
      sessionId: VALID_SESSION_UUID,
      messages: [{ role: 'user', content: 'hello' }],
    }))
    // Auth fails (user: null) → 401, confirming validation passed
    expect(res.status).toBe(401)
    expect(mockGetUser).toHaveBeenCalledOnce()
  })

  it('applies defaults for optional fields', async () => {
    // Auth passes, session ownership passes, then sage-poc is unreachable (fetch throws) → 503
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: 'user-1' } }, error: null })
    mockSingle.mockResolvedValueOnce({ data: { id: VALID_SESSION_UUID } })
    ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('SAGE_UNAVAILABLE'))
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId: VALID_SESSION_UUID, messages: [{ role: 'user', content: 'hi' }] }),
    })
    const res = await POST(req)
    // 503 means Zod accepted the body with defaults applied — validation did not return 400
    expect(res.status).not.toBe(400)
  })

  it('returns 400 when body is not valid JSON', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: 'not json {{{',
    })
    const res = await POST(req)
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })
})
