import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Locale, AgeRange, UserRole } from '@cdai/types'

interface OnboardingAnswers {
  locale: Locale | null
  name: string
  ageRange: AgeRange | null
  role: UserRole | null
  wellnessQ1: string
  wellnessQ2: string
}

interface OnboardingStore {
  step: number
  answers: OnboardingAnswers
  setStep: (step: number) => void
  setAnswer: <K extends keyof OnboardingAnswers>(key: K, value: OnboardingAnswers[K]) => void
  reset: () => void
}

const defaultAnswers: OnboardingAnswers = {
  locale: null, name: '', ageRange: null,
  role: null, wellnessQ1: '', wellnessQ2: '',
}

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set) => ({
      step: 1,
      answers: defaultAnswers,
      setStep: (step) => set({ step }),
      setAnswer: (key, value) =>
        set((s) => ({ answers: { ...s.answers, [key]: value } })),
      reset: () => set({ step: 1, answers: defaultAnswers }),
    }),
    { name: 'cdai-onboarding' }
  )
)
