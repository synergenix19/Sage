'use client'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export function ProgressBar({ totalSteps }: { totalSteps: number }) {
  const step = useOnboardingStore((s) => s.step)
  const pct = Math.round(((step - 1) / totalSteps) * 100)
  return (
    <div className="h-1 w-full bg-[var(--color-border)]">
      <div
        className="h-1 bg-[var(--color-primary)] transition-all duration-350"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
