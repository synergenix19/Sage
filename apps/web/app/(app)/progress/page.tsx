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
import type { SessionInsight } from '@cdai/types'

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
                <div
                  key={flag}
                  className="rounded-xl border border-[var(--color-surface-tinted)] bg-[var(--color-surface-tinted)] px-4 py-3"
                >
                  <p className="text-xs leading-relaxed text-[var(--color-text-primary)]">{copy}</p>
                </div>
              ))}
            </div>
          )}
          <InsightsList insights={[] as SessionInsight[]} />
        </>
      )}
    </div>
  )
}
