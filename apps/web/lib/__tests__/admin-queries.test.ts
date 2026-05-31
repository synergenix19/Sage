import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchSystemPerformance,
  fetchClinicalSafety,
  fetchResponseQuality,
  fetchConversationIntelligence,
  fetchOverviewMetrics,
  fetchAllAdminData,
  type AdminData,
} from '../admin-queries'

function mockSupabase(rows: Record<string, unknown[]>) {
  function makeChain(table: string) {
    const resolved = Promise.resolve({ data: rows[table] ?? [], error: null })
    const chain: any = {
      select: () => chain,
      eq: () => chain,
      gte: () => chain,
      lte: () => chain,
      not: () => chain,
      in: () => chain,
      order: () => chain,
      limit: () => chain,
      single: () => Promise.resolve({ data: (rows[table] ?? [])[0] ?? null, error: null }),
      then: resolved.then.bind(resolved),
      catch: resolved.catch.bind(resolved),
      finally: resolved.finally.bind(resolved),
    }
    return chain
  }
  return { from: (table: string) => makeChain(table) }
}

describe('fetchOverviewMetrics', () => {
  it('returns zero values when tables are empty', async () => {
    const admin = mockSupabase({
      user_profiles: [],
      messages: [],
      chat_sessions: [],
    })
    const result = await fetchOverviewMetrics(admin as never)
    expect(result.totalUsers).toBe(0)
    expect(result.crisisThisWeek).toBe(0)
  })
})

describe('fetchSystemPerformance', () => {
  it('returns empty arrays when no data', async () => {
    const admin = mockSupabase({ messages: [] })
    const result = await fetchSystemPerformance(admin as never)
    expect(result.latencyByDay).toEqual([])
    expect(result.intentDistribution).toEqual([])
  })

  it('aggregates latency by day', async () => {
    const admin = mockSupabase({
      messages: [
        { created_at: '2026-05-22T10:00:00Z', latency_ms: 800, intent_classification: 'general_chat' },
        { created_at: '2026-05-22T11:00:00Z', latency_ms: 1200, intent_classification: 'new_skill' },
      ],
    })
    const result = await fetchSystemPerformance(admin as never)
    expect(result.latencyByDay).toHaveLength(1)
    expect(result.latencyByDay[0].avgMs).toBe(1000)
    expect(result.intentDistribution.find(i => i.intent === 'general_chat')?.count).toBe(1)
  })
})

describe('fetchClinicalSafety', () => {
  it('counts crisis messages', async () => {
    const admin = mockSupabase({
      messages: [
        { role: 'crisis', created_at: '2026-05-22T10:00:00Z', clinical_flags: [] },
        { role: 'ai', created_at: '2026-05-22T10:00:00Z', clinical_flags: ['substance_use'] },
      ],
    })
    const result = await fetchClinicalSafety(admin as never)
    expect(typeof result.crisisThisWeek).toBe('number')
    expect(Array.isArray(result.flagDistribution)).toBe(true)
  })
})

describe('fetchResponseQuality', () => {
  it('returns zero thumbs when no feedback', async () => {
    const admin = mockSupabase({ message_feedback: [], messages: [] })
    const result = await fetchResponseQuality(admin as never)
    expect(result.thumbsUp).toBe(0)
    expect(result.thumbsDown).toBe(0)
    expect(Array.isArray(result.gatePathDistribution)).toBe(true)
  })
})

// Data-layer gate proof: fetchAllAdminData must never issue a clinical_flags query
// when hasClinicalAccess = false (operations_admin). This is the acceptance criterion
// for the admin crisis-banner boundary fix — the server must not touch clinical-flag
// columns at all for ops, regardless of what the UI renders.
describe('fetchAllAdminData — clinical-access gate', () => {
  function makeTrackingClient(selectLog: string[]) {
    function makeChain(table: string): any {
      const resolved = Promise.resolve({ data: [], error: null })
      const c: any = {
        select: (cols: string) => { selectLog.push(`${table}:${cols}`); return c },
        eq: () => c,
        gte: () => c,
        lte: () => c,
        not: () => c,
        in: () => c,
        order: () => c,
        limit: () => c,
        single: () => Promise.resolve({ data: null, error: null }),
        maybeSingle: () => Promise.resolve({ data: null, error: null }),
        then: resolved.then.bind(resolved),
        catch: resolved.catch.bind(resolved),
        finally: resolved.finally.bind(resolved),
      }
      return c
    }
    return { from: (table: string) => makeChain(table) }
  }

  it('ops (hasClinicalAccess=false): no clinical_flags column is ever queried', async () => {
    const log: string[] = []
    await fetchAllAdminData(makeTrackingClient(log) as never, false)
    const clinicalFlagCalls = log.filter(e => e.includes('clinical_flags'))
    expect(clinicalFlagCalls).toHaveLength(0)
  })

  it('reviewer (hasClinicalAccess=true): clinical_flags is queried', async () => {
    const log: string[] = []
    await fetchAllAdminData(makeTrackingClient(log) as never, true)
    const clinicalFlagCalls = log.filter(e => e.includes('clinical_flags'))
    expect(clinicalFlagCalls.length).toBeGreaterThan(0)
  })

  it('ops result has clinicalSafety null; reviewer result has non-null', async () => {
    const opsResult = await fetchAllAdminData(makeTrackingClient([]) as never, false)
    const reviewerResult = await fetchAllAdminData(makeTrackingClient([]) as never, true)
    expect(opsResult.clinicalSafety).toBeNull()
    expect(reviewerResult.clinicalSafety).not.toBeNull()
  })
})
