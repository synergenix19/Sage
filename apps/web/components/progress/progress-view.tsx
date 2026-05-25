'use client'
import Link from 'next/link'
import { tenant } from '@cdai/tenant'
import { EngagementCard } from './engagement-card'
import { MoodChart } from './mood-chart'
import { TopicsScroll } from './topics-scroll'
import { INTENT_TOPIC_LABELS, type ProgressData } from '@/lib/progress-queries'

interface ProgressViewProps {
  data: ProgressData
}

export function ProgressView({ data }: ProgressViewProps) {
  const hasAnyData =
    data.engagement.sessionCount > 0 ||
    data.moodTrajectory.length > 0 ||
    data.topics.length > 0

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 pb-8">
      <h1 className="text-xl font-semibold">{tenant.copy.progressHeader}</h1>

      {!hasAnyData && (
        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-16">
          Your progress will appear here after your first conversation.
          <br />
          <Link
            href="/chat"
            className="mt-2 inline-block text-[var(--color-primary)] underline"
          >
            Start chatting
          </Link>
        </p>
      )}

      {hasAnyData && (
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
                <div
                  key={flag}
                  className="rounded-xl border border-[var(--color-surface-tinted)] bg-[var(--color-surface-tinted)] px-4 py-3"
                >
                  <p className="text-xs leading-relaxed text-[var(--color-text-primary)]">{copy}</p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
