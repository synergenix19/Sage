'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'
import { useLocaleStore } from '@/lib/stores/locale-store'

const LABELS = {
  en: {
    title: 'Past conversations',
    newConvo: '+ New conversation',
    loading: 'Loading…',
    errorMsg: "Couldn’t load history",
    retry: 'retry',
    empty: 'No past conversations yet.',
    untitled: 'Untitled conversation',
  },
  ar: {
    title: 'المحادثات السابقة',
    newConvo: '+ محادثة جديدة',
    loading: 'جار التحميل…',
    errorMsg: 'تعذّر تحميل السجل',
    retry: 'إعادة المحاولة',
    empty: 'لا توجد محادثات سابقة.',
    untitled: 'محادثة بدون عنوان',
  },
} as const

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { sessions, loading, error, refresh } = useChatSessions()
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)
  const t = LABELS[locale] ?? LABELS.en

  return (
    <ResponsivePanel open={open} onClose={onClose} title={t.title}>
      <button
        onClick={() => {
          router.push(`/chat?new=${Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
          onClose()
        }}
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-primary)] px-4 text-sm font-medium text-white hover:bg-[var(--color-primary-dark)]"
      >
        {t.newConvo}
      </button>
      {loading && (
        <p className="text-sm text-[var(--color-text-secondary)]">{t.loading}</p>
      )}
      {error && (
        <p className="text-sm text-[var(--color-crisis)]">
          <span>{t.errorMsg}</span>{' '}
          <button onClick={refresh} className="underline">
            {t.retry}
          </button>
        </p>
      )}
      {!loading && !error && sessions.length === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          {t.empty}
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
            {s.title ?? t.untitled}
          </Link>
        ))}
    </ResponsivePanel>
  )
}
