import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockSignOut = vi.fn().mockResolvedValue({})

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: { signOut: mockSignOut },
  }),
}))

import { signOutUser } from '../auth-actions'

describe('signOutUser', () => {
  const push = vi.fn()

  beforeEach(() => {
    mockSignOut.mockClear()
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
})
