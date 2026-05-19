'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Card } from '@cdai/ui'
import type { MoodScore } from '@cdai/types'

const LABELS: Record<number, string> = { 1: 'Low', 3: 'Okay', 5: 'Great' }

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en', { weekday: 'short' })
}

export function MoodChart({ scores }: { scores: MoodScore[] }) {
  const last7 = scores.slice(-7).map((s) => ({ day: formatDate(s.createdAt), score: s.score }))

  return (
    <Card>
      <p className="mb-3 text-sm font-medium">Mood this week</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={last7}>
          <XAxis dataKey="day" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 3, 5]}
            tickFormatter={(v) => LABELS[v as number] ?? ''}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip formatter={(v) => [LABELS[v as number] ?? v, 'Mood']} />
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
