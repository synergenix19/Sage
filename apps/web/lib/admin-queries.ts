import type { SupabaseClient } from '@supabase/supabase-js'
import { countAndRank, daysAgo } from '@/lib/aggregation'

export interface OverviewMetrics {
  totalUsers: number
  activeToday: number
  avgEmotionalIntensity: number | null
  crisisThisWeek: number
}

export interface LatencyDay {
  day: string
  avgMs: number
  p95Ms: number
  turnCount: number
}

export interface IntentCount {
  intent: string
  count: number
}

export interface SystemPerformanceData {
  latencyByDay: LatencyDay[]
  intentDistribution: IntentCount[]
}

export interface FlagCount {
  flag: string
  count: number
}

export interface ClinicalSafetyData {
  crisisThisWeek: number
  escalationsThisWeek: number
  flagDistribution: FlagCount[]
}

export interface ResponseQualityData {
  thumbsUp: number
  thumbsDown: number
  totalFeedback: number
  gatePathDistribution: { gatePath: string; count: number }[]
}

export interface SkillCount {
  skillId: string
  count: number
}

export interface ConversationIntelligenceData {
  semanticMatchRate: number | null
  skillUsage: SkillCount[]
  avgTokenUsageInput: number | null
  avgTokenUsageOutput: number | null
}

export interface AdminData {
  overview: OverviewMetrics
  systemPerformance: SystemPerformanceData
  clinicalSafety: ClinicalSafetyData | null
  responseQuality: ResponseQualityData
  intelligence: ConversationIntelligenceData
}

function toDay(isoString: string): string {
  return isoString.slice(0, 10)
}

function groupByDay<T extends { created_at: string }>(
  rows: T[],
  fn: (group: T[]) => Omit<LatencyDay, 'day'>
): LatencyDay[] {
  const groups: Record<string, T[]> = {}
  for (const row of rows) {
    const day = toDay(row.created_at)
    if (!groups[day]) groups[day] = []
    groups[day].push(row)
  }
  return Object.entries(groups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, group]) => ({ day, ...fn(group) }))
}

export async function fetchOverviewMetrics(admin: SupabaseClient): Promise<OverviewMetrics> {
  // UAE (Dubai) is UTC+4 year-round. The UAE does not observe daylight saving time,
  // so this offset is fixed and does not need seasonal adjustment.
  // Shift back 4h so that slicing the ISO date gives the UAE calendar date, not UTC date.
  const uaeMidnight = new Date(Date.now() - 4 * 60 * 60 * 1000)
  const todayUtc = uaeMidnight.toISOString().slice(0, 10) + 'T00:00:00.000Z'

  const [usersRes, crisisRes, aiMsgsRes] = await Promise.all([
    admin.from('user_profiles').select('id'),
    admin.from('messages').select('id').eq('role', 'crisis').gte('created_at', daysAgo(7)),
    admin.from('messages').select('emotional_intensity').eq('role', 'ai').gte('created_at', daysAgo(7)),
  ])

  const totalUsers = usersRes.data?.length ?? 0
  const crisisThisWeek = crisisRes.data?.length ?? 0
  const intensities = (aiMsgsRes.data ?? [])
    .map(m => m.emotional_intensity as number | null)
    .filter((v): v is number => v !== null && v !== undefined)
  const avgEmotionalIntensity = intensities.length
    ? Math.round((intensities.reduce((a, b) => a + b, 0) / intensities.length) * 10) / 10
    : null

  const { data: todayMsgs } = await admin
    .from('messages')
    .select('session_id')
    .gte('created_at', todayUtc)
  const activeSessions = new Set((todayMsgs ?? []).map(m => m.session_id as string))

  let activeToday = 0
  if (activeSessions.size > 0) {
    const { data: sessions } = await admin
      .from('chat_sessions')
      .select('user_id')
      .in('id', Array.from(activeSessions))
    activeToday = new Set((sessions ?? []).map(s => s.user_id as string)).size
  }

  return { totalUsers, activeToday, avgEmotionalIntensity, crisisThisWeek }
}

