'use client'
import { startTransition, useCallback, useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@cdai/types'

// Derives from the same generated `chat_sessions` row as ChatSession (packages/types) —
// `title` is the one renamed field (DB column is `name`), everything else is row-shape.
export type SessionSummary =
  Pick<Database['public']['Tables']['chat_sessions']['Row'], 'id' | 'updated_at'> & {
    title: string | null
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
    startTransition(() => {
      setLoading(true)
      setError(null)
    })

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
        .then(({ data, error: err }) => {
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
