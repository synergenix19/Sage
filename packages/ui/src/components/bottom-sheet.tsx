'use client'
import * as React from 'react'
import { cn } from '../lib/utils'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
  title?: string
}

export function BottomSheet({ open, onClose, children, className, title }: BottomSheetProps) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-[var(--color-surface)] shadow-xl',
          className
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
            <h2 className="font-semibold text-[var(--color-text-primary)]">{title}</h2>
            <button
              onClick={onClose}
              className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]"
              aria-label="Close"
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
