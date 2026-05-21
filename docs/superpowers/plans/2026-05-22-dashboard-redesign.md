# Dashboard Redesign: Admin + Progress

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mock data in both dashboards with real Supabase data. Admin gets 4 new analysis panels ordered by priority: Clinical Safety, System Performance, Response Quality, Conversation Intelligence. Progress replaces streak + demo seed with real mood trajectory, engagement stats, topics, and skill progress.

**Architecture:** Admin dashboard becomes a server component that fetches via Supabase service role, passing typed props to client panel components. Progress page fetches from Supabase using the user's authenticated session (existing RLS). Population Wellness section of admin retains mock data — it requires location/district data not in the current schema and will be wired to real data post-pilot.

**Tech Stack:** Next.js 14 App Router, Supabase JS v2, Recharts (already installed), Vitest, React Testing Library

**Prerequisites:** `003_complete_trace_fields.sql` migration and `trace-and-feedback` plan must both be applied for `intent_classification`, `semantic_score`, and `message_feedback` to contain real data. The dashboards render correctly with those fields NULL — they just show zero/empty states.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `cdai/apps/web/lib/supabase/admin.ts` | Create | Service-role Supabase client (server-only) |
| `cdai/apps/web/lib/admin-queries.ts` | Create | Typed query functions for admin panels |
| `cdai/apps/web/lib/progress-queries.ts` | Create | Typed query functions for progress panels |
| `cdai/apps/web/app/admin/page.tsx` | Modify | Server component: fetch + pass data to AdminDashboard |
| `cdai/apps/web/components/admin/admin-dashboard.tsx` | Create | Client component: receives data, handles highlight state |
| `cdai/apps/web/components/admin/admin-sidebar.tsx` | Modify | Update nav sections to match new panels |
| `cdai/apps/web/components/admin/charts.tsx` | Modify | Add IntentBarChart, FeedbackRatioCard, SkillUsageChart |
| `cdai/apps/web/components/admin/system-performance.tsx` | Create | Latency trend + intent distribution panel |
| `cdai/apps/web/components/admin/clinical-safety.tsx` | Create | Crisis count + clinical flags panel |
| `cdai/apps/web/components/admin/response-quality.tsx` | Create | Feedback ratio + gate path panel |
| `cdai/apps/web/components/admin/conversation-intelligence.tsx` | Create | Skill usage + semantic match panel |
| `cdai/apps/web/app/(app)/progress/page.tsx` | Modify | Replace getUserDemoData() with real queries |
| `cdai/apps/web/components/progress/engagement-card.tsx` | Create | Replaces StreakCard: sessions + skills used |
| `cdai/apps/web/components/progress/mood-chart.tsx` | Modify | Accept MoodPoint[] instead of MoodScore[]; add session tooltip |
| `cdai/apps/web/lib/__tests__/admin-queries.test.ts` | Create | Tests for admin query functions |
| `cdai/apps/web/lib/__tests__/progress-queries.test.ts` | Create | Tests for progress query functions |

---

## Group A: Admin Dashboard

---

### Task A1: Create Supabase service role client

**Files:**
- Create: `cdai/apps/web/lib/supabase/admin.ts`

- [ ] **Step 1: Create the admin client**

Create `cdai/apps/web/lib/supabase/admin.ts`:

```typescript
// lib/supabase/admin.ts
// SERVER-ONLY. Never import this file in client components.
// The service role key bypasses RLS — only use for admin data aggregation.
import { createClient } from '@supabase/supabase-js'

export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) {
    throw new Error('SUPABASE_SERVICE_ROLE_KEY or NEXT_PUBLIC_SUPABASE_URL not set')
  }
  return createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}
```

- [ ] **Step 2: Verify SUPABASE_SERVICE_ROLE_KEY is in .env.local**

```bash
grep -l "SUPABASE_SERVICE_ROLE_KEY" /Users/knowledgebase/Documents/Sage/cdai/apps/web/.env.local 2>/dev/null || echo "NOT FOUND"
```

If NOT FOUND, add to `.env.local`:
```
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_from_supabase_dashboard
```
Find the key in Supabase Dashboard > Project Settings > API > Service role key.

- [ ] **Step 3: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/lib/supabase/admin.ts
git commit -m "feat(admin): add service-role Supabase client for admin data access"
```

---

### Task A2: Create admin-queries.ts with typed query functions

**Files:**
- Create: `cdai/apps/web/lib/admin-queries.ts`
- Create: `cdai/apps/web/lib/__tests__/admin-queries.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/lib/__tests__/admin-queries.test.ts`:

```typescript
// lib/__tests__/admin-queries.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchSystemPerformance,
  fetchClinicalSafety,
  fetchResponseQuality,
  fetchConversationIntelligence,
  fetchOverviewMetrics,
  type AdminData,
} from '../admin-queries'

