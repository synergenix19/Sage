'use client'
import { type ReactNode, useEffect, useId, useState } from 'react'
import { BottomSheet } from './bottom-sheet'
import { useFocusTrap } from '../hooks/use-focus-trap'
import { cn } from '../lib/utils'

interface ResponsivePanelProps {
  open: boolean
  onClose: () => void
  title?: string
  closeLabel?: string
  children: ReactNode
}

// A11Y-5/11: dialog semantics + focus trap on the desktop drawer, promoted here (and shared with
// BottomSheet's mobile sheet, see bottom-sheet.tsx) from AppSideNav's hand-rolled sign-out
// confirmation. `closeLabel` lets callers localize the close button's accessible name instead of
// the hardcoded "Close" that shipped before.
export function ResponsivePanel({ open, onClose, title, closeLabel = 'Close', children }: ResponsivePanelProps) {
  const [isDesktop, setIsDesktop] = useState(false)
  const titleId = useId()
  // Only the desktop branch below owns an active trap instance — when rendering BottomSheet
  // (mobile), BottomSheet runs its own, so this one stays inert (open=false) to avoid two traps
  // fighting over Escape/focus-restoration at once.
  const containerRef = useFocusTrap<HTMLDivElement>(open && isDesktop, onClose)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    setIsDesktop(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  if (!open) return null

  if (!isDesktop) {
    return (
      <BottomSheet open={open} onClose={onClose} title={title} closeLabel={closeLabel}>
        {children}
      </BottomSheet>
    )
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        className="fixed top-0 end-0 z-50 h-full w-80 flex flex-col bg-[var(--color-surface)] shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
          {title && <h2 id={titleId} className="font-semibold">{title}</h2>}
          <button onClick={onClose} className="ms-auto flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]" aria-label={closeLabel}>✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </>
  )
}
