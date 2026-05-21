'use client'
import { useState } from 'react'
import { cn } from '@cdai/ui'

interface Props {
  messageId: string
  onFeedback: (messageId: string, value: 1 | -1) => void
}

function ThumbsUpIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  )
}

function ThumbsDownIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    </svg>
  )
}

export function FeedbackButtons({ messageId, onFeedback }: Props) {
  const [selected, setSelected] = useState<1 | -1 | null>(null)

  function handleClick(value: 1 | -1) {
    if (selected !== null) return
    setSelected(value)
    onFeedback(messageId, value)
  }

  return (
    <div className="flex gap-1 mt-1">
      <button
        aria-label="Thumbs up"
        aria-pressed={selected === 1}
        disabled={selected !== null}
        onClick={() => handleClick(1)}
        className={cn(
          'rounded-full p-1.5 transition-all',
          selected === 1
            ? 'text-[var(--color-primary)] opacity-100'
            : 'text-[var(--color-text-secondary)] opacity-70 hover:opacity-100 hover:text-[var(--color-primary)]',
          'disabled:cursor-default'
        )}
      >
        <ThumbsUpIcon />
      </button>
      <button
        aria-label="Thumbs down"
        aria-pressed={selected === -1}
        disabled={selected !== null}
        onClick={() => handleClick(-1)}
        className={cn(
          'rounded-full p-1.5 transition-all',
          selected === -1
            ? 'text-[var(--color-crisis)] opacity-100'
            : 'text-[var(--color-text-secondary)] opacity-70 hover:opacity-100 hover:text-[var(--color-crisis)]',
          'disabled:cursor-default'
        )}
      >
        <ThumbsDownIcon />
      </button>
    </div>
  )
}
