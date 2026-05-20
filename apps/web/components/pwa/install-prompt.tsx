'use client'
import { useEffect, useState } from 'react'
import { cn } from '@cdai/ui'

// BeforeInstallPromptEvent is not in the standard TS DOM lib
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const DISMISSED_KEY = 'cdai-install-dismissed'

export function InstallPrompt() {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null)

  useEffect(() => {
    if (localStorage.getItem(DISMISSED_KEY)) return
    const handler = (e: Event) => {
      e.preventDefault()
      setPromptEvent(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  if (!promptEvent) return null

  function handleDismiss() {
    localStorage.setItem(DISMISSED_KEY, '1')
    setPromptEvent(null)
  }

  async function handleInstall() {
    if (!promptEvent) return
    await promptEvent.prompt()
    await promptEvent.userChoice
    // Clear regardless of outcome — prompt() can only be called once per event
    setPromptEvent(null)
  }

  return (
    <div className={cn(
      'fixed bottom-20 inset-x-4 z-50',
      'flex items-center justify-between gap-3',
      'rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-lg'
    )}>
      <p className="text-sm text-[var(--color-text-primary)]">
        Add Sage to your home screen
      </p>
      <div className="flex gap-2">
        <button
          onClick={handleDismiss}
          className="min-h-[44px] px-3 text-sm text-[var(--color-text-secondary)]"
        >
          Later
        </button>
        <button
          onClick={handleInstall}
          className="min-h-[44px] rounded-full bg-[var(--color-primary)] px-4 text-sm text-white"
        >
          Install
        </button>
      </div>
    </div>
  )
}
