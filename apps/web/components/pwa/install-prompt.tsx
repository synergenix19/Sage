'use client'
import { useEffect, useRef, useState } from 'react'
import { cn } from '@cdai/ui'

// BeforeInstallPromptEvent is not in the standard TS DOM lib
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const DISMISSED_KEY = 'cdai-install-dismissed'
export const FIRST_CHAT_EVENT = 'sage:first-chat-complete'

export function InstallPrompt() {
  const promptRef = useRef<BeforeInstallPromptEvent | null>(null)
  const [showBanner, setShowBanner] = useState(false)

  useEffect(() => {
    if (localStorage.getItem(DISMISSED_KEY)) return

    function tryShow() {
      if (promptRef.current) setShowBanner(true)
    }

    const installHandler = (e: Event) => {
      e.preventDefault()
      promptRef.current = e as BeforeInstallPromptEvent
      // Only reveal if first chat already happened (e.g. browser fires event late)
      if (localStorage.getItem(FIRST_CHAT_EVENT)) tryShow()
    }
    window.addEventListener('beforeinstallprompt', installHandler)

    // Show when the chat interface signals first completed exchange
    window.addEventListener(FIRST_CHAT_EVENT, tryShow)

    return () => {
      window.removeEventListener('beforeinstallprompt', installHandler)
      window.removeEventListener(FIRST_CHAT_EVENT, tryShow)
    }
  }, [])

  const promptEvent = showBanner ? promptRef.current : null

  if (!promptEvent) return null

  function handleDismiss() {
    localStorage.setItem(DISMISSED_KEY, '1')
    setShowBanner(false)
  }

  async function handleInstall() {
    if (!promptRef.current) return
    await promptRef.current.prompt()
    await promptRef.current.userChoice
    // prompt() can only be called once per event; always persist so the banner
    // never reappears even if the browser fires a new beforeinstallprompt later.
    localStorage.setItem(DISMISSED_KEY, '1')
    setShowBanner(false)
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
