'use client'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { Card } from '@cdai/ui'
import type { MoodPoint } from '@/lib/progress-queries'

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
  const rounded = Math.round((mood ?? 0) * 2) / 2
  const moodLabel = MOOD_LABELS[rounded as keyof typeof MOOD_LABELS] ?? mood?.toFixed(1)

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs shadow">
      <p className="font-medium">{label}</p>
      <p>Feeling: <span className="font-medium text-[var(--color-text-primary)]">{moodLabel}</span></p>
      {session && <p className="mt-0.5 text-[var(--color-text-secondary)]">{session}</p>}
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
        <p className="text-sm text-[var(--color-text-secondary)]">
          Your mood over time will appear here. Start a conversation to begin tracking.
        </p>
      </Card>
    )
  }

  return (
    <Card>
      <p className="mb-3 text-sm font-medium">Mood this week</p>
      <ResponsiveContainer width="100%" height={130}>
        <AreaChart data={last7} margin={{ top: 4, right: 4, bottom: 0, left: -8 }}>
          <defs>
            <linearGradient id="moodAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#4A7C59" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#4A7C59" stopOpacity={0} />
            </linearGradient>
          </defs>
          <ReferenceLine y={2.5} stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis dataKey="day" tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }} axisLine={false} tickLine={false} />
          <YAxis
            domain={[0, 5]}
            ticks={[0, 2.5, 5]}
            tickFormatter={(v) => MOOD_LABELS[v as number] ?? ''}
            tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="score"
            stroke="#4A7C59"
            strokeWidth={2}
            fill="url(#moodAreaGradient)"
            dot={{ fill: '#4A7C59', r: 3, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: '#4A7C59', strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  )
}
