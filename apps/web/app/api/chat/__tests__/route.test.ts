// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

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
      'X-Sage-Active-Step-Id':       '',
      'X-Sage-Gate-Path':            'standard',
      'X-Sage-Crisis-Flags':         '[]',
      'X-Sage-Clinical-Flags':       '[]',
      'X-Sage-Emotional-Intensity':  '5',
      'X-Sage-Crisis-State':         'none',
      'X-Sage-Distress-Trajectory':  '[]',
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
        sessionId: 'test-session-id',
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
        sessionId: 'test-session-id',
      }),
    })
    await POST(req)
    await new Promise((r) => setTimeout(r, 50))

    const calls = mockInsert.mock.calls
    const aiInsert = calls.find((c) => c[0]?.role === 'ai' || c[0]?.role === 'crisis')
    expect(aiInsert).toBeDefined()
    const payload = aiInsert![0]
    expect(payload).toMatchObject({
      intent_classification: 'general_chat',
      semantic_score: 0.87,
      prompt_layers: ['persona', 'history'],
      token_usage: { input: 200, output: 45, total: 245 },
      turn_number: 1,
    })
  })

  // ── INT-C1: crisis state forwarded to sage-poc ────────────────────────────
  it('forwards crisisState from request body to sage-poc as crisis_state', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I feel better now' }],
        sessionId: 'test-session-id',
        crisisState: 'monitoring',
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeDefined()
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.crisis_state).toBe('monitoring')
  })

  it('forwards activeSkillId and activeStepId to sage-poc', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'continue' }],
        sessionId: 'test-session-id',
        activeSkillId: 'cbt_thought_record',
        activeStepId: 'explore_distortion',
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.active_skill_id).toBe('cbt_thought_record')
    expect(body.active_step_id).toBe('explore_distortion')
  })

  it('uses default values for missing state fields (backward compatibility)', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
        // crisisState, activeSkillId, etc. intentionally omitted
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    const body = JSON.parse(sageCall![1].body as string)
    expect(body.crisis_state).toBe('none')
    expect(body.active_skill_id).toBeNull()
    expect(body.active_step_id).toBeNull()
    expect(body.clinical_flags).toEqual([])
    expect(body.distress_trajectory).toEqual([])
  })

  // ── INT-C2: sage-poc headers forwarded to browser ─────────────────────────
  it('forwards X-Sage-Crisis-State to the browser response', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeSageResponse('hello', { 'X-Sage-Crisis-State': 'monitoring' })
    )
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I am struggling' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Crisis-State')).toBe('monitoring')
  })

  it('forwards X-Sage-Skill-Id and X-Sage-Active-Step-Id to the browser response', async () => {
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
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Skill-Id')).toBe('cbt_thought_record')
    expect(res.headers.get('X-Sage-Active-Step-Id')).toBe('explore_distortion')
  })

  it('forwards X-Sage-Clinical-Flags and X-Sage-Distress-Trajectory to the browser', async () => {
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
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res.headers.get('X-Sage-Clinical-Flags')).toBe('["trauma_indicator"]')
    expect(res.headers.get('X-Sage-Distress-Trajectory')).toBe('[8,7,6]')
  })

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

  it('does not write to Supabase when auth fails', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hello' }],
        sessionId: 'test-session-id',
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
        sessionId: 'session-1',
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
        sessionId: 'session-1',
      }),
    })
    const res = await POST(req)
    expect(res.status).not.toBe(403)
    expect(mockInsert).toHaveBeenCalled()
  })

  it('does not write to Supabase when session ownership check fails', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'hi' }],
        sessionId: 'session-1',
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
        sessionId: 'test-session-id',
      }),
    })
    await POST(req)

    const fetchCalls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls
    const sageCall = fetchCalls.find((c) => (c[0] as string).includes('/chat'))
    expect(sageCall).toBeDefined()
    expect(sageCall![1].headers['X-Sage-Api-Key']).toBe('test-secret')
  })
})
