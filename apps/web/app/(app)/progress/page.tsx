// POST-PILOT: When demoSeed is false, implement real data fetching from
// mood_scores and session_insights tables (populated by the chat API's onFinish callback).
'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { getUserDemoData } from '@/lib/demo-seed'
import { tenant } from '@cdai/tenant'
import { StreakCard } from '@/components/progress/streak-card'
import { MoodChart } from '@/components/progress/mood-chart'
import { TopicsScroll } from '@/components/progress/topics-scroll'
import { InsightsList } from '@/components/progress/insights-list'
import { Skeleton } from '@cdai/ui'
import type { MoodScore, SessionInsight } from '@cdai/types'

interface DemoData {
  streak: number
  moodScores: MoodScore[]
  insights: SessionInsight[]
  topics: string[]
}

export default function ProgressPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [data, setData] = useState<DemoData | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser()
      .then(({ data: { user }, error: authError }) => {
        if (authError || !user) { setError(true); setLoading(false); return }
        // Pilot: always use demo seed. Real data path ships post-pilot when demoSeed is false.
        try {
          setData(getUserDemoData(user.id))
        } catch {
          setError(true)
        }
        setLoading(false)
      })
      .catch(() => { setError(true); setLoading(false) })
  }, [])

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4 pb-8">
      <h1 className="text-xl font-semibold">{tenant.copy.progressHeader}</h1>
      {loading && (
        <>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </>
      )}
      {error && (
        <p className="text-sm text-[var(--color-crisis)]">
          Couldn&apos;t load your progress —{' '}
          <button onClick={() => window.location.reload()} className="underline">retry</button>
        </p>
      )}
      {!loading && !error && !data && (
        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-16">
          Your progress will appear here after your first conversation.
          <br />
          <a href="/chat" className="mt-2 inline-block text-[var(--color-primary)] underline">
            Start chatting
          </a>
        </p>
      )}
      {data && (
        <>
          <StreakCard streak={data.streak} />
          <MoodChart scores={data.moodScores} />
          <TopicsScroll topics={data.topics} />
          <InsightsList insights={data.insights} />
        </>
      )}
    </div>
  )
}
