'use client'
import Link from 'next/link'
import { cn } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'
import { formatRelativeTime } from '@/lib/format-relative-time'
import { t } from '@/lib/copy'

// ─── SessionList (P4 Task 4) ─────────────────────────────────────────────────
// One component behind the two shells that used to duplicate the session-list
// markup: app-side-nav.tsx's desktop sidebar ("sidebar" variant) and
// history-panel.tsx's mobile panel ("panel" variant). Each shell still routes
// through its OWN copy-registry keys (appSideNav.sessionList.* vs
// historyPanel.*) — Task 2 preserved the Arabic-string drift between them on
// purpose, and this task does not unify it either. Each variant also keeps
// its own current styling exactly (rounded-xl list rows + active/aria-current
// highlighting for the sidebar; rounded-lg rows + empty-state copy + onNavigate
// close-on-click for the panel) — same DOM, same classes, just one file.
export type SessionListVariant = 'sidebar' | 'panel'

interface SessionListProps {
  variant: SessionListVariant
  /** Sidebar-only: id of the session currently open, for aria-current highlighting. */
  activeId?: string | null
  /** Panel-only: called after a session link is clicked (history-panel closes itself). */
  onNavigate?: () => void
}

export function SessionList({ variant, activeId = null, onNavigate }: SessionListProps) {
  const locale = useLocaleStore((s) => s.locale)
  const { sessions, loading, error, refresh } = useChatSessions()

  if (loading) {
    if (variant === 'sidebar') {
      return (
        <div className="flex-1 px-3 py-2">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {t('appSideNav.sessionList.loading', locale)}
          </p>
        </div>
      )
    }
    return (
      <p className="text-sm text-[var(--color-text-secondary)]">{t('historyPanel.loading', locale)}</p>
    )
  }

  if (error) {
    if (variant === 'sidebar') {
      return (
        <div className="flex-1 px-3 py-2 flex flex-col gap-1">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {t('appSideNav.sessionList.errorMsg', locale)} —{' '}
            <button onClick={refresh} className="underline text-xs">
              {t('appSideNav.sessionList.retry', locale)}
            </button>
          </p>
        </div>
      )
    }
    return (
      <p className="text-sm text-[var(--color-crisis)]">
        <span>{t('historyPanel.errorMsg', locale)}</span>{' '}
        <button onClick={refresh} className="underline">
          {t('historyPanel.retry', locale)}
        </button>
      </p>
    )
  }

  if (variant === 'panel' && sessions.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)]">{t('historyPanel.empty', locale)}</p>
    )
  }

  if (variant === 'sidebar') {
    return (
      <ul className="flex-1 overflow-y-auto px-3 py-1 flex flex-col gap-0.5">
        {sessions.map((s) => (
          <li key={s.id}>
            <Link
              href={`/chat?session=${s.id}`}
              aria-current={s.id === activeId ? 'page' : undefined}
              className={cn(
                'flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]',
                s.id === activeId
                  ? 'bg-[var(--color-surface-tinted)]'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
              )}
            >
              <span className="flex-1 truncate text-[var(--color-text-primary)]">
                {s.title ?? t('appSideNav.sessionList.untitled', locale)}
              </span>
              <span className="text-xs text-[var(--color-text-secondary)] text-end shrink-0">
                {formatRelativeTime(s.updated_at, locale)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <>
      {sessions.map((s) => (
        <Link
          key={s.id}
          href={`/chat?session=${s.id}`}
          onClick={onNavigate}
          className="block w-full min-h-[44px] rounded-lg px-3 py-2 text-start text-sm hover:bg-[var(--color-surface-tinted)]"
        >
          {s.title ?? t('historyPanel.untitled', locale)}
        </Link>
      ))}
    </>
  )
}
