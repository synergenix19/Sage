// apps/web/app/api/feedback/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockUpsert, mockGetUser } = vi.hoisted(() => ({
  mockUpsert: vi.fn().mockResolvedValue({ error: null }),
  mockGetUser: vi.fn().mockResolvedValue({
    data: { user: { id: 'user-abc' } },
    error: null,
  }),
}))

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
    from: () => ({ upsert: mockUpsert }),
  }),
}))

import { POST } from '../route'

describe('POST /api/feedback', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns 401 when user is not authenticated', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: 1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('returns 400 when value is not 1 or -1', async () => {
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: 0 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(400)
  })

  it('upserts feedback for thumbs up', async () => {
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: 1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(mockUpsert).toHaveBeenCalledWith(
      { message_id: 'msg-1', user_id: 'user-abc', value: 1 },
      { onConflict: 'message_id,user_id' }
    )
  })

  it('upserts feedback for thumbs down', async () => {
    const req = new Request('http://localhost/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ messageId: 'msg-1', value: -1 }),
    })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(mockUpsert).toHaveBeenCalledWith(
      { message_id: 'msg-1', user_id: 'user-abc', value: -1 },
      { onConflict: 'message_id,user_id' }
    )
  })
})
