'use client'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button } from '@cdai/ui'
import { tenant } from '@cdai/tenant'

export function Welcome() {
  const { setStep } = useOnboardingStore()
  const router = useRouter()

  function next() {
    setStep(2)
    router.push('/onboarding/step-2')
  }

  return (
    <div className="flex flex-col items-center gap-8 text-center">
      <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-16 w-16" />
      <div>
        <h1 className="text-2xl font-semibold">{tenant.copy.onboardingGreeting}</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{tenant.copy.tagline}</p>
      </div>
      <Button onClick={next} size="lg" className="w-full">Get started</Button>
    </div>
  )
}
