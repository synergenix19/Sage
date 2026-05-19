import { describe, it, expect, beforeEach } from 'vitest'
import { useOnboardingStore } from '../onboarding-store'

describe('useOnboardingStore', () => {
  beforeEach(() => useOnboardingStore.getState().reset())

  it('starts at step 1', () => {
    expect(useOnboardingStore.getState().step).toBe(1)
  })

  it('setAnswer updates a single answer field', () => {
    useOnboardingStore.getState().setAnswer('name', 'Fatima')
    expect(useOnboardingStore.getState().answers.name).toBe('Fatima')
  })

  it('setAnswer does not overwrite other fields', () => {
    useOnboardingStore.getState().setAnswer('name', 'Fatima')
    useOnboardingStore.getState().setAnswer('wellnessQ1', 'Stress')
    expect(useOnboardingStore.getState().answers.name).toBe('Fatima')
    expect(useOnboardingStore.getState().answers.wellnessQ1).toBe('Stress')
  })

  it('reset clears all answers and resets step', () => {
    useOnboardingStore.getState().setAnswer('name', 'Fatima')
    useOnboardingStore.getState().setStep(4)
    useOnboardingStore.getState().reset()
    expect(useOnboardingStore.getState().answers.name).toBe('')
    expect(useOnboardingStore.getState().step).toBe(1)
  })
})
