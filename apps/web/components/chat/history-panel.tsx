'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import type { ChatSession } from '@cdai/types'
import { createClient } from '@/lib/supabase/client'

interface SessionRow {
  id: string
  user_id: string
  name: string | null
  created_at: string
  updated_at: string
}

function rowToSession(row: SessionRow): ChatSession {
  return {
    id: row.id,
    userId: row.user_id,
    name: row.name,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const router = useRouter()

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    setHasError(false)

    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        if (!cancelled) setLoading(false)
        return
      }
      supabase
        .from('chat_sessions')
        .select('*')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false })
        .limit(20)
        .then(({ data, error: err }) => {
          if (cancelled) return
          if (err) {
            setHasError(true)
          } else {
            setSessions((data ?? []).map(rowToSession))
          }
          setLoading(false)
        })
    })

    return () => {
      cancelled = true
    }
  }, [open, reloadKey])

  return (
    <ResponsivePanel open={open} onClose={onClose} title="Past conversations">
      <button
        onClick={() => {
          router.push(`/chat?new=${Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
          onClose()
        }}
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-primary)] px-4 text-sm font-medium text-white hover:bg-[var(--color-primary-dark)]"
      >
        + New conversation
      </button>
      {loading && (
        <p className="text-sm text-[var(--color-text-secondary)]">Loading…</p>
      )}
      {hasError && (
        <p className="text-sm text-[var(--color-crisis)]">
          Couldn&apos;t load history —{' '}
          <button
            onClick={() => setReloadKey((k) => k + 1)}
            className="underline"
          >
            retry
          </button>
        </p>
      )}
      {!loading && !hasError && sessions.length === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          No past conversations yet.
        </p>
      )}
      {!loading &&
        !hasError &&
        sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => {
              router.push(`/chat?session=${s.id}`)
              onClose()
            }}
            className="block w-full min-h-[44px] rounded-lg px-3 py-2 text-start text-sm hover:bg-[var(--color-surface-tinted)]"
          >
            {s.name ?? 'Untitled conversation'}
          </button>
        ))}
    </ResponsivePanel>
  )
}
