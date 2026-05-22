'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export function StepGuard({ pageStep, children }: { pageStep: number; children: React.ReactNode }) {
  const storedStep = useOnboardingStore((s) => s.step)
  const router = useRouter()

  useEffect(() => {
    if (storedStep > pageStep) {
      router.replace(`/step-${Math.min(storedStep, 6)}`)
    } else if (storedStep < pageStep) {
      router.replace(`/step-${Math.max(storedStep, 1)}`)
    }
  }, [storedStep, pageStep, router])

  return <>{children}</>
}
