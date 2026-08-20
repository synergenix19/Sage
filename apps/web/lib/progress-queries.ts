import type { SupabaseClient } from '@supabase/supabase-js'
import { countAndRank, daysAgo } from '@/lib/aggregation'

export interface EngagementStats {
  sessionCount: number
  skillsUsedCount: number
}

export interface MoodPoint {
  day: string
  avgIntensity: number
  sessionName: string | null
}

export interface TopicStat {
  topic: string
  count: number
}

export interface SkillStat {
  skillId: string
}

export const INTENT_TOPIC_LABELS: Record<string, string> = {
  new_skill:            'Exploring techniques',
  general_chat:         'Open conversation',
  info_request:         'Learning',
  skill_continuation:   'Continuing practice',
  emotional:            'Emotional support',
}

const CLINICAL_FLAG_COPY: Record<string, string> = {
  substance_use:       'You have been exploring topics around substances. Sage is here for those conversations.',
  trauma_indicator:    'You have opened up about difficult experiences. That takes real courage.',
  eating_concern:      'You have shared some thoughts about eating and your body. Sage is here to listen.',
  medication_mention:  'You have mentioned medication. For specific medical questions, a healthcare professional is best placed to help.',
}

export interface ProgressData {
  engagement: EngagementStats
  moodTrajectory: MoodPoint[]
  topics: TopicStat[]
  skills: SkillStat[]
  clinicalFlags: { flag: string; copy: string }[]
}

// ── Query building blocks for fetchAllProgressData ──────────────────────────────────
// Each accepts pre-fetched session data (sessionIds / cutoff / name map) rather than a bare
// userId, so fetchAllProgressData can do a single chat_sessions round-trip and share the
// result across all five instead of each query re-fetching sessions independently.

export async function fetchEngagement(
  client: SupabaseClient,
  recentSessionIds: string[],
  cutoff: string,
): Promise<EngagementStats> {
  if (recentSessionIds.length === 0) return { sessionCount: 0, skillsUsedCount: 0 }
  const { data: skillMsgs } = await client
    .from('messages')
    .select('skill_id')
    .in('session_id', recentSessionIds)
    .gte('created_at', cutoff)
    .not('skill_id', 'is', null)
  const distinctSkills = new Set((skillMsgs ?? []).map(m => m.skill_id as string))
  return { sessionCount: recentSessionIds.length, skillsUsedCount: distinctSkills.size }
}

export async function fetchMoodTrajectory(
  client: SupabaseClient,
  allSessionIds: string[],
  sessionNameMap: Map<string, string | null>,
): Promise<MoodPoint[]> {
  if (allSessionIds.length === 0) return []
  const { data: rows } = await client
    .from('messages')
    .select('created_at, emotional_intensity, session_id')
    .in('session_id', allSessionIds)
    .eq('role', 'ai')
    .gte('created_at', daysAgo(21))
    .not('emotional_intensity', 'is', null)
    .order('created_at')
  const groups: Record<string, { intensities: number[]; lastSessionId: string }> = {}
  for (const row of rows ?? []) {
    const day = (row.created_at as string).slice(0, 10)
    if (!groups[day]) groups[day] = { intensities: [], lastSessionId: row.session_id as string }
    groups[day].intensities.push(row.emotional_intensity as number)
    groups[day].lastSessionId = row.session_id as string
  }
  return Object.entries(groups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, { intensities, lastSessionId }]) => {
      const avg = intensities.reduce((s, v) => s + v, 0) / intensities.length
      return {
        day,
        avgIntensity: Math.round((5 - avg / 2) * 10) / 10,
        sessionName: sessionNameMap.get(lastSessionId) ?? null,
      }
    })
}

export async function fetchRecentTopics(
  client: SupabaseClient,
  allSessionIds: string[],
): Promise<TopicStat[]> {
  if (allSessionIds.length === 0) return []
  const { data: rows } = await client
    .from('messages')
    .select('intent_classification')
    .in('session_id', allSessionIds)
    .gte('created_at', daysAgo(30))
    .not('intent_classification', 'is', null)
  const EXCLUDED = new Set(['scope_refusal', 'jailbreak', 'exit_skill', 'unknown'])
  const includedRows = (rows ?? []).filter(row => !EXCLUDED.has(row.intent_classification as string))
  return countAndRank(includedRows, row => row.intent_classification as string, (topic, count) => ({ topic, count }), 6)
}

export async function fetchSkillsUsed(
  client: SupabaseClient,
  allSessionIds: string[],
): Promise<SkillStat[]> {
  if (allSessionIds.length === 0) return []
  const { data: rows } = await client
    .from('messages')
    .select('skill_id')
    .in('session_id', allSessionIds)
    .not('skill_id', 'is', null)
  const seen = new Set<string>()
  const result: SkillStat[] = []
  for (const row of rows ?? []) {
    const id = row.skill_id as string
    if (!seen.has(id)) { seen.add(id); result.push({ skillId: id }) }
  }
  return result
}

export async function fetchClinicalFlagsForUser(
  client: SupabaseClient,
  allSessionIds: string[],
): Promise<{ flag: string; copy: string }[]> {
  if (allSessionIds.length === 0) return []
  const { data: rows } = await client
    .from('messages')
    .select('clinical_flags')
    .in('session_id', allSessionIds)
    .not('clinical_flags', 'is', null)
  const seen = new Set<string>()
  const result: { flag: string; copy: string }[] = []
  for (const row of rows ?? []) {
    for (const flag of (row.clinical_flags as string[]) ?? []) {
      if (!seen.has(flag) && CLINICAL_FLAG_COPY[flag]) {
        seen.add(flag)
        result.push({ flag, copy: CLINICAL_FLAG_COPY[flag] })
      }
    }
  }
  return result
}

export async function fetchAllProgressData(
  client: SupabaseClient,
  userId: string
): Promise<ProgressData> {
  const cutoff21 = daysAgo(21)

  // Single session fetch shared across all five queries — avoids 5 redundant DB round-trips.
  const { data: allSessions } = await client
    .from('chat_sessions')
    .select('id, name, created_at')
    .eq('user_id', userId)

  const sessions = allSessions ?? []
  const allIds = sessions.map(s => s.id as string)
  const recentIds = sessions
    .filter(s => (s.created_at as string) >= cutoff21)
    .map(s => s.id as string)
  const sessionNameMap = new Map<string, string | null>(
    sessions.map(s => [s.id as string, s.name as string | null])
  )

  const [engagement, moodTrajectory, topics, skills, clinicalFlags] = await Promise.all([
    fetchEngagement(client, recentIds, cutoff21),
    fetchMoodTrajectory(client, allIds, sessionNameMap),
    fetchRecentTopics(client, allIds),
    fetchSkillsUsed(client, allIds),
    fetchClinicalFlagsForUser(client, allIds),
  ])
  return { engagement, moodTrajectory, topics, skills, clinicalFlags }
}
