'use client'
import * as React from 'react'
import { useFocusTrap } from '../hooks/use-focus-trap'
import { cn } from '../lib/utils'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
  title?: string
  closeLabel?: string
}

// A11Y-4: dialog semantics + focus trap, shared with ResponsivePanel's desktop drawer via
// useFocusTrap (promoted from AppSideNav's hand-rolled sign-out confirmation — see that hook for
// the "one tap away, no gates" invariant this preserves).
export function BottomSheet({ open, onClose, children, className, title, closeLabel = 'Close' }: BottomSheetProps) {
  const titleId = React.useId()
  const containerRef = useFocusTrap<HTMLDivElement>(open, onClose)

  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        tabIndex={-1}
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-[var(--color-surface)] shadow-xl',
          className
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
            <h2 id={titleId} className="font-semibold text-[var(--color-text-primary)]">{title}</h2>
            <button
              onClick={onClose}
              className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]"
              aria-label={closeLabel}
            >
              ✕
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </>
  )
}
