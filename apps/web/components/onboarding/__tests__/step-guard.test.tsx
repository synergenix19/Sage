import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { StepGuard } from '../step-guard'

const { mockReplace, stepRef } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
  stepRef: { value: 1 },
}))

vi.mock('next/navigation', () => ({ useRouter: () => ({ replace: mockReplace }) }))

vi.mock('@/lib/stores/onboarding-store', () => ({
  useOnboardingStore: (sel: (s: { step: number }) => number) => sel({ step: stepRef.value }),
}))

describe('StepGuard', () => {
  beforeEach(() => {
    mockReplace.mockClear()
    stepRef.value = 1
  })

  it('renders children without redirecting when storedStep equals pageStep', () => {
    stepRef.value = 3
    const { getByText } = render(
      <StepGuard pageStep={3}><div>content</div></StepGuard>
    )
    expect(getByText('content')).toBeTruthy()
    expect(mockReplace).not.toHaveBeenCalled()
  })

  it('redirects backward navigator to storedStep when storedStep > pageStep', () => {
    stepRef.value = 5
    render(<StepGuard pageStep={2}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-5')
  })

  it('caps backward redirect at step 6', () => {
    stepRef.value = 8
    render(<StepGuard pageStep={1}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-6')
  })

  it('redirects forward-skipper to storedStep when storedStep < pageStep', () => {
    stepRef.value = 2
    render(<StepGuard pageStep={5}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-2')
  })

  it('does not redirect when storedStep equals pageStep', () => {
    stepRef.value = 1
    render(<StepGuard pageStep={1}><div /></StepGuard>)
    expect(mockReplace).not.toHaveBeenCalled()
  })
})
