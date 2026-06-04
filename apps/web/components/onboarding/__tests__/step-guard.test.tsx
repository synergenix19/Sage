import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { StepGuard } from '../step-guard'

const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}))

const mockStep = vi.fn()
vi.mock('@/lib/stores/onboarding-store', () => {
  const useOnboardingStore = (selector: (s: { step: number }) => unknown) =>
    selector({ step: mockStep() })
  useOnboardingStore.persist = {
    hasHydrated: () => true,
    onFinishHydration: () => () => {},
  }
  return { useOnboardingStore }
})

describe('StepGuard', () => {
  beforeEach(() => {
    mockStep.mockReturnValue(1)
    mockReplace.mockClear()
  })

  it('renders children when stored step matches page step', () => {
    const { getByText } = render(
      <StepGuard pageStep={1}><p>content</p></StepGuard>
    )
    expect(getByText('content')).toBeTruthy()
  })

  it('returns null when stored step is ahead of page step', () => {
    mockStep.mockReturnValue(3)
    const { container } = render(
      <StepGuard pageStep={1}><p>content</p></StepGuard>
    )
    expect(container.firstChild).toBeNull()
  })

  it('returns null when stored step is behind page step', () => {
    mockStep.mockReturnValue(1)
    const { container } = render(
      <StepGuard pageStep={3}><p>content</p></StepGuard>
    )
    expect(container.firstChild).toBeNull()
  })

  it('redirects forward when stored step is ahead of page step', () => {
    mockStep.mockReturnValue(3)
    render(<StepGuard pageStep={1}><p>content</p></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-3')
  })

  it('caps forward redirect at step 6', () => {
    mockStep.mockReturnValue(10)
    render(<StepGuard pageStep={1}><p>content</p></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-6')
  })

  it('redirects back when stored step is behind page step', () => {
    mockStep.mockReturnValue(1)
    render(<StepGuard pageStep={3}><p>content</p></StepGuard>)
    expect(mockReplace).toHaveBeenCalledWith('/step-1')
  })
})
