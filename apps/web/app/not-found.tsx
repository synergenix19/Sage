import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
        Page not found
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)]">
        This page does not exist or has been moved.
      </p>
      <Link
        href="/chat"
        className="min-h-[44px] inline-flex items-center rounded-full bg-[var(--color-primary)] px-6 text-sm text-white"
      >
        Go to chat
      </Link>
    </div>
  )
}
