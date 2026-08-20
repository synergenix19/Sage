'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { t } from '@/lib/copy'

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { sessions, loading, error, refresh } = useChatSessions()
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)

  return (
    <ResponsivePanel open={open} onClose={onClose} title={t('historyPanel.title', locale)}>
      <button
        onClick={() => {
          router.push(`/chat?new=${Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
          onClose()
        }}
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-surface-tinted)] px-4 text-sm font-medium text-[var(--color-primary-dark)] hover:bg-[var(--color-primary)] hover:text-white transition-colors"
      >
        {t('historyPanel.newConvo', locale)}
      </button>
      {loading && (
        <p className="text-sm text-[var(--color-text-secondary)]">{t('historyPanel.loading', locale)}</p>
      )}
      {error && (
        <p className="text-sm text-[var(--color-crisis)]">
          <span>{t('historyPanel.errorMsg', locale)}</span>{' '}
          <button onClick={refresh} className="underline">
            {t('historyPanel.retry', locale)}
          </button>
        </p>
      )}
      {!loading && !error && sessions.length === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          {t('historyPanel.empty', locale)}
        </p>
      )}
      {!loading &&
        !error &&
        sessions.map((s) => (
          <Link
            key={s.id}
            href={`/chat?session=${s.id}`}
            onClick={onClose}
            className="block w-full min-h-[44px] rounded-lg px-3 py-2 text-start text-sm hover:bg-[var(--color-surface-tinted)]"
          >
            {s.title ?? t('historyPanel.untitled', locale)}
          </Link>
        ))}
    </ResponsivePanel>
  )
}
