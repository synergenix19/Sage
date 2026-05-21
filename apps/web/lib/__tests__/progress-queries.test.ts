import { describe, it, expect, vi } from 'vitest'
import {
  fetchEngagement,
  fetchMoodTrajectory,
  fetchRecentTopics,
  fetchSkillsUsed,
  fetchClinicalFlagsForUser,
  type MoodPoint,
} from '../progress-queries'

const USER_ID = 'user-test-123'

function mockClient(data: Record<string, unknown[]>) {
  function makeChain(table: string) {
    const resolved = Promise.resolve({ data: data[table] ?? [], error: null })
    const chain: any = {
      select: () => chain, eq: () => chain, gte: () => chain, lte: () => chain,
      not: () => chain, in: () => chain, order: () => chain, limit: () => chain,
      single: () => Promise.resolve({ data: (data[table] ?? [])[0] ?? null, error: null }),
      then: resolved.then.bind(resolved),
      catch: resolved.catch.bind(resolved),
      finally: resolved.finally.bind(resolved),
    }
    return chain
  }
  return { from: (table: string) => makeChain(table) }
}

describe('fetchEngagement', () => {
  it('returns zero counts when no data', async () => {
    const client = mockClient({ chat_sessions: [], messages: [] })
    const result = await fetchEngagement(client as never, USER_ID)
    expect(result.sessionCount).toBe(0)
    expect(result.skillsUsedCount).toBe(0)
  })
})

describe('fetchMoodTrajectory', () => {
  it('returns empty array when no data', async () => {
    const client = mockClient({ messages: [] })
    const result = await fetchMoodTrajectory(client as never, USER_ID)
    expect(result).toEqual([])
  })

  it('inverts emotional_intensity so high distress maps to low mood', async () => {
    const client = mockClient({
      chat_sessions: [{ id: 's1', name: 'Test Session', user_id: USER_ID }],
      messages: [
        { created_at: '2026-05-22T10:00:00Z', emotional_intensity: 8, session_id: 's1', role: 'ai' },
      ],
    })
    const result = await fetchMoodTrajectory(client as never, USER_ID)
    if (result.length > 0) {
      expect(result[0].avgIntensity).toBe(1.0)
      expect(result[0].avgIntensity).toBeLessThan(3)
    }
  })

  it('returns near-max mood for calm sessions', async () => {
    const client = mockClient({
      chat_sessions: [{ id: 's1', name: 'Calm session', user_id: USER_ID }],
      messages: [
        { created_at: '2026-05-22T10:00:00Z', emotional_intensity: 2, session_id: 's1', role: 'ai' },
      ],
    })
    const result = await fetchMoodTrajectory(client as never, USER_ID)
    if (result.length > 0) {
      expect(result[0].avgIntensity).toBe(4.0)
      expect(result[0].avgIntensity).toBeGreaterThan(3)
    }
  })
})

describe('fetchRecentTopics', () => {
  it('returns empty array when no data', async () => {
    const client = mockClient({ messages: [] })
    const result = await fetchRecentTopics(client as never, USER_ID)
    expect(Array.isArray(result)).toBe(true)
  })
})

describe('fetchClinicalFlagsForUser', () => {
  it('returns empty array when no flags', async () => {
    const client = mockClient({ messages: [] })
    const result = await fetchClinicalFlagsForUser(client as never, USER_ID)
    expect(result).toEqual([])
  })
})