export async function fetchSystemPerformance(admin: SupabaseClient): Promise<SystemPerformanceData> {
  const { data: rows } = await admin
    .from('messages')
    .select('created_at, latency_ms, intent_classification')
    .eq('role', 'ai')
    .gte('created_at', daysAgo(7))

  const latencyRows = (rows ?? []).filter(r => r.latency_ms != null)

  const latencyByDay = groupByDay(latencyRows as { created_at: string; latency_ms: number }[], (group) => {
    const sorted = group.map(r => r.latency_ms).sort((a, b) => a - b)
    const avgMs = Math.round(sorted.reduce((s, v) => s + v, 0) / sorted.length)
    const p95Ms = sorted[Math.ceil(sorted.length * 0.95) - 1] ?? sorted[sorted.length - 1] ?? 0
    return { avgMs, p95Ms, turnCount: group.length }
  })

  const intentDistribution = countAndRank(
    rows ?? [],
    row => (row.intent_classification as string | null) ?? 'unknown',
    (intent, count) => ({ intent, count }),
  )

  return { latencyByDay, intentDistribution }
}

export async function fetchClinicalSafety(admin: SupabaseClient): Promise<ClinicalSafetyData> {
  const cutoff = daysAgo(7)

  const { data: allMsgs } = await admin
    .from('messages')
    .select('role, clinical_flags, created_at')
    .gte('created_at', cutoff)

  const rows = allMsgs ?? []
  const crisisThisWeek = rows.filter(r => r.role === 'crisis').length
  const withFlags = rows.filter(
    r => Array.isArray(r.clinical_flags) && (r.clinical_flags as string[]).length > 0
  )
  const escalationsThisWeek = withFlags.length

  const allFlags = withFlags.flatMap(row => row.clinical_flags as string[])
  const flagDistribution = countAndRank(allFlags, flag => flag, (flag, count) => ({ flag, count }))

  return { crisisThisWeek, escalationsThisWeek, flagDistribution }
}

export async function fetchResponseQuality(admin: SupabaseClient): Promise<ResponseQualityData> {
  const cutoff = daysAgo(7)

  const [feedbackRes, gateRes] = await Promise.all([
    admin.from('message_feedback').select('value').gte('created_at', cutoff),
    admin.from('messages').select('gate_path').eq('role', 'ai').gte('created_at', cutoff),
  ])

  const feedback = feedbackRes.data ?? []
  const thumbsUp    = feedback.filter(f => (f.value as number) === 1).length
  const thumbsDown  = feedback.filter(f => (f.value as number) === -1).length
  const totalFeedback = feedback.length

  const gatePathDistribution = countAndRank(
    gateRes.data ?? [],
    row => (row.gate_path as string | null) ?? 'standard',
    (gatePath, count) => ({ gatePath, count }),
  )

  return { thumbsUp, thumbsDown, totalFeedback, gatePathDistribution }
}

export async function fetchConversationIntelligence(admin: SupabaseClient): Promise<ConversationIntelligenceData> {
  const cutoff = daysAgo(7)

  const { data: rows } = await admin
    .from('messages')
    .select('skill_id, semantic_score, token_usage')
    .eq('role', 'ai')
    .gte('created_at', cutoff)

  const allRows = rows ?? []
  const total = allRows.length

  // mirrors SEMANTIC_THRESHOLD in sage-poc/src/sage_poc/nodes/skill_select.py
  const withSemantic = allRows.filter(r => (r.semantic_score as number | null) != null && (r.semantic_score as number) >= 0.459).length
  const semanticMatchRate = total > 0 ? Math.round((withSemantic / total) * 100) / 100 : null

  const skillRows = allRows.filter(row => row.skill_id)
  const skillUsage = countAndRank(skillRows, row => row.skill_id as string, (skillId, count) => ({ skillId, count }), 10)

  const usageRows = allRows
    .map(r => r.token_usage as { input?: number; output?: number } | null)
    .filter((u): u is { input: number; output: number } => u !== null && typeof u?.input === 'number' && typeof u?.output === 'number')
  const avgTokenUsageInput = usageRows.length
    ? Math.round(usageRows.reduce((s, u) => s + u.input, 0) / usageRows.length)
    : null
  const avgTokenUsageOutput = usageRows.length
    ? Math.round(usageRows.reduce((s, u) => s + u.output, 0) / usageRows.length)
    : null

  return { semanticMatchRate, skillUsage, avgTokenUsageInput, avgTokenUsageOutput }
}

export async function fetchAllAdminData(
  admin: SupabaseClient,
  hasClinicalAccess: boolean
): Promise<AdminData> {
  const [overview, systemPerformance, clinicalSafety, responseQuality, intelligence] =
    await Promise.all([
      fetchOverviewMetrics(admin),
      fetchSystemPerformance(admin),
      hasClinicalAccess ? fetchClinicalSafety(admin) : Promise.resolve(null),
      fetchResponseQuality(admin),
      fetchConversationIntelligence(admin),
    ])
  return { overview, systemPerformance, clinicalSafety, responseQuality, intelligence }
}
