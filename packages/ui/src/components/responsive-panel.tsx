'use client'
import { useEffect, useState } from 'react'
import { BottomSheet } from './bottom-sheet'
import { cn } from '../lib/utils'

interface ResponsivePanelProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function ResponsivePanel({ open, onClose, title, children }: ResponsivePanelProps) {
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    setIsDesktop(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  if (!open) return null

  if (!isDesktop) return <BottomSheet open={open} onClose={onClose} title={title}>{children}</BottomSheet>

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <div className="fixed top-0 end-0 z-50 h-full w-80 flex flex-col bg-[var(--color-surface)] shadow-2xl">
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
          {title && <h2 className="font-semibold">{title}</h2>}
          <button onClick={onClose} className="ms-auto flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]" aria-label="Close">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </>
  )
}
