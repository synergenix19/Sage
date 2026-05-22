import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { StepGuard } from '../step-guard'

const { mockReplace } = vi.hoisted(() => ({ mockReplace: vi.fn() }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace: mockReplace }) }))

let mockStep = 1
vi.mock('@/lib/stores/onboarding-store', () => ({
  useOnboardingStore: (sel: (s: { step: number }) => number) => sel({ step: mockStep }),
}))

describe('StepGuard', () => {
  beforeEach(() => {
    mockReplace.mockClear()
    mockStep = 1
  })

  it('renders children without redirecting when storedStep equals pageStep', () => {
    mockStep = 3
    const { getByText } = render(
      <StepGuard pageStep={3}><div>content</div></StepGuard>
    )
    expect(getByText('content')).toBeTruthy()
    expect(mockReplace).not.toHaveBeenCalled()
  })

  it('redirects backward navigator to storedStep when storedStep > pageStep', () => {
    mockStep = 5
    render(<StepGuard pageStep={2}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-5')
  })

  it('caps backward redirect at step 6', () => {
    mockStep = 8
    render(<StepGuard pageStep={1}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-6')
  })

  it('redirects forward-skipper to storedStep when storedStep < pageStep', () => {
    mockStep = 2
    render(<StepGuard pageStep={5}><div /></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-2')
  })

  it('does not redirect when storedStep equals pageStep', () => {
    mockStep = 1
    render(<StepGuard pageStep={1}><div /></StepGuard>)
    expect(mockReplace).not.toHaveBeenCalled()
  })
})
