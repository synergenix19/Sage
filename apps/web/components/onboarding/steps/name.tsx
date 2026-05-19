'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button, Input } from '@cdai/ui'

export function Name() {
  const { answers, setAnswer, setStep } = useOnboardingStore()
  const [value, setValue] = useState(answers.name)
  const router = useRouter()

  function next() {
    if (!value.trim()) return
    setAnswer('name', value.trim())
    setStep(4)
    router.push('/onboarding/step-4')
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-semibold">What should we call you?</h2>
      <Input
        placeholder="Your name"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && next()}
        autoFocus
      />
      <Button onClick={next} disabled={!value.trim()} size="lg" className="w-full">
        Continue
      </Button>
    </div>
  )
}
