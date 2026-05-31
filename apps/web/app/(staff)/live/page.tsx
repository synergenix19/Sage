// RSC — no 'use client'. LivePanel is the client component.
import { Suspense } from 'react'
import { requireCapability } from '@/lib/auth/get-session-roles'
import { LivePanel } from '@/components/clinical-live/live-panel'

export default async function LivePage() {
  await requireCapability('live:read')

  return (
    <Suspense fallback={
      <div className="p-4 text-sm" style={{ color: 'var(--color-clinical-text)' }}>
        Loading…
      </div>
    }>
      <LivePanel />
    </Suspense>
  )
}
