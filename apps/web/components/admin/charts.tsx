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

export const MoodTrendChart = dynamic(
  () => Promise.resolve(MoodTrendChartImpl),
  { ssr: false }
)

export const TopTopicsChart = dynamic(
  () => Promise.resolve(TopTopicsChartImpl),
  { ssr: false }
)
