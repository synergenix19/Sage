import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useChatSessions } from '../use-chat-sessions'

// --- Mocks ---

const mockGetUser = vi.fn()
const mockLimit = vi.fn()
const mockOrder = vi.fn(() => ({ limit: mockLimit }))
const mockEq = vi.fn(() => ({ order: mockOrder }))
const mockSelect = vi.fn(() => ({ eq: mockEq }))
const mockFrom = vi.fn(() => ({ select: mockSelect }))

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: { getUser: mockGetUser },
    from: mockFrom,
  }),
}))

const SESSION_ROW = { id: 'sess-1', name: 'Feeling stressed', updated_at: '2026-05-23T10:00:00Z' }

beforeEach(() => {
  vi.clearAllMocks()
  mockGetUser.mockResolvedValue({ data: { user: { id: 'user-abc' } } })
  mockLimit.mockResolvedValue({ data: [SESSION_ROW], error: null })
})

// --- Tests ---

describe('useChatSessions — success path', () => {
  it('starts with loading=true and empty sessions', () => {
    mockLimit.mockReturnValue(new Promise(() => {})) // never resolves
    const { result } = renderHook(() => useChatSessions())
    expect(result.current.loading).toBe(true)
    expect(result.current.sessions).toEqual([])
  })

  it('returns sessions with title mapped from DB name column', async () => {
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.sessions).toEqual([
      { id: 'sess-1', title: 'Feeling stressed', updated_at: '2026-05-23T10:00:00Z' },
    ])
    expect(result.current.error).toBeNull()
  })

  it('queries chat_sessions ordered by updated_at desc, limit 20', async () => {
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockFrom).toHaveBeenCalledWith('chat_sessions')
    expect(mockSelect).toHaveBeenCalledWith('id, name, updated_at')
    expect(mockEq).toHaveBeenCalledWith('user_id', 'user-abc')
    expect(mockOrder).toHaveBeenCalledWith('updated_at', { ascending: false })
    expect(mockLimit).toHaveBeenCalledWith(20)
  })

  it('handles null name as null title', async () => {
    mockLimit.mockResolvedValueOnce({
      data: [{ id: 's2', name: null, updated_at: '2026-05-23T09:00:00Z' }],
      error: null,
    })
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.sessions[0].title).toBeNull()
  })
})

describe('useChatSessions — error path', () => {
  it('sets error message when Supabase query fails', async () => {
    mockLimit.mockResolvedValueOnce({ data: null, error: { message: 'Connection refused' } })
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.error).toBe('Connection refused'))
    expect(result.current.sessions).toEqual([])
    expect(result.current.loading).toBe(false)
  })
})

describe('useChatSessions — no authenticated user', () => {
  it('sets loading=false and leaves sessions empty when no user', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } })
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.sessions).toEqual([])
    expect(mockFrom).not.toHaveBeenCalled()
  })
})

describe('useChatSessions — refresh()', () => {
  it('re-fetches sessions when refresh() is called', async () => {
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(mockLimit).toHaveBeenCalledTimes(1)

    const updatedRow = { id: 'sess-2', name: 'New chat', updated_at: '2026-05-23T11:00:00Z' }
    mockLimit.mockResolvedValueOnce({ data: [updatedRow, SESSION_ROW], error: null })

    act(() => { result.current.refresh() })

    await waitFor(() => expect(result.current.sessions).toHaveLength(2))
    expect(result.current.sessions[0].title).toBe('New chat')
    expect(mockLimit).toHaveBeenCalledTimes(2)
  })

  it('clears error and re-fetches on refresh() after a failure', async () => {
    mockLimit.mockResolvedValueOnce({ data: null, error: { message: 'DB error' } })
    const { result } = renderHook(() => useChatSessions())
    await waitFor(() => expect(result.current.error).toBe('DB error'))

    mockLimit.mockResolvedValueOnce({ data: [SESSION_ROW], error: null })
    act(() => { result.current.refresh() })

    await waitFor(() => {
      expect(result.current.error).toBeNull()
      expect(result.current.sessions).toHaveLength(1)
    })
  })
})
