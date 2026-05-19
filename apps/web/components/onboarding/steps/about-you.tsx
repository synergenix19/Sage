'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button, cn } from '@cdai/ui'
import type { AgeRange, UserRole } from '@cdai/types'

const AGE_RANGES: AgeRange[] = ['under-18', '18-24', '25-34', '35-44', '45-54', '55+']
const ROLES: { label: string; value: UserRole }[] = [
  { label: 'Parent / Guardian', value: 'parent' },
  { label: 'CDA Service User', value: 'service_user' },
  { label: 'Professional', value: 'professional' },
]

export function AboutYou() {
  const { setAnswer, setStep } = useOnboardingStore()
  const [age, setAge] = useState<AgeRange | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const router = useRouter()

  function next() {
    if (!age || !role) return
    setAnswer('ageRange', age)
    setAnswer('role', role)
    setStep(5)
    router.push('/onboarding/step-5')
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-semibold">Tell us a little about you</h2>
      <div>
        <p className="mb-2 text-sm text-[var(--color-text-secondary)]">Age range</p>
        <div className="flex flex-wrap gap-2">
          {AGE_RANGES.map((a) => (
            <button
              key={a}
              onClick={() => setAge(a)}
              className={cn(
                'min-h-[44px] rounded-full border px-4 py-2 text-sm transition-colors duration-200',
                age === a
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                  : 'border-[var(--color-border)] hover:border-[var(--color-primary)]'
              )}
            >
              {a}
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 text-sm text-[var(--color-text-secondary)]">I am a</p>
        <div className="flex flex-col gap-2">
          {ROLES.map((r) => (
            <button
              key={r.value}
              onClick={() => setRole(r.value)}
              className={cn(
                'min-h-[44px] rounded-xl border px-4 py-3 text-start text-sm transition-colors duration-200',
                role === r.value
                  ? 'border-[var(--color-primary)] bg-[var(--color-surface-tinted)]'
                  : 'border-[var(--color-border)] hover:border-[var(--color-primary)]'
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <Button onClick={next} disabled={!age || !role} size="lg" className="w-full">
        Continue
      </Button>
    </div>
  )
}
