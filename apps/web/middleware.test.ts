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
