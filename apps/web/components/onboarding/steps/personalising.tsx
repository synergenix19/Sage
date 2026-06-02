'use client'
import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'
import { createClient } from '@/lib/supabase/client'

export function Personalising() {
  const { setStep } = useOnboardingStore()
  const [failed, setFailed] = useState(false)
  const router = useRouter()
  const failTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => { mountedRef.current = false }
  }, [])

  async function persist() {
    // Read answers at call time — safe against Zustand async rehydration
    const { answers } = useOnboardingStore.getState()

    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) { router.push('/sign-in'); return }

    const { error } = await supabase.from('user_profiles').upsert({
      id: user.id,
      name: answers.name,
      age_range: answers.ageRange,
      role: answers.role,
      locale: answers.locale ?? 'en',
      wellness_q1: answers.wellnessQ1,
      wellness_q2: answers.wellnessQ2,
      onboarding_complete: true,
      onboarding_step: TOTAL_ONBOARDING_STEPS,
    })

    if (error) {
      if (mountedRef.current) setFailed(true)
      return
    }
    clearTimeout(failTimerRef.current!)
    // Advance past the final step so the progress bar shows 100% before we leave.
    // reset() is NOT called here — doing so drops step to 1 while StepGuard is still
    // mounted, causing a redirect to step-1 that races and wins over push('/chat').
    // The app layout's OnboardingCleanup component resets the store after arrival.
    setStep(TOTAL_ONBOARDING_STEPS + 1)
    setTimeout(() => {
      router.push('/chat')
    }, 350)
  }

  function retry() {
    setFailed(false)
    // Re-arm the 8-second failsafe for the retry attempt
    clearTimeout(failTimerRef.current!)
    failTimerRef.current = setTimeout(() => {
      if (mountedRef.current) setFailed(true)
    }, 8000)
    persist()
  }

  useEffect(() => {
    const startTimer = setTimeout(() => persist(), 400)
    failTimerRef.current = setTimeout(() => {
      if (mountedRef.current) setFailed(true)
    }, 8000)
    return () => { clearTimeout(startTimer); clearTimeout(failTimerRef.current!) }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (failed) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-sm text-[var(--color-text-secondary)]">
          We&apos;re having trouble setting things up — tap to try again.
        </p>
        <button
          onClick={retry}
          className="min-h-[44px] text-sm text-[var(--color-primary)] underline px-4"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="h-16 w-16 rounded-full bg-[var(--color-surface-tinted)] animate-pulse" />
      <p className="text-sm text-[var(--color-text-secondary)]">
        Personalising your experience…
      </p>
    </div>
  )
}
