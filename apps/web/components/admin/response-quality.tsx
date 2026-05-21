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

      {data.totalFeedback > 0 && thumbsUpPct !== null && (
        <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <p className="mb-3 text-sm font-medium text-[var(--color-text-primary)]">
            Feedback sentiment
          </p>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-[var(--color-border)]">
            <div
              className="h-full rounded-l-full bg-[var(--color-primary)] transition-all duration-500"
              style={{ width: `${thumbsUpPct}%` }}
            />
            <div
              className="h-full bg-[var(--color-crisis)]"
              style={{ width: `${100 - thumbsUpPct}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>{thumbsUpPct}% positive</span>
            <span>{100 - thumbsUpPct}% needs improvement</span>
          </div>
        </div>
      )}

      {data.totalFeedback === 0 && (
        <p className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 text-sm text-[var(--color-text-secondary)]">
          No feedback submitted yet. Feedback buttons appear below AI messages after the trace-and-feedback plan is deployed.
        </p>
      )}
    </div>
  )
}