// Fluent mock: every chaining method returns the same chain object; awaiting
// it resolves with the table's data. Handles all Supabase query chain patterns.
function mockSupabase(rows: Record<string, unknown[]>) {
  function makeChain(table: string) {
    const resolved = Promise.resolve({ data: rows[table] ?? [], error: null })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- admin-queries
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create admin-queries.ts**

Create `cdai/apps/web/lib/admin-queries.ts`:

```typescript
// lib/admin-queries.ts
// All functions accept a Supabase client so they can be tested with mocks.
// Call createAdminClient() from server components and pass it in.

import type { SupabaseClient } from '@supabase/supabase-js'

const SEVEN_DAYS_AGO = () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
const FOURTEEN_DAYS_AGO = () => new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString()

export interface OverviewMetrics {
  totalUsers: number
  activeToday: number
  avgEmotionalIntensity: number | null
  crisisThisWeek: number
}

export interface LatencyDay {
  day: string      // 'YYYY-MM-DD'
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
  clinicalSafety: ClinicalSafetyData
  responseQuality: ResponseQualityData
  intelligence: ConversationIntelligenceData
}

function toDay(isoString: string): string {
  return isoString.slice(0, 10) // 'YYYY-MM-DD'
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
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // 'user_profiles' is the table name in this schema (not 'profiles' or 'users').
  // Verify in Supabase Dashboard > Table Editor before applying if in doubt.
  const [usersRes, crisisRes, aiMsgsRes] = await Promise.all([
    admin.from('user_profiles').select('id'),
    admin.from('messages').select('id').eq('role', 'crisis').gte('created_at', SEVEN_DAYS_AGO()),
    admin.from('messages').select('emotional_intensity').eq('role', 'ai').gte('created_at', SEVEN_DAYS_AGO()),
  ])

  const totalUsers = usersRes.data?.length ?? 0
  const crisisThisWeek = crisisRes.data?.length ?? 0
  const intensities = (aiMsgsRes.data ?? [])
    .map(m => m.emotional_intensity as number | null)
    .filter((v): v is number => v !== null && v !== undefined)
  const avgEmotionalIntensity = intensities.length
    ? Math.round((intensities.reduce((a, b) => a + b, 0) / intensities.length) * 10) / 10
    : null

  // Active today: distinct sessions that have a message today
  const { data: todayMsgs } = await admin
    .from('messages')
    .select('session_id')
    .gte('created_at', today.toISOString())
  const activeSessions = new Set((todayMsgs ?? []).map(m => m.session_id as string))

  // Get distinct user_ids from those sessions
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
    .gte('created_at', FOURTEEN_DAYS_AGO())

  const latencyRows = (rows ?? []).filter(r => r.latency_ms != null)

  const latencyByDay = groupByDay(latencyRows as { created_at: string; latency_ms: number }[], (group) => {
    const sorted = group.map(r => r.latency_ms).sort((a, b) => a - b)
    const avgMs = Math.round(sorted.reduce((s, v) => s + v, 0) / sorted.length)
    const p95Ms = sorted[Math.floor(sorted.length * 0.95)] ?? sorted[sorted.length - 1] ?? 0
    return { avgMs, p95Ms, turnCount: group.length }
  })

  const intentCounts: Record<string, number> = {}
  for (const row of rows ?? []) {
    const intent = (row.intent_classification as string | null) ?? 'unknown'
    intentCounts[intent] = (intentCounts[intent] ?? 0) + 1
  }
  const intentDistribution = Object.entries(intentCounts)
    .map(([intent, count]) => ({ intent, count }))
    .sort((a, b) => b.count - a.count)

  return { latencyByDay, intentDistribution }
}

export async function fetchClinicalSafety(admin: SupabaseClient): Promise<ClinicalSafetyData> {
  const cutoff = SEVEN_DAYS_AGO()

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

  const flagCounts: Record<string, number> = {}
  for (const row of withFlags) {
    for (const flag of row.clinical_flags as string[]) {
      flagCounts[flag] = (flagCounts[flag] ?? 0) + 1
    }
  }
  const flagDistribution = Object.entries(flagCounts)
    .map(([flag, count]) => ({ flag, count }))
    .sort((a, b) => b.count - a.count)

  return { crisisThisWeek, escalationsThisWeek, flagDistribution }
}

export async function fetchResponseQuality(admin: SupabaseClient): Promise<ResponseQualityData> {
  const cutoff = SEVEN_DAYS_AGO()

  const [feedbackRes, gateRes] = await Promise.all([
    admin.from('message_feedback').select('value').gte('created_at', cutoff),
    admin.from('messages').select('gate_path').eq('role', 'ai').gte('created_at', cutoff),
  ])

  const feedback = feedbackRes.data ?? []
  const thumbsUp    = feedback.filter(f => (f.value as number) === 1).length
  const thumbsDown  = feedback.filter(f => (f.value as number) === -1).length
  const totalFeedback = feedback.length

  const gatePathCounts: Record<string, number> = {}
  for (const row of gateRes.data ?? []) {
    const gp = (row.gate_path as string | null) ?? 'standard'
    gatePathCounts[gp] = (gatePathCounts[gp] ?? 0) + 1
  }
  const gatePathDistribution = Object.entries(gatePathCounts)
    .map(([gatePath, count]) => ({ gatePath, count }))
    .sort((a, b) => b.count - a.count)

  return { thumbsUp, thumbsDown, totalFeedback, gatePathDistribution }
}

export async function fetchConversationIntelligence(admin: SupabaseClient): Promise<ConversationIntelligenceData> {
  const cutoff = SEVEN_DAYS_AGO()

  const { data: rows } = await admin
    .from('messages')
    .select('skill_id, semantic_score, token_usage')
    .eq('role', 'ai')
    .gte('created_at', cutoff)

  const allRows = rows ?? []
  const total = allRows.length

  const withSemantic = allRows.filter(r => r.semantic_score != null).length
  const semanticMatchRate = total > 0 ? Math.round((withSemantic / total) * 100) / 100 : null

  const skillCounts: Record<string, number> = {}
  for (const row of allRows) {
    if (row.skill_id) {
      skillCounts[row.skill_id as string] = (skillCounts[row.skill_id as string] ?? 0) + 1
    }
  }
  const skillUsage = Object.entries(skillCounts)
    .map(([skillId, count]) => ({ skillId, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)

  const usageRows = allRows
    .map(r => r.token_usage as { input?: number; output?: number } | null)
    .filter((u): u is { input: number; output: number } => u !== null && typeof u?.input === 'number')
  const avgTokenUsageInput = usageRows.length
    ? Math.round(usageRows.reduce((s, u) => s + u.input, 0) / usageRows.length)
    : null
  const avgTokenUsageOutput = usageRows.length
    ? Math.round(usageRows.reduce((s, u) => s + u.output, 0) / usageRows.length)
    : null

  return { semanticMatchRate, skillUsage, avgTokenUsageInput, avgTokenUsageOutput }
}

export async function fetchAllAdminData(admin: SupabaseClient): Promise<AdminData> {
  const [overview, systemPerformance, clinicalSafety, responseQuality, intelligence] =
    await Promise.all([
      fetchOverviewMetrics(admin),
      fetchSystemPerformance(admin),
      fetchClinicalSafety(admin),
      fetchResponseQuality(admin),
      fetchConversationIntelligence(admin),
    ])
  return { overview, systemPerformance, clinicalSafety, responseQuality, intelligence }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- admin-queries
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/lib/admin-queries.ts apps/web/lib/__tests__/admin-queries.test.ts
git commit -m "feat(admin): add typed Supabase query functions for all 4 admin panels"
```

---

### Task A3: Add new chart components for admin panels

**Files:**
- Modify: `cdai/apps/web/components/admin/charts.tsx`

- [ ] **Step 1: Append new chart implementations to charts.tsx**

Append to the end of `cdai/apps/web/components/admin/charts.tsx` (before the final dynamic exports, add these new implementations, then add dynamic exports at the bottom):

```typescript
// -- New chart implementations for admin panels --

interface IntentBarChartProps {
  data: Array<{ intent: string; count: number }>
}

function IntentBarChartImpl({ data }: IntentBarChartProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Intent Distribution (7 days)
      </h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
            <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="intent" width={120} tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '12px' }} />
            <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

interface LatencyLineChartProps {
  data: Array<{ day: string; avgMs: number; p95Ms: number }>
}

function LatencyLineChartImpl({ data }: LatencyLineChartProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Response Latency (14 days)
      </h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
            <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '12px' }}
              formatter={(v, name) => [`${v}ms`, name === 'avgMs' ? 'Avg' : 'P95'] as [string, string]}
            />
            <Line type="monotone" dataKey="avgMs" stroke="var(--color-primary)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} name="avgMs" />
            <Line type="monotone" dataKey="p95Ms" stroke="var(--color-border)" strokeWidth={1} strokeDasharray="4 2" dot={false} name="p95Ms" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

interface FlagBarChartProps {
  data: Array<{ flag: string; count: number }>
}

function FlagBarChartImpl({ data }: FlagBarChartProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Clinical Flags (7 days)
      </h2>
      {data.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No flags this week.</p>
      ) : (
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
              <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="flag" width={120} tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '12px' }} />
              <Bar dataKey="count" fill="var(--color-crisis)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

interface SkillUsageChartProps {
  data: Array<{ skillId: string; count: number }>
}

function SkillUsageChartImpl({ data }: SkillUsageChartProps) {
  const display = data.slice(0, 8)
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Skill Usage (7 days)
      </h2>
      {display.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No skills activated this week.</p>
      ) : (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={display} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
              <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="skillId" width={140} tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', fontSize: '12px' }} />
              <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
```

Then append the dynamic exports (add to the end of the file):

```typescript
export const IntentBarChart = dynamic(() => Promise.resolve(IntentBarChartImpl), { ssr: false })
export const LatencyLineChart = dynamic(() => Promise.resolve(LatencyLineChartImpl), { ssr: false })
export const FlagBarChart = dynamic(() => Promise.resolve(FlagBarChartImpl), { ssr: false })
export const SkillUsageChart = dynamic(() => Promise.resolve(SkillUsageChartImpl), { ssr: false })
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web build 2>&1 | head -30
```
Expected: no TypeScript errors in charts.tsx (build may warn about other things).

- [ ] **Step 3: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/components/admin/charts.tsx
git commit -m "feat(admin): add IntentBarChart, LatencyLineChart, FlagBarChart, SkillUsageChart"
```

---

### Task A4: Create 4 admin panel components

**Files:**
- Create: `cdai/apps/web/components/admin/system-performance.tsx`
- Create: `cdai/apps/web/components/admin/clinical-safety.tsx`
- Create: `cdai/apps/web/components/admin/response-quality.tsx`
- Create: `cdai/apps/web/components/admin/conversation-intelligence.tsx`

- [ ] **Step 1: Create system-performance.tsx**

Create `cdai/apps/web/components/admin/system-performance.tsx`:

```typescript
import { MetricCard } from './metric-card'
import { LatencyLineChart, IntentBarChart } from './charts'
import type { OverviewMetrics, SystemPerformanceData } from '@/lib/admin-queries'

interface Props {
  overview: OverviewMetrics
  data: SystemPerformanceData
}

export function SystemPerformancePanel({ overview, data }: Props) {
  const avgLatency = data.latencyByDay.length
    ? Math.round(data.latencyByDay.reduce((s, d) => s + d.avgMs, 0) / data.latencyByDay.length)
    : null
  const totalTurns = data.latencyByDay.reduce((s, d) => s + d.turnCount, 0)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <MetricCard label="Total Users" value={overview.totalUsers} subtext="All registered accounts" />
        <MetricCard label="Active Today" value={overview.activeToday} subtext="Distinct users with sessions today" />
        <MetricCard
          label="Avg Latency (14d)"
          value={avgLatency !== null ? `${avgLatency}ms` : 'No data'}
          subtext={`${totalTurns} AI turns recorded`}
        />
      </div>
      <LatencyLineChart data={data.latencyByDay} />
      <IntentBarChart data={data.intentDistribution} />
    </div>
  )
}
```

- [ ] **Step 2: Create clinical-safety.tsx**

Create `cdai/apps/web/components/admin/clinical-safety.tsx`:

```typescript
import { MetricCard } from './metric-card'
import { FlagBarChart } from './charts'
import type { ClinicalSafetyData } from '@/lib/admin-queries'

export function ClinicalSafetyPanel({ data }: { data: ClinicalSafetyData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="Crisis Events (7d)"
          value={data.crisisThisWeek}
          subtext="Messages flagged as crisis"
        />
        <MetricCard
          label="Clinical Escalations (7d)"
          value={data.escalationsThisWeek}
          subtext="Turns with clinical flags"
        />
      </div>
      <FlagBarChart data={data.flagDistribution} />
    </div>
  )
}
```

- [ ] **Step 3: Create response-quality.tsx**

Create `cdai/apps/web/components/admin/response-quality.tsx`:

```typescript
import { MetricCard } from './metric-card'
import type { ResponseQualityData } from '@/lib/admin-queries'

export function ResponseQualityPanel({ data }: { data: ResponseQualityData }) {
  const thumbsUpPct = data.totalFeedback > 0
    ? Math.round((data.thumbsUp / data.totalFeedback) * 100)
    : null

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Thumbs Up (7d)"
          value={data.thumbsUp}
          subtext={thumbsUpPct !== null ? `${thumbsUpPct}% of all feedback` : 'No feedback yet'}
        />
        <MetricCard
          label="Thumbs Down (7d)"
          value={data.thumbsDown}
          subtext={data.totalFeedback > 0 ? `${data.totalFeedback} total ratings` : 'No feedback yet'}
        />
        {data.gatePathDistribution.map(({ gatePath, count }) => (
          <MetricCard key={gatePath} label={`Gate: ${gatePath}`} value={count} subtext="AI turns this week" />
        ))}
      </div>
      {data.totalFeedback === 0 && (
        <p className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 text-sm text-[var(--color-text-secondary)]">
          No feedback submitted yet. Feedback buttons appear below AI messages after the trace-and-feedback plan is deployed.
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create conversation-intelligence.tsx**

Create `cdai/apps/web/components/admin/conversation-intelligence.tsx`:

```typescript
import { MetricCard } from './metric-card'
import { SkillUsageChart } from './charts'
import type { ConversationIntelligenceData } from '@/lib/admin-queries'

export function ConversationIntelligencePanel({ data }: { data: ConversationIntelligenceData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Semantic Match Rate"
          value={data.semanticMatchRate !== null ? `${Math.round(data.semanticMatchRate * 100)}%` : 'No data'}
          subtext="Turns matched via semantic skill search"
        />
        <MetricCard
          label="Avg Input Tokens"
          value={data.avgTokenUsageInput ?? 'No data'}
          subtext="Per AI turn (7 days)"
        />
        <MetricCard
          label="Avg Output Tokens"
          value={data.avgTokenUsageOutput ?? 'No data'}
          subtext="Per AI turn (7 days)"
        />
        <MetricCard
          label="Skills Active"
          value={data.skillUsage.length}
          subtext="Distinct skills used this week"
        />
      </div>
      <SkillUsageChart data={data.skillUsage} />
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add \
  apps/web/components/admin/system-performance.tsx \
  apps/web/components/admin/clinical-safety.tsx \
  apps/web/components/admin/response-quality.tsx \
  apps/web/components/admin/conversation-intelligence.tsx
git commit -m "feat(admin): add 4 analysis panel components (System Performance, Clinical Safety, Response Quality, Intelligence)"
```

---

### Task A5: Create AdminDashboard client component and update admin page

**Files:**
- Create: `cdai/apps/web/components/admin/admin-dashboard.tsx`
- Modify: `cdai/apps/web/components/admin/admin-sidebar.tsx`
- Modify: `cdai/apps/web/app/admin/page.tsx`

- [ ] **Step 1: Create AdminDashboard client component**

Create `cdai/apps/web/components/admin/admin-dashboard.tsx`:

```typescript
'use client'
import { useState, useCallback } from 'react'
import { cn } from '@cdai/ui'
import { MetricCard } from './metric-card'
import { MoodTrendChart, TopTopicsChart, DistrictStressChart } from './charts'
import { AlertsPanel } from './alerts-panel'
import { SystemPerformancePanel } from './system-performance'
import { ClinicalSafetyPanel } from './clinical-safety'
import { ResponseQualityPanel } from './response-quality'
import { ConversationIntelligencePanel } from './conversation-intelligence'
import { getAdminDemoData } from '@/lib/admin-seed'
import type { AdminData } from '@/lib/admin-queries'

interface Props {
  data: AdminData
}

export function AdminDashboard({ data }: Props) {
  const [highlightSection, setHighlightSection] = useState<string | null>(null)
  const demo = getAdminDemoData() // Population Wellness still uses demo data

  const handleAlertClick = useCallback((targetSection: string) => {
    setHighlightSection(targetSection)
    setTimeout(() => {
      document.getElementById(targetSection)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
    setTimeout(() => setHighlightSection(null), 4000)
  }, [])

  function sectionClass(id: string) {
    if (highlightSection === null) return ''
    return highlightSection === id ? '' : 'opacity-20 transition-opacity duration-300'
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Admin Dashboard</h1>
        <p className="text-xs text-[var(--color-text-secondary)]">Live data, last 7 days unless noted</p>
      </div>

      {/* Crisis summary banner — leads with the clinician's primary concern */}
      {data.clinicalSafety.crisisThisWeek > 0 && (
        <div className="rounded-2xl border border-[var(--color-crisis)] bg-[var(--color-crisis)]/10 px-5 py-4">
          <p className="text-sm font-semibold text-[var(--color-crisis)]">
            {data.clinicalSafety.crisisThisWeek} crisis event{data.clinicalSafety.crisisThisWeek !== 1 ? 's' : ''} this week
          </p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            Review the Clinical Safety section below for details.
          </p>
        </div>
      )}

      {/* Pyramid Principle: Clinical Safety leads — it is the admin's primary responsibility */}
      <section id="clinical-safety" className={sectionClass('clinical-safety')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">Clinical Safety</h2>
        <ClinicalSafetyPanel data={data.clinicalSafety} />
      </section>

      <section id="system-performance" className={sectionClass('system-performance')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">System Performance</h2>
        <SystemPerformancePanel overview={data.overview} data={data.systemPerformance} />
      </section>

      <section id="response-quality" className={sectionClass('response-quality')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">Response Quality</h2>
        <ResponseQualityPanel data={data.responseQuality} />
      </section>

      <section id="intelligence" className={sectionClass('intelligence')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">Conversation Intelligence</h2>
        <ConversationIntelligencePanel data={data.intelligence} />
      </section>

      <section id="population">
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">
          Population Wellness
          <span className="ml-2 text-xs font-normal text-[var(--color-text-secondary)]">(demo data, location signals pending)</span>
        </h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-4">
          <MetricCard label="Avg Mood Score" value={demo.avgMoodScore} subtext="Out of 5.0 this week (demo)" />
          <MetricCard label="Crisis Alerts" value={demo.crisisAlertsThisWeek} subtext="This week (demo)" />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 mb-4">
          <MoodTrendChart data={demo.moodTrend} />
          <TopTopicsChart data={demo.topTopics} />
        </div>
        <DistrictStressChart data={demo.districtStress} />
        <div className="mt-4">
          <AlertsPanel alerts={demo.recentAlerts} onAlertClick={handleAlertClick} />
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Update admin-sidebar.tsx**

Replace the `SECTIONS` array in `cdai/apps/web/components/admin/admin-sidebar.tsx`:

```typescript
const SECTIONS = [
  { id: 'clinical-safety',    label: 'Clinical Safety'    },
  { id: 'system-performance', label: 'System Performance' },
  { id: 'response-quality',   label: 'Response Quality'   },
  { id: 'intelligence',       label: 'Intelligence'       },
  { id: 'population',         label: 'Population'         },
]
```

- [ ] **Step 3: Update admin page.tsx to be a server component**

Replace the full content of `cdai/apps/web/app/admin/page.tsx`:

```typescript
import { createAdminClient } from '@/lib/supabase/admin'
import { fetchAllAdminData } from '@/lib/admin-queries'
import { AdminDashboard } from '@/components/admin/admin-dashboard'

// ISR: revalidate every 60s so the admin page is served from cache between refreshes.
// Without this, every page load fires all Supabase queries on the server.
export const revalidate = 60

export default async function AdminPage() {
  let data
  try {
    const admin = createAdminClient()
    data = await fetchAllAdminData(admin)
  } catch (err) {
    console.error('[admin] data fetch failed:', err)
    return (
      <div className="p-6">
        <p className="text-sm text-[var(--color-crisis)]">
          Admin data unavailable. Check SUPABASE_SERVICE_ROLE_KEY in .env.local.
        </p>
      </div>
    )
  }

  return <AdminDashboard data={data} />
}
```

- [ ] **Step 4: Verify the page compiles**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web build 2>&1 | grep -E "error|Error|✓" | head -20
```
Expected: no TypeScript errors. The build may fail on other unrelated pages — focus only on admin page errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add \
  apps/web/components/admin/admin-dashboard.tsx \
  apps/web/components/admin/admin-sidebar.tsx \
  apps/web/app/admin/page.tsx
git commit -m "feat(admin): replace mock data with real Supabase queries, add 4 analysis panels"
```

---

## Group B: Progress Dashboard

---

### Task B1: Create progress-queries.ts

**Files:**
- Create: `cdai/apps/web/lib/progress-queries.ts`
- Create: `cdai/apps/web/lib/__tests__/progress-queries.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `cdai/apps/web/lib/__tests__/progress-queries.test.ts`:

```typescript
// lib/__tests__/progress-queries.test.ts
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

// Same fluent-mock pattern as admin-queries test: handles all chain shapes.
function mockClient(data: Record<string, unknown[]>) {
  function makeChain(table: string) {
    const resolved = Promise.resolve({ data: data[table] ?? [], error: null })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
    // emotional_intensity=8 (high distress) → mood = 5 - 8/2 = 1.0 (low end)
    const client = mockClient({
      chat_sessions: [{ id: 's1', name: 'Test Session', user_id: USER_ID }],
      messages: [
        { created_at: '2026-05-22T10:00:00Z', emotional_intensity: 8, session_id: 's1', role: 'ai' },
      ],
    })
    const result = await fetchMoodTrajectory(client as never, USER_ID)
    if (result.length > 0) {
      expect(result[0].avgIntensity).toBe(1.0) // 5 - 8/2 = 1.0
      expect(result[0].avgIntensity).toBeLessThan(3) // high distress = low mood
    }
  })

  it('returns near-max mood for calm sessions', async () => {
    // emotional_intensity=2 (calm) → mood = 5 - 2/2 = 4.0
    const client = mockClient({
      chat_sessions: [{ id: 's1', name: 'Calm session', user_id: USER_ID }],
      messages: [
        { created_at: '2026-05-22T10:00:00Z', emotional_intensity: 2, session_id: 's1', role: 'ai' },
      ],
    })
    const result = await fetchMoodTrajectory(client as never, USER_ID)
    if (result.length > 0) {
      expect(result[0].avgIntensity).toBe(4.0) // 5 - 2/2 = 4.0
      expect(result[0].avgIntensity).toBeGreaterThan(3) // calm = high mood
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- progress-queries
```
Expected: FAIL — module not found.

- [ ] **Step 3: Create progress-queries.ts**

Create `cdai/apps/web/lib/progress-queries.ts`:

```typescript
// lib/progress-queries.ts
// All functions accept a Supabase client (server or browser) for testability.
// Uses the user's auth session — RLS applies. Pass createClient() result in.

import type { SupabaseClient } from '@supabase/supabase-js'

const THIRTY_DAYS_AGO = () => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
const TWENTY_ONE_DAYS_AGO = () => new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString()

export interface EngagementStats {
  sessionCount: number
  skillsUsedCount: number
}

export interface MoodPoint {
  day: string              // 'YYYY-MM-DD'
  avgIntensity: number     // normalized to 1-5 scale (emotional_intensity / 2)
  sessionName: string | null
}

export interface TopicStat {
  topic: string
  count: number
}

export interface SkillStat {
  skillId: string
}

// Maps raw intent_classification values to user-facing labels for TopicsScroll.
// Unknown intents fall back to the raw value (capitalised by the component).
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
  const { data: sessions } = await client
    .from('chat_sessions')
    .select('id')
    .eq('user_id', userId)

  const sessionIds = (sessions ?? []).map(s => s.id as string)
  if (sessionIds.length === 0) return { sessionCount: 0, skillsUsedCount: 0 }

  const { data: skillMsgs } = await client
    .from('messages')
    .select('skill_id')
    .in('session_id', sessionIds)
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

  // Group by day, average intensity, attach most recent session name
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
        // INVERT: emotional_intensity is a DISTRESS scale (1=calm, 10=extreme distress).
        // High distress must map to LOW mood, not high. Formula: 5 - (avg / 2)
        // so intensity=1 → 4.5 (near Great), intensity=10 → 0 (Low).
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web test -- progress-queries
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/lib/progress-queries.ts apps/web/lib/__tests__/progress-queries.test.ts
git commit -m "feat(progress): add typed Supabase query functions for progress dashboard"
```

---

### Task B2: Create EngagementCard component

**Files:**
- Create: `cdai/apps/web/components/progress/engagement-card.tsx`

- [ ] **Step 1: Create the component**

Create `cdai/apps/web/components/progress/engagement-card.tsx`:

```typescript
import { Card } from '@cdai/ui'
import type { EngagementStats } from '@/lib/progress-queries'

export function EngagementCard({ stats }: { stats: EngagementStats }) {
  return (
    <Card className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-2xl font-semibold">{stats.sessionCount}</p>
        <p className="text-xs text-[var(--color-text-secondary)]">conversations</p>
      </div>
      <div>
        <p className="text-2xl font-semibold">{stats.skillsUsedCount}</p>
        <p className="text-xs text-[var(--color-text-secondary)]">
          {stats.skillsUsedCount === 1 ? 'technique explored' : 'techniques explored'}
        </p>
      </div>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/components/progress/engagement-card.tsx
git commit -m "feat(progress): add EngagementCard (sessions + techniques explored)"
```

---

### Task B3: Update MoodChart for new data shape and session annotations

**Files:**
- Modify: `cdai/apps/web/components/progress/mood-chart.tsx`

- [ ] **Step 1: Replace the component**

Replace the full content of `cdai/apps/web/components/progress/mood-chart.tsx`:

```typescript
'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Card } from '@cdai/ui'
import type { MoodPoint } from '@/lib/progress-queries'

// Scale: 0 = Low (intensity 10), 2.5 = Okay (intensity 5), 5 = Great (intensity 0/1).
// Derived from the inversion formula: 5 - (emotional_intensity / 2).
const MOOD_LABELS: Record<number, string> = { 0: 'Low', 2.5: 'Okay', 5: 'Great' }

function formatDay(isoDay: string) {
  return new Date(isoDay + 'T00:00:00').toLocaleDateString('en', { weekday: 'short' })
}

interface TooltipPayload {
  payload?: { sessionName?: string | null }
  value?: number
  label?: string
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipPayload[]; label?: string }) {
  if (!active || !payload?.length) return null
  const point = payload[0]
  const mood = point.value
  const session = point.payload?.sessionName

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs shadow">
      <p className="font-medium">{label}</p>
      <p>Mood: {MOOD_LABELS[Math.round((mood ?? 0) * 2) / 2 as keyof typeof MOOD_LABELS] ?? mood}</p>
      {session && <p className="text-[var(--color-text-secondary)]">{session}</p>}
    </div>
  )
}

export function MoodChart({ points }: { points: MoodPoint[] }) {
  const last7 = points.slice(-7).map(p => ({
    day: formatDay(p.day),
    score: p.avgIntensity,
    sessionName: p.sessionName,
  }))

  if (last7.length === 0) {
    return (
      <Card>
        <p className="mb-3 text-sm font-medium">Mood this week</p>
        <p className="text-xs text-[var(--color-text-secondary)]">
          Your mood trend will appear after a few conversations.
        </p>
      </Card>
    )
  }

  return (
    <Card>
      <p className="mb-3 text-sm font-medium">Mood this week</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={last7}>
          <XAxis dataKey="day" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis
            domain={[0, 5]}
            ticks={[0, 2.5, 5]}
            tickFormatter={(v) => MOOD_LABELS[v as number] ?? ''}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="score"
            stroke="var(--color-primary)"
            strokeWidth={2}
            dot={{ fill: 'var(--color-primary)', r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/components/progress/mood-chart.tsx
git commit -m "feat(progress): update MoodChart to accept MoodPoint[], add session name tooltip"
```

---

### Task B4: Wire up progress page with real Supabase data

**Files:**
- Modify: `cdai/apps/web/app/(app)/progress/page.tsx`

- [ ] **Step 1: Replace progress page**

Replace the full content of `cdai/apps/web/app/(app)/progress/page.tsx`:

```typescript
'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { fetchAllProgressData, INTENT_TOPIC_LABELS, type ProgressData } from '@/lib/progress-queries'
import { tenant } from '@cdai/tenant'
import { EngagementCard } from '@/components/progress/engagement-card'
import { MoodChart } from '@/components/progress/mood-chart'
import { TopicsScroll } from '@/components/progress/topics-scroll'
import { InsightsList } from '@/components/progress/insights-list'
import { Skeleton } from '@cdai/ui'

export default function ProgressPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [data, setData] = useState<ProgressData | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser()
      .then(async ({ data: { user }, error: authError }) => {
        if (authError || !user) {
          // Not authenticated — redirect rather than showing a broken page.
          router.push('/sign-in')
          return
        }
        try {
          const result = await fetchAllProgressData(supabase, user.id)
          setData(result)
        } catch {
          setError(true)
        }
        setLoading(false)
      })
      .catch(() => { setError(true); setLoading(false) })
  }, [router])

  const hasAnyData = data && (
    data.engagement.sessionCount > 0 ||
    data.moodTrajectory.length > 0 ||
    data.topics.length > 0
  )

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4 pb-8">
      <h1 className="text-xl font-semibold">{tenant.copy.progressHeader}</h1>
      {loading && (
        <>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-24 w-full" />
        </>
      )}
      {error && (
        <p className="text-sm text-[var(--color-crisis)]">
          Couldn&apos;t load your progress,{' '}
          <button onClick={() => window.location.reload()} className="underline">retry</button>
        </p>
      )}
      {!loading && !error && !hasAnyData && (
        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-16">
          Your progress will appear here after your first conversation.
          <br />
          <a href="/chat" className="mt-2 inline-block text-[var(--color-primary)] underline">
            Start chatting
          </a>
        </p>
      )}
      {!loading && !error && hasAnyData && data && (
        <>
          <EngagementCard stats={data.engagement} />
          <MoodChart points={data.moodTrajectory} />
          {data.topics.length > 0 && (
            <TopicsScroll
              topics={data.topics.map(t => INTENT_TOPIC_LABELS[t.topic] ?? t.topic)}
            />
          )}
          {data.skills.length > 0 && (
            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
              <p className="mb-2 text-sm font-medium">Techniques you have explored</p>
              <div className="flex flex-wrap gap-2">
                {data.skills.map(s => (
                  <span
                    key={s.skillId}
                    className="rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)]"
                  >
                    {s.skillId.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
          {data.clinicalFlags.length > 0 && (
            <div className="space-y-2">
              {data.clinicalFlags.map(({ flag, copy }) => (
                <p
                  key={flag}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-xs text-[var(--color-text-secondary)]"
                >
                  {copy}
                </p>
              ))}
            </div>
          )}
          <InsightsList insights={[]} />
        </>
      )}
    </div>
  )
}
```

Note: `InsightsList` receives an empty array since `session_insights` is populated post-pilot (the `POST-PILOT` comment in route.ts). The component should already handle an empty list gracefully.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web build 2>&1 | grep -E "error TS" | head -20
```
Expected: no TypeScript errors in progress/page.tsx.

- [ ] **Step 3: Run all tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm test
```
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/app/\(app\)/progress/page.tsx
git commit -m "feat(progress): replace demo seed with real Supabase data (engagement, mood, topics, skills, gentle flags)"
```

---

## Final: Full test run

- [ ] **Run frontend tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm test
```
Expected: all PASS

- [ ] **Spot-check: TypeScript build**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
pnpm --filter @web build 2>&1 | tail -10
```
Expected: build completes (or known pre-existing errors only — none new from this plan).
