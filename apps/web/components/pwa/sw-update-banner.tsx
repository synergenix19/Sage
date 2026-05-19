'use client'
import { useEffect, useState } from 'react'

export function SwUpdateBanner() {
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null)

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    // IMPORTANT: Use serviceWorker.ready (NOT register()) — Serwist auto-registers
    navigator.serviceWorker.ready.then((registration) => {
      if (registration.waiting) setWaitingWorker(registration.waiting)
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        newWorker?.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            setWaitingWorker(newWorker)
          }
        })
      })
    })
  }, [])

  if (!waitingWorker) return null

  function handleUpdate() {
    waitingWorker!.postMessage({ type: 'SKIP_WAITING' })
    window.location.reload()
  }

  return (
    <div className="fixed top-4 inset-x-4 z-50 flex items-center justify-between gap-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-lg">
      <p className="text-sm text-[var(--color-text-primary)]">
        A new version is available
      </p>
      <button
        onClick={handleUpdate}
        className="min-h-[44px] rounded-full bg-[var(--color-primary)] px-4 text-sm text-white"
      >
        Update
      </button>
    </div>
  )
}
