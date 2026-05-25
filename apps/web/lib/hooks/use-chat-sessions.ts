'use client'
import { useCallback, useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'

export interface SessionSummary {
  id: string
  title: string | null
  updated_at: string
}

export function useChatSessions(): {
  sessions: SessionSummary[]
  loading: boolean
  error: string | null
  refresh: () => void
} {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user }, error: userError }) => {
      if (userError || !user) {
        if (!cancelled) {
          if (userError) setError(userError.message)
          setLoading(false)
        }
        return
      }
      supabase
        .from('chat_sessions')
        .select('id, name, updated_at')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false })
        .limit(20)
        .then(({ data, error: err }: { data: Array<{ id: string; name: string | null; updated_at: string }> | null; error: { message: string } | null }) => {
          if (cancelled) return
          if (err) {
            setError(err.message)
          } else {
            setSessions(
              (data ?? []).map((row) => ({
                id: row.id,
                title: row.name,
                updated_at: row.updated_at,
              }))
            )
          }
          setLoading(false)
        })
    })

    return () => { cancelled = true }
  }, [tick])

  return { sessions, loading, error, refresh }
}
