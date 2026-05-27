import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import type { AuditRow } from '@/lib/types/session-audit'

const mockRow = (overrides: Partial<AuditRow> = {}): AuditRow => ({
  id: '1',
  inserted_at: '2026-05-27T10:00:00Z',
  session_id: 'sess-001',
  turn_number: 1,
  node_path: ['safety_check', 'intent_route', 'freeflow_respond', 'output_gate'],
  primary_intent: 'general_chat',
  secondary_intent: null,
  intent_confidence: 0.9,
  active_skill_id: null,
  active_step_id: null,
  skill_match_method: null,
  knowledge_source: null,
  knowledge_passage_ids: [],
  knowledge_abstain: null,
  crisis_state: 'none',
  crisis_flags: [],
  clinical_flags: [],
  engagement: 7,
  emotional_intensity: 4,
  model_version: 'claude-sonnet-4-6',
  latency_ms: null,
  user_id: null,
  ...overrides,
})

let realtimeCallback: ((payload: { new: AuditRow }) => void) | null = null

function makeMockSupabase(initialRows: AuditRow[] = []) {
  return {
    from: () => ({
      select: () => ({
        eq: () => ({
          order: () => ({
            limit: () => Promise.resolve({ data: initialRows, error: null }),
            then: (f: Function) => Promise.resolve({ data: initialRows, error: null }).then(f),
          }),
          then: (f: Function) => Promise.resolve({ data: initialRows, error: null }).then(f),
        }),
        order: () => ({
          limit: () => Promise.resolve({ data: initialRows, error: null }),
        }),
      }),
    }),
    channel: () => ({
      on: (_event: string, _filter: object, cb: (payload: { new: AuditRow }) => void) => {
        realtimeCallback = cb
        return {
          subscribe: (statusCb: (s: string) => void) => {
            statusCb('SUBSCRIBED')
            return {}
          },
        }
      },
    }),
    removeChannel: vi.fn(),
  }
}

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(),
}))

describe('useSessionAudit — follow-latest mode', () => {
  it('loads initial rows from most recent session', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit(null))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))
    expect(result.current.activeSessionId).toBe('sess-001')
    expect(result.current.status).toBe('live')
  })

  it('appends new rows from the same session', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit(null))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))

    act(() => {
      realtimeCallback?.({ new: mockRow({ turn_number: 2, id: '2' }) })
    })

    expect(result.current.rows).toHaveLength(2)
  })

  it('resets rows when a new session_id arrives', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit(null))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))

    act(() => {
      realtimeCallback?.({ new: mockRow({ session_id: 'sess-002', turn_number: 1, id: '3' }) })
    })

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.rows[0].session_id).toBe('sess-002')
    expect(result.current.activeSessionId).toBe('sess-002')
  })
})

describe('useSessionAudit — locked mode', () => {
  it('rejects rows from other sessions', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    vi.mocked(createClient).mockReturnValue(makeMockSupabase([mockRow()]) as never)

    const { useSessionAudit } = await import('../use-session-audit')
    const { result } = renderHook(() => useSessionAudit('sess-001'))

    await waitFor(() => expect(result.current.rows).toHaveLength(1))

    act(() => {
      realtimeCallback?.({ new: mockRow({ session_id: 'sess-other', turn_number: 2, id: '9' }) })
    })

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.status).toBe('locked')
  })
})
