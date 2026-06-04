'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'

export function StepGuard({ pageStep, children }: { pageStep: number; children: React.ReactNode }) {
  const storedStep = useOnboardingStore((s) => s.step)
  const router = useRouter()
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    // Zustand persist hydrates asynchronously; redirecting before hydration
    // always sees the default step (1) and loops the user back to step-1.
    if (useOnboardingStore.persist.hasHydrated()) {
      setHydrated(true)
    } else {
      return useOnboardingStore.persist.onFinishHydration(() => setHydrated(true))
    }
  }, [])

  useEffect(() => {
    if (!hydrated) return
    if (storedStep > pageStep) {
      router.replace(`/step-${Math.min(storedStep, TOTAL_ONBOARDING_STEPS)}`)
    } else if (storedStep < pageStep) {
      router.replace(`/step-${Math.max(storedStep, 1)}`)
    }
  }, [hydrated, storedStep, pageStep, router])

  if (!hydrated || storedStep !== pageStep) return null
  return <>{children}</>
}
