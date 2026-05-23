import { describe, it, expect, vi, beforeEach } from 'vitest'

const { mockGetUser, mockSelect, mockEq, mockSingle, mockFrom, mockRedirect } = vi.hoisted(() => {
  const mockGetUser = vi.fn()
  const mockSelect = vi.fn()
  const mockEq = vi.fn()
  const mockSingle = vi.fn()

  // Chainable Supabase builder mock
  const mockFrom = vi.fn(() => ({
    select: mockSelect.mockReturnThis(),
    eq: mockEq.mockReturnThis(),
    single: mockSingle,
  }))

  // redirect throws to short-circuit component rendering — matches Next.js behaviour in tests
  const mockRedirect = vi.fn((url: string) => { throw new Error(`REDIRECT:${url}`) })

  return { mockGetUser, mockSelect, mockEq, mockSingle, mockFrom, mockRedirect }
})

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    auth: { getUser: mockGetUser },
    from: mockFrom,
  }),
}))

vi.mock('next/navigation', () => ({ redirect: mockRedirect }))

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: vi.fn(() => ({})),
}))

vi.mock('@/lib/admin-queries', () => ({
  fetchAllAdminData: vi.fn().mockResolvedValue({ users: [], sessions: [] }),
}))

import AdminPage from '../page'

describe('AdminPage — auth guard', () => {
  beforeEach(() => {
    mockGetUser.mockClear()
    mockFrom.mockClear()
    mockSelect.mockClear()
    mockEq.mockClear()
    mockSingle.mockClear()
    mockRedirect.mockClear()
  })

  it('redirects to /sign-in when user is not authenticated', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null }, error: null })
    await expect(AdminPage()).rejects.toThrow('REDIRECT:/sign-in')
    expect(mockRedirect).toHaveBeenCalledWith('/sign-in')
  })

  it('redirects to /chat when user is authenticated but not admin', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } }, error: null })
    mockSingle.mockResolvedValue({ data: { is_admin: false }, error: null })
    await expect(AdminPage()).rejects.toThrow('REDIRECT:/chat')
    expect(mockRedirect).toHaveBeenCalledWith('/chat')
  })

  it('redirects to /chat when user_profiles row does not exist', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } }, error: null })
    mockSingle.mockResolvedValue({ data: null, error: null })
    await expect(AdminPage()).rejects.toThrow('REDIRECT:/chat')
  })

  it('renders dashboard for authenticated admin', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'admin-1' } }, error: null })
    mockSingle.mockResolvedValue({ data: { is_admin: true }, error: null })
    const result = await AdminPage()
    expect(result).toBeTruthy()
    expect(mockRedirect).not.toHaveBeenCalled()
  })

  it('queries user_profiles with the authenticated user id', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'specific-user-id' } }, error: null })
    mockSingle.mockResolvedValue({ data: { is_admin: true }, error: null })
    await AdminPage()
    expect(mockFrom).toHaveBeenCalledWith('user_profiles')
    expect(mockEq).toHaveBeenCalledWith('id', 'specific-user-id')
  })
})
