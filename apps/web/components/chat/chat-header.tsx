'use client'
import { useState } from 'react'
import type { ChatSession } from '@cdai/types'
import { tenant } from '@cdai/tenant'
import { HistoryPanel } from './history-panel'
import { SettingsPanel } from './settings-panel'

export function ChatHeader({ session }: { session: ChatSession | null }) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

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
          <button
            onClick={() => setHistoryOpen(true)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label="History"
          >
            🕐
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label="Settings"
          >
            ⚙
          </button>
        </div>
      </header>
      <HistoryPanel open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  )
}
