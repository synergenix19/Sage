// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('ai', () => ({
  generateText: vi.fn().mockResolvedValue({ text: 'emotional' }),
  streamText: vi.fn().mockReturnValue({
    toTextStreamResponse: () => new Response('ok'),
  }),
}))
vi.mock('@ai-sdk/openai', () => ({ createOpenAI: vi.fn(() => vi.fn()) }))
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    from: () => ({
      insert: vi.fn().mockResolvedValue({ error: null }),
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ data: { name: null } }),
      update: vi.fn().mockReturnThis(),
    }),
  }),
}))

import { POST } from '../route'

describe('POST /api/chat', () => {
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
})
