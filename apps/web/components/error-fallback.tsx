import { cn } from '@cdai/ui'

// Shared presentational content for the app's error.tsx boundaries (app/error.tsx,
// app/(app)/error.tsx). Next.js requires each route segment's error.tsx to be its own
// file exporting a default component — this factors out the identical copy/markup those
// two files previously duplicated, leaving each error.tsx to own only its error-logging
// effect and its container height (h-dvh at the root vs h-full nested inside (app)'s layout).
interface ErrorFallbackProps {
  reset: () => void
  className?: string
}

export function ErrorFallback({ reset, className }: ErrorFallbackProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-4 p-8 text-center', className)}>
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
