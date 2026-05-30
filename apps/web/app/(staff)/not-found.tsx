// Renders at the (staff)/ segment level so Next.js App Router sets HTTP 404
// when requireCapability() calls notFound() from any (staff) route.
// Placing this at app/not-found.tsx causes the (staff)/layout.tsx to wrap it
// (because that layout ran successfully), resulting in HTTP 200 from the
// framework's perspective. A segment-level not-found.tsx stops the layout
// chain at the right point and sets the 404 status correctly.
import Link from 'next/link'

export default function StaffNotFound() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
        Page not found
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)]">
        This page does not exist or you do not have access to it.
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
