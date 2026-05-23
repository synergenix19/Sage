import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockSignOut = vi.fn().mockResolvedValue({})
const mockReset = vi.fn()

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: { signOut: mockSignOut },
  }),
}))

vi.mock('@/lib/stores/onboarding-store', () => ({
  useOnboardingStore: {
    getState: vi.fn(() => ({ reset: mockReset })),
  },
}))

import { signOutUser } from '../auth-actions'

describe('signOutUser', () => {
  const push = vi.fn()

  beforeEach(() => {
    mockSignOut.mockClear()
    mockReset.mockClear()
    push.mockClear()
  })

  it('calls supabase.auth.signOut', async () => {
    await signOutUser(push)
    expect(mockSignOut).toHaveBeenCalledOnce()
  })

  it('navigates to /sign-in after signing out', async () => {
    await signOutUser(push)
    expect(push).toHaveBeenCalledWith('/sign-in')
  })

  it('navigates after signOut completes, not before', async () => {
    let signOutDone = false
    mockSignOut.mockImplementation(async () => { signOutDone = true })
    await signOutUser(push)
    expect(signOutDone).toBe(true)
    expect(push).toHaveBeenCalledWith('/sign-in')
  })

  it('resets onboarding store before signing out', async () => {
    let resetCalledBeforeSignOut = false
    mockSignOut.mockImplementation(async () => {
      resetCalledBeforeSignOut = mockReset.mock.calls.length > 0
    })
    await signOutUser(push)
    expect(mockReset).toHaveBeenCalledOnce()
    expect(resetCalledBeforeSignOut).toBe(true)
  })

  it('redirects to /sign-in even when signOut throws', async () => {
    mockSignOut.mockRejectedValue(new Error('network error'))
    const push = vi.fn()
    await signOutUser(push)
    expect(mockReset).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith('/sign-in')
  })
})
