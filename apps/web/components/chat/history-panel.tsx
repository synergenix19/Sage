'use client'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { SessionList } from '@/components/session-list'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { newChatHref } from '@/lib/new-chat'
import { t } from '@/lib/copy'

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)

  return (
    <ResponsivePanel open={open} onClose={onClose} title={t('historyPanel.title', locale)}>
      <button
        onClick={() => {
          router.push(newChatHref())
          onClose()
        }}
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-surface-tinted)] px-4 text-sm font-medium text-[var(--color-primary-dark)] hover:bg-[var(--color-primary)] hover:text-white transition-colors"
      >
        {t('historyPanel.newConvo', locale)}
      </button>
      <SessionList variant="panel" onNavigate={onClose} />
    </ResponsivePanel>
  )
}
