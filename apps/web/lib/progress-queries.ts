import type { SupabaseClient } from '@supabase/supabase-js'

const THIRTY_DAYS_AGO = () => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
const TWENTY_ONE_DAYS_AGO = () => new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString()

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

export async function fetchEngagement(client: SupabaseClient, userId: string): Promise<EngagementStats> {
  const cutoff = TWENTY_ONE_DAYS_AGO()

  const { data: sessions } = await client
    .from('chat_sessions')
    .select('id')
    .eq('user_id', userId)
    .gte('created_at', cutoff)

  const sessionIds = (sessions ?? []).map(s => s.id as string)
  if (sessionIds.length === 0) return { sessionCount: 0, skillsUsedCount: 0 }

  const { data: skillMsgs } = await client
    .from('messages')
    .select('skill_id')
    .in('session_id', sessionIds)
    .gte('created_at', cutoff)
    .not('skill_id', 'is', null)

  const distinctSkills = new Set((skillMsgs ?? []).map(m => m.skill_id as string))
  return { sessionCount: sessionIds.length, skillsUsedCount: distinctSkills.size }
}

export async function fetchMoodTrajectory(client: SupabaseClient, userId: string): Promise<MoodPoint[]> {
  const { data: sessions } = await client
    .from('chat_sessions')
    .select('id, name')
    .eq('user_id', userId)

  const sessionMap = new Map<string, string | null>(
    (sessions ?? []).map(s => [s.id as string, s.name as string | null])
  )
  const sessionIds = Array.from(sessionMap.keys())
  if (sessionIds.length === 0) return []

  const { data: rows } = await client
    .from('messages')
    .select('created_at, emotional_intensity, session_id')
    .in('session_id', sessionIds)
    .eq('role', 'ai')
    .gte('created_at', TWENTY_ONE_DAYS_AGO())
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
        sessionName: sessionMap.get(lastSessionId) ?? null,
      }
    })
}

export async function fetchRecentTopics(client: SupabaseClient, userId: string): Promise<TopicStat[]> {
  const { data: sessions } = await client
    .from('chat_sessions')
    .select('id')
    .eq('user_id', userId)

  const sessionIds = (sessions ?? []).map(s => s.id as string)
  if (sessionIds.length === 0) return []

  const { data: rows } = await client
    .from('messages')
    .select('intent_classification')
    .in('session_id', sessionIds)
    .gte('created_at', THIRTY_DAYS_AGO())
    .not('intent_classification', 'is', null)

  const EXCLUDED = new Set(['scope_refusal', 'jailbreak', 'exit_skill', 'unknown'])
  const counts: Record<string, number> = {}
  for (const row of rows ?? []) {
    const topic = row.intent_classification as string
    if (EXCLUDED.has(topic)) continue
    counts[topic] = (counts[topic] ?? 0) + 1
  }

  return Object.entries(counts)
    .map(([topic, count]) => ({ topic, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6)
}

export async function fetchSkillsUsed(client: SupabaseClient, userId: string): Promise<SkillStat[]> {
  const { data: sessions } = await client
    .from('chat_sessions')
    .select('id')
    .eq('user_id', userId)

  const sessionIds = (sessions ?? []).map(s => s.id as string)
  if (sessionIds.length === 0) return []

  const { data: rows } = await client
    .from('messages')
    .select('skill_id')
    .in('session_id', sessionIds)
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
  userId: string
): Promise<{ flag: string; copy: string }[]> {
  const { data: sessions } = await client
    .from('chat_sessions')
    .select('id')
    .eq('user_id', userId)

  const sessionIds = (sessions ?? []).map(s => s.id as string)
  if (sessionIds.length === 0) return []

  const { data: rows } = await client
    .from('messages')
    .select('clinical_flags')
    .in('session_id', sessionIds)
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

export interface ProgressData {
  engagement: EngagementStats
  moodTrajectory: MoodPoint[]
  topics: TopicStat[]
  skills: SkillStat[]
  clinicalFlags: { flag: string; copy: string }[]
}

export async function fetchAllProgressData(
  client: SupabaseClient,
  userId: string
): Promise<ProgressData> {
  const [engagement, moodTrajectory, topics, skills, clinicalFlags] = await Promise.all([
    fetchEngagement(client, userId),
    fetchMoodTrajectory(client, userId),
    fetchRecentTopics(client, userId),
    fetchSkillsUsed(client, userId),
    fetchClinicalFlagsForUser(client, userId),
  ])
  return { engagement, moodTrajectory, topics, skills, clinicalFlags }
}
