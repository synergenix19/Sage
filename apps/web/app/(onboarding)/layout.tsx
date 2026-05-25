import { ProgressBar } from '@/components/onboarding/progress-bar'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col bg-[var(--color-surface)]">
      <ProgressBar totalSteps={TOTAL_ONBOARDING_STEPS} />
      <main id="main-content" className="flex flex-1 flex-col items-center justify-center px-6 py-8">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  )
}
