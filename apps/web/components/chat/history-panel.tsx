'use client'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { sessions, loading, error, refresh } = useChatSessions()
  const router = useRouter()

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
      {error && (
        <p className="text-sm text-[var(--color-crisis)]">
          Couldn&apos;t load history —{' '}
          <button onClick={refresh} className="underline">
            retry
          </button>
        </p>
      )}
      {!loading && !error && sessions.length === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          No past conversations yet.
        </p>
      )}
      {!loading &&
        !error &&
        sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => {
              router.push(`/chat?session=${s.id}`)
              onClose()
            }}
            className="block w-full min-h-[44px] rounded-lg px-3 py-2 text-start text-sm hover:bg-[var(--color-surface-tinted)]"
          >
            {s.title ?? 'Untitled conversation'}
          </button>
        ))}
    </ResponsivePanel>
  )
}
