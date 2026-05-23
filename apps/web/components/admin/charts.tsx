'use client'
import dynamic from 'next/dynamic'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  LabelList,
} from 'recharts'

// Static imports keep all Recharts sub-components in the same React context as
// their parent chart root. The exported components are wrapped with dynamic
// ssr:false so Next.js skips server-rendering chart output (which relies on
// browser APIs for sizing), while the internals share context correctly.

interface MoodTrendChartProps {
  data: Array<{ date: string; avg: number }>
}

function MoodTrendChartImpl({ data }: MoodTrendChartProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        14-Day Mood Trend
      </h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[1, 5]}
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Line
              type="monotone"
              dataKey="avg"
              stroke="var(--color-primary)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

interface TopTopicsChartProps {
  data: Array<{ topic: string; count: number }>
}

function TopTopicsChartImpl({ data }: TopTopicsChartProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Top Topics
      </h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 8 }}>
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="topic"
              width={100}
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

interface DistrictStressChartProps {
  data: Array<{ district: string; index: number }>
}

// Color interpolation between design token values.
// LOW_RGB  = --color-surface-tinted (#EAF0EA = rgb(234, 240, 234)) — calm/low stress
// HIGH_RGB = --color-crisis         (#DC2626 = rgb(220,  38,  38)) — high stress
// These values mirror the tenant brand tokens. If tokens change, update these constants.
// TODO(post-Gitex): derive from getComputedStyle(document.documentElement) to auto-follow token changes.
const LOW_RGB  = { r: 234, g: 240, b: 234 } // --color-surface-tinted (#EAF0EA)
const HIGH_RGB = { r: 220, g: 38,  b: 38  } // --color-crisis        (#DC2626)

function districtColor(index: number): string {
  const ratio = Math.min(Math.max((index - 20) / 80, 0), 1) // maps 20–100 → 0–1
  const r = Math.round(LOW_RGB.r + (HIGH_RGB.r - LOW_RGB.r) * ratio)
  const g = Math.round(LOW_RGB.g + (HIGH_RGB.g - LOW_RGB.g) * ratio)
  const b = Math.round(LOW_RGB.b + (HIGH_RGB.b - LOW_RGB.b) * ratio)
  return `rgb(${r}, ${g}, ${b})`
}

function DistrictStressChartImpl({ data }: DistrictStressChartProps) {
  const sorted = [...data].sort((a, b) => b.index - a.index)
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 lg:col-span-2">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        District Stress Index
      </h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ top: 0, right: 48, bottom: 0, left: 8 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category"
              dataKey="district"
              width={96}
              tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(v) => [`${v}`, 'Stress index'] as [string, string]}
            />
            <Bar dataKey="index" radius={[0, 4, 4, 0]}>
              {sorted.map((entry) => (
                <Cell key={entry.district} fill={districtColor(entry.index)} />
              ))}
              <LabelList
                dataKey="index"
                position="right"
                style={{ fontSize: 11, fill: 'var(--color-text-secondary)' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

const INTENT_COLORS: Record<string, string> = {
  skill_continuation: '#4A7C59',
  new_skill:          '#2D6B6B',
  general_chat:       '#6B9E7A',
  info_request:       '#3B82F6',
  emotional:          '#8B5CF6',
  crisis:             '#DC2626',
  exit_skill:         '#9CA3AF',
  scope_refusal:      '#D97706',
  jailbreak:          '#D97706',
  unknown:            '#9CA3AF',
}

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
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {data.map((entry) => (
                <Cell
                  key={entry.intent}
                  fill={INTENT_COLORS[entry.intent] ?? INTENT_COLORS.unknown}
                />
              ))}
            </Bar>
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
        Response Latency (7 days)
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

export const MoodTrendChart = dynamic(
  () => Promise.resolve(MoodTrendChartImpl),
  { ssr: false }
)

export const TopTopicsChart = dynamic(
  () => Promise.resolve(TopTopicsChartImpl),
  { ssr: false }
)

export const DistrictStressChart = dynamic(
  () => Promise.resolve(DistrictStressChartImpl),
  { ssr: false }
)

export const IntentBarChart = dynamic(() => Promise.resolve(IntentBarChartImpl), { ssr: false })
export const LatencyLineChart = dynamic(() => Promise.resolve(LatencyLineChartImpl), { ssr: false })
export const FlagBarChart = dynamic(() => Promise.resolve(FlagBarChartImpl), { ssr: false })
export const SkillUsageChart = dynamic(() => Promise.resolve(SkillUsageChartImpl), { ssr: false })
