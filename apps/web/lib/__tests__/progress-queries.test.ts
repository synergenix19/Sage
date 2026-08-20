import { describe, it, expect } from 'vitest'
import {
  fetchEngagement,
  fetchMoodTrajectory,
  fetchRecentTopics,
  fetchSkillsUsed,
  fetchClinicalFlagsForUser,
  fetchAllProgressData,
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

// ── Unit tests: each function takes its real (pre-fetched) inputs directly —────
// no chat_sessions mocking needed, since the shipped signature no longer self-fetches
// sessions. This is the shipped contract fetchAllProgressData actually calls.

describe('fetchEngagement', () => {
  it('short-circuits on an empty session list without querying messages', async () => {
    const client = mockClient({ messages: [{ skill_id: 'should-not-be-counted' }] })
    const result = await fetchEngagement(client as never, [], '2026-01-01T00:00:00Z')
    expect(result.sessionCount).toBe(0)
    expect(result.skillsUsedCount).toBe(0)
  })

  it('counts sessions given and distinct skills used', async () => {
    const client = mockClient({
      messages: [
        { skill_id: 'box_breathing' },
        { skill_id: 'box_breathing' },
        { skill_id: 'grounding' },
      ],
    })
    const result = await fetchEngagement(client as never, ['s1', 's2'], '2026-01-01T00:00:00Z')
    expect(result.sessionCount).toBe(2)
    expect(result.skillsUsedCount).toBe(2)
  })
})

describe('fetchMoodTrajectory', () => {
  it('returns empty array on an empty session list', async () => {
    const client = mockClient({ messages: [{ emotional_intensity: 8 }] })
    const result = await fetchMoodTrajectory(client as never, [], new Map())
    expect(result).toEqual([])
  })

  it('inverts emotional_intensity so high distress maps to low mood', async () => {
    const client = mockClient({
      messages: [
        { created_at: '2026-05-22T10:00:00Z', emotional_intensity: 8, session_id: 's1', role: 'ai' },
      ],
    })
    const sessionNameMap = new Map([['s1', 'Test Session']])
    const result = await fetchMoodTrajectory(client as never, ['s1'], sessionNameMap)
    expect(result).toHaveLength(1)
    expect(result[0].avgIntensity).toBe(1.0)
    expect(result[0].avgIntensity).toBeLessThan(3)
    expect(result[0].sessionName).toBe('Test Session')
  })

  it('returns near-max mood for calm sessions', async () => {
    const client = mockClient({
      messages: [
        { created_at: '2026-05-22T10:00:00Z', emotional_intensity: 2, session_id: 's1', role: 'ai' },
      ],
    })
    const sessionNameMap = new Map([['s1', 'Calm session']])
    const result = await fetchMoodTrajectory(client as never, ['s1'], sessionNameMap)
    expect(result).toHaveLength(1)
    expect(result[0].avgIntensity).toBe(4.0)
    expect(result[0].avgIntensity).toBeGreaterThan(3)
  })

  it('resolves sessionName from the provided map even for sessions absent elsewhere', async () => {
    // Proves the function trusts its sessionNameMap argument rather than re-deriving names —
    // this is the behavior fetchAllProgressData relies on when it shares one map built from
    // ALL sessions (not just the "recent" subset fetchEngagement sees).
    const client = mockClient({
      messages: [
        { created_at: '2026-01-01T10:00:00Z', emotional_intensity: 4, session_id: 'old-session', role: 'ai' },
      ],
    })
    const sessionNameMap = new Map([['old-session', 'An Old Session']])
    const result = await fetchMoodTrajectory(client as never, ['old-session'], sessionNameMap)
    expect(result[0].sessionName).toBe('An Old Session')
  })
})

describe('fetchRecentTopics', () => {
  it('returns empty array on an empty session list', async () => {
    const client = mockClient({ messages: [{ intent_classification: 'general_chat' }] })
    const result = await fetchRecentTopics(client as never, [])
    expect(result).toEqual([])
  })

  it('counts topics and excludes routing-only classifications', async () => {
    const client = mockClient({
      messages: [
        { intent_classification: 'new_skill' },
        { intent_classification: 'new_skill' },
        { intent_classification: 'scope_refusal' },
        { intent_classification: 'unknown' },
      ],
    })
    const result = await fetchRecentTopics(client as never, ['s1'])
    expect(result).toEqual([{ topic: 'new_skill', count: 2 }])
  })
})

describe('fetchSkillsUsed', () => {
  it('returns empty array on an empty session list', async () => {
    const client = mockClient({ messages: [{ skill_id: 'grounding' }] })
    const result = await fetchSkillsUsed(client as never, [])
    expect(result).toEqual([])
  })

  it('returns distinct skill ids in first-seen order', async () => {
    const client = mockClient({
      messages: [
        { skill_id: 'grounding' },
        { skill_id: 'box_breathing' },
        { skill_id: 'grounding' },
      ],
    })
    const result = await fetchSkillsUsed(client as never, ['s1'])
    expect(result).toEqual([{ skillId: 'grounding' }, { skillId: 'box_breathing' }])
  })
})

describe('fetchClinicalFlagsForUser', () => {
  it('returns empty array on an empty session list', async () => {
    const client = mockClient({ messages: [{ clinical_flags: ['substance_use'] }] })
    const result = await fetchClinicalFlagsForUser(client as never, [])
    expect(result).toEqual([])
  })

  it('drops flags with no configured copy and de-duplicates known ones', async () => {
    const client = mockClient({
      messages: [
        { clinical_flags: ['substance_use', 'not_a_real_flag'] },
        { clinical_flags: ['substance_use'] },
      ],
    })
    const result = await fetchClinicalFlagsForUser(client as never, ['s1'])
    expect(result.map(f => f.flag)).toEqual(['substance_use'])
    expect(result[0].copy.length).toBeGreaterThan(0)
  })
})

// ── Integration: fetchAllProgressData ───────────────────────────────────────
// The app only ever calls this composed entry point (apps/web/app/(app)/progress/page.tsx).
// Covers the wiring the unit tests above cannot: the single chat_sessions fetch, the
// recent/all id split by the 21-day cutoff, and the shared sessionNameMap — fed into the
// five query functions above.

describe('fetchAllProgressData', () => {
  it('wires sessions → recent/all ids → sessionNameMap into the five queries', async () => {
    const now = Date.now()
    const recentCreatedAt = new Date(now - 5 * 24 * 60 * 60 * 1000).toISOString()
    const oldCreatedAt = new Date(now - 40 * 24 * 60 * 60 * 1000).toISOString()

    const client = mockClient({
      chat_sessions: [
        { id: 's-recent', name: 'Recent Session', user_id: USER_ID, created_at: recentCreatedAt },
        { id: 's-old', name: 'Old Session', user_id: USER_ID, created_at: oldCreatedAt },
      ],
      messages: [
        {
          session_id: 's-recent',
          created_at: recentCreatedAt,
          role: 'ai',
          emotional_intensity: 4,
          skill_id: 'box_breathing',
          intent_classification: 'new_skill',
          clinical_flags: ['substance_use', 'not_a_real_flag'],
        },
        {
          session_id: 's-old',
          created_at: oldCreatedAt,
          role: 'ai',
          emotional_intensity: 8,
          skill_id: 'grounding',
          intent_classification: 'general_chat',
          clinical_flags: ['trauma_indicator'],
        },
      ],
    })

    const result = await fetchAllProgressData(client as never, USER_ID)

    // engagement is built from the RECENT-only id split (one session, not two) —
    // proves fetchAllProgressData filters by the 21-day cutoff before calling fetchEngagement.
    expect(result.engagement.sessionCount).toBe(1)

    // moodTrajectory is built from ALL sessions + the shared name map, so it can still
    // resolve a name for the OLD session that engagement excluded — proves the map is
    // built from allSessions, not the recent-only subset.
    expect(result.moodTrajectory).toHaveLength(2)
    const oldPoint = result.moodTrajectory.find(p => p.sessionName === 'Old Session')
    const recentPoint = result.moodTrajectory.find(p => p.sessionName === 'Recent Session')
    expect(oldPoint?.avgIntensity).toBe(1.0)
    expect(recentPoint?.avgIntensity).toBe(3.0)

    // topics/skills draw from all sessions' messages
    expect(result.topics.map(t => t.topic).sort()).toEqual(['general_chat', 'new_skill'])
    expect(result.skills.map(s => s.skillId).sort()).toEqual(['box_breathing', 'grounding'])

    // clinicalFlags de-duplicates against the configured-copy allowlist across all sessions
    expect(result.clinicalFlags.map(f => f.flag).sort()).toEqual(['substance_use', 'trauma_indicator'])
    expect(result.clinicalFlags.every(f => f.copy.length > 0)).toBe(true)
  })

  it('returns empty/zero shapes with no sessions', async () => {
    const client = mockClient({ chat_sessions: [], messages: [] })
    const result = await fetchAllProgressData(client as never, USER_ID)
    expect(result).toEqual({
      engagement: { sessionCount: 0, skillsUsedCount: 0 },
      moodTrajectory: [],
      topics: [],
      skills: [],
      clinicalFlags: [],
    })
  })
})
