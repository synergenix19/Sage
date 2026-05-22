import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

const { mockExchangeCode, mockCookieStore } = vi.hoisted(() => {
  const mockExchangeCode = vi.fn()
  const mockCookieStore = { getAll: vi.fn(() => []), set: vi.fn() }
  return { mockExchangeCode, mockCookieStore }
})

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
    mockExchangeCode.mockClear()
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
    expect(res.headers.get('location')).toContain('error=callback-failed')
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
