// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockInsert = vi.fn().mockResolvedValue({ error: null })
const mockSelect = vi.fn().mockReturnThis()
const mockEq = vi.fn().mockReturnThis()
const mockSingle = vi.fn().mockResolvedValue({ data: { name: null } })
const mockUpdate = vi.fn().mockReturnValue({ eq: vi.fn().mockResolvedValue({ error: null }) })

vi.mock('ai', () => ({
  generateText: vi.fn().mockResolvedValue({ text: 'emotional' }),
}))
vi.mock('@ai-sdk/openai', () => ({ createOpenAI: vi.fn(() => vi.fn()) }))
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    from: () => ({ insert: mockInsert, select: mockSelect, eq: mockEq, single: mockSingle, update: mockUpdate }),
  }),
}))

import { POST } from '../route'

function makeSageResponse(headers: Record<string, string> = {}) {
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('hello world'))
      controller.close()
    },
  })
  return new Response(body, {
    status: 200,
    headers: {
      'X-Sage-Node-Path':           '["safety_check","intent_route","freeflow_respond","output_gate"]',
      'X-Sage-Model':               'anthropic/claude-haiku-4-5',
      'X-Sage-Skill-Id':            '',
      'X-Sage-Step-Id':             '',
      'X-Sage-Gate-Path':           'standard',
      'X-Sage-Crisis-Flags':        '[]',
      'X-Sage-Clinical-Flags':      '[]',
      'X-Sage-Emotional-Intensity': '5',
      'X-Sage-Intent':              'general_chat',
      'X-Sage-Semantic-Score':      '0.87',
      'X-Sage-Prompt-Layers':       '["persona","history"]',
      'X-Sage-Token-Usage':         '{"input":200,"output":45,"total":245}',
      'X-Sage-Turn-Number':         '1',
      'X-Sage-Ai-Message-Id':       'test-ai-msg-uuid',
      ...headers,
    },
  })
}

vi.mock('node-fetch', () => ({ default: vi.fn() }))

// Override global fetch for the sage backend call
global.fetch = vi.fn().mockResolvedValue(makeSageResponse())

describe('POST /api/chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(makeSageResponse())
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
    // Give the background persist time to run
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
})
