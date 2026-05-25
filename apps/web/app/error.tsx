'use client'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
        Something went wrong
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)]">
        We could not load this page. Please try again.
      </p>
      <button
        onClick={reset}
        className="min-h-[44px] rounded-full bg-[var(--color-primary)] px-6 text-sm text-white"
      >
        Try again
      </button>
    </div>
  )
}
