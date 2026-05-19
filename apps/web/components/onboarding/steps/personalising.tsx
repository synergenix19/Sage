'use client'
import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { createClient } from '@/lib/supabase/client'

export function Personalising() {
  const { answers, reset } = useOnboardingStore()
  const [failed, setFailed] = useState(false)
  const router = useRouter()
  const failTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  async function persist() {
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
      onboarding_step: 6,
    })

    if (error) { setFailed(true); return }
    // Clear the fail timer before navigating — prevents setFailed on an unmounted component
    clearTimeout(failTimerRef.current!)
    reset()
    router.push('/chat')
  }

  useEffect(() => {
    const startTimer = setTimeout(() => persist(), 400)
    failTimerRef.current = setTimeout(() => setFailed(true), 8000)
    return () => { clearTimeout(startTimer); clearTimeout(failTimerRef.current!) }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (failed) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-sm text-[var(--color-text-secondary)]">
          We&apos;re having trouble setting things up — tap to try again.
        </p>
        <button
          onClick={() => { setFailed(false); persist() }}
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
        Personalising your experience&hellip;
      </p>
    </div>
  )
}
