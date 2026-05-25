'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button, cn } from '@cdai/ui'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'

const Q1_OPTIONS = ['Managing stress', 'Parenting challenges', 'Work-life balance', 'Grief or loss', 'Anxiety', 'Relationships']
const Q2_OPTIONS = ['Someone to talk to', 'Practical tools & tips', 'Understanding my emotions', 'Crisis support']

export function WhatMatters() {
  const { setAnswer, setStep } = useOnboardingStore()
  const [q1, setQ1] = useState('')
  const [q2, setQ2] = useState('')
  const router = useRouter()

  function next() {
    if (!q1 || !q2) return
    setAnswer('wellnessQ1', q1)
    setAnswer('wellnessQ2', q2)
    setStep(TOTAL_ONBOARDING_STEPS)
    router.push(`/step-${TOTAL_ONBOARDING_STEPS}`)
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-semibold">What brings you here?</h2>
      <div className="flex flex-wrap gap-2">
        {Q1_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => setQ1(opt)}
            className={cn(
              'min-h-[44px] rounded-full border px-4 py-2 text-sm transition-colors duration-200',
              q1 === opt
                ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                : 'border-[var(--color-border)]'
            )}
          >
            {opt}
          </button>
        ))}
      </div>
      <p className="text-sm text-[var(--color-text-secondary)]">What would help most?</p>
      <div className="flex flex-col gap-2">
        {Q2_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => setQ2(opt)}
            className={cn(
              'min-h-[44px] rounded-xl border px-4 py-3 text-start text-sm transition-colors duration-200',
              q2 === opt
                ? 'border-[var(--color-primary)] bg-[var(--color-surface-tinted)]'
                : 'border-[var(--color-border)]'
            )}
          >
            {opt}
          </button>
        ))}
      </div>
      <Button onClick={next} disabled={!q1 || !q2} size="lg" className="w-full">
        Continue
      </Button>
    </div>
  )
}
