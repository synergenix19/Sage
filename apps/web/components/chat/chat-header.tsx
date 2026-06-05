'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { ChatSession } from '@cdai/types'
import { tenant } from '@cdai/tenant'
import { HistoryPanel } from './history-panel'
import { SettingsPanel } from './settings-panel'
// TODO: remove after clinical pilot
import { TestingGuidePanel } from './testing-guide-panel'
import { LanguageToggle } from '@/components/auth/language-toggle'
import { useLocaleStore } from '@/lib/stores/locale-store'

export function ChatHeader({ session }: { session: ChatSession | null }) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  // TODO: remove after clinical pilot period ends
  const [guideOpen, setGuideOpen] = useState(false)
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)

  function handleNewChat() {
    router.push(`/chat?new=${Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
  }

  return (
    <>
      <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <div className="flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-7 w-7" />
          <span className="max-w-[140px] truncate text-sm font-medium text-[var(--color-text-secondary)]">
            {session?.name ?? 'New conversation'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {/* Compose icon — mobile only, left of clock per spec */}
          <button
            onClick={handleNewChat}
            className="md:hidden flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label={locale === 'ar' ? 'محادثة جديدة' : 'New conversation'}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path
                d="M13 2.5a1.414 1.414 0 0 1 2 2L5.5 14.5 2 15.5l1-3.5L13 2.5Z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          {/* Clock icon — mobile only, desktop has sidebar history list */}
          <button
            onClick={() => setHistoryOpen(true)}
            className="md:hidden flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label={locale === 'ar' ? 'السجل' : 'History'}
          >
            🕐
          </button>
          {/* TODO: remove after clinical pilot */}
          <button
            onClick={() => setGuideOpen(true)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-base font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]"
            aria-label="Testing guide"
            title="Testing guide"
          >
            ?
          </button>
          <LanguageToggle />
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label={locale === 'ar' ? 'الإعدادات' : 'Settings'}
          >
            ⚙
          </button>
        </div>
      </header>
      <HistoryPanel open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      {/* TODO: remove after clinical pilot */}
      <TestingGuidePanel open={guideOpen} onClose={() => setGuideOpen(false)} />
    </>
  )
}
