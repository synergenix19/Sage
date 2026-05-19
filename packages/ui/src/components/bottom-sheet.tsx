'use client'
import * as React from 'react'
import { cn } from '../lib/utils'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
}

export function BottomSheet({ open, onClose, children, className }: BottomSheetProps) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-[var(--color-surface)] p-6 shadow-xl',
          className
        )}
      >
        {children}
      </div>
    </>
  )
}
