'use client'
import { useEffect } from 'react'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'

// Resets the persisted onboarding store once the user has reached the app shell.
// Personalising intentionally skips reset() to avoid racing StepGuard; this
// component is the deferred cleanup point.
export function OnboardingCleanup() {
  useEffect(() => {
    const { step, reset } = useOnboardingStore.getState()
    if (step > TOTAL_ONBOARDING_STEPS) reset()
  }, [])
  return null
}
