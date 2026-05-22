// apps/web/app/api/feedback/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const VALID_MSG_UUID = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'

const { mockUpsert, mockGetUser, mockSelect, mockEq, mockSingle } = vi.hoisted(() => ({
  mockUpsert: vi.fn().mockResolvedValue({ error: null }),
  mockGetUser: vi.fn().mockResolvedValue({
    data: { user: { id: 'user-abc' } },
    error: null,
  }),
  mockSelect: vi.fn().mockReturnThis(),
  mockEq: vi.fn().mockReturnThis(),
  mockSingle: vi.fn().mockResolvedValue({ data: { session_id: 'session-1' } }),
}))

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
    from: () => ({
      upsert: mockUpsert,
      select: mockSelect,
      eq: mockEq,
      single: mockSingle,
    }),
  }),
}))

import { POST } from '../route'

function makeRequest(body: Record<string, unknown>) {
  return new Request('http://localhost/api/feedback', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

describe('POST /api/feedback', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns 401 when user is not authenticated', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null })
    const req = makeRequest({ messageId: VALID_MSG_UUID, value: 1 })
    const res = await POST(req)
    expect(res.status).toBe(401)
  })

  it('returns 400 when value is not 1 or -1', async () => {
    const req = makeRequest({ messageId: VALID_MSG_UUID, value: 0 })
    const res = await POST(req)
    expect(res.status).toBe(400)
  })

  it('upserts feedback for thumbs up', async () => {
    const req = makeRequest({ messageId: VALID_MSG_UUID, value: 1 })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(mockUpsert).toHaveBeenCalledWith(
      { message_id: VALID_MSG_UUID, user_id: 'user-abc', value: 1 },
      { onConflict: 'message_id,user_id' }
    )
  })

  it('upserts feedback for thumbs down', async () => {
    const req = makeRequest({ messageId: VALID_MSG_UUID, value: -1 })
    const res = await POST(req)
    expect(res.status).toBe(200)
    expect(mockUpsert).toHaveBeenCalledWith(
      { message_id: VALID_MSG_UUID, user_id: 'user-abc', value: -1 },
      { onConflict: 'message_id,user_id' }
    )
  })

  it('returns 404 when messageId does not exist', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = makeRequest({ messageId: VALID_MSG_UUID, value: 1 })
    const res = await POST(req)
    expect(res.status).toBe(404)
    expect(mockUpsert).not.toHaveBeenCalled()
  })

  it('returns 403 when message session does not belong to the authenticated user', async () => {
    // First single() call (message lookup) succeeds
    mockSingle.mockResolvedValueOnce({ data: { session_id: 'session-1' }, error: null })
    // Second single() call (session ownership) returns null → 403
    mockSingle.mockResolvedValueOnce({ data: null, error: null })
    const req = makeRequest({ messageId: VALID_MSG_UUID, value: 1 })
    const res = await POST(req)
    expect(res.status).toBe(403)
    expect(mockUpsert).not.toHaveBeenCalled()
  })
})

describe('POST /api/feedback — input validation', () => {
  beforeEach(() => {
    mockGetUser.mockClear()
    mockUpsert.mockClear()
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-abc' } }, error: null })
  })

  it('returns 400 when messageId is missing', async () => {
    const res = await POST(makeRequest({ value: 1 }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when messageId is not a valid UUID', async () => {
    const res = await POST(makeRequest({ messageId: 'not-a-uuid', value: 1 }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when value is not 1 or -1', async () => {
    const res = await POST(makeRequest({
      messageId: VALID_MSG_UUID,
      value: 0,
    }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('returns 400 when value is a string', async () => {
    const res = await POST(makeRequest({
      messageId: VALID_MSG_UUID,
      value: 'thumbs_up',
    }))
    expect(res.status).toBe(400)
    expect(mockGetUser).not.toHaveBeenCalled()
  })

  it('proceeds past validation with valid input (reaches auth check)', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null }, error: null })
    const res = await POST(makeRequest({
      messageId: VALID_MSG_UUID,
      value: 1,
    }))
    expect(res.status).toBe(401)
    expect(mockGetUser).toHaveBeenCalledOnce()
  })
})
