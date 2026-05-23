import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TypingIndicator } from '../typing-indicator'
import { useLocaleStore } from '@/lib/stores/locale-store'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en' })),
}))

describe('TypingIndicator', () => {
  it('has role="status" so screen readers announce it', () => {
    render(<TypingIndicator />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('has an English aria-label when locale is en', () => {
    render(<TypingIndicator />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Sage is typing...')
  })
})

describe('TypingIndicator — Arabic locale', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en' }))
  })

  it('has an Arabic aria-label when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar' }))
    render(<TypingIndicator />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', '...Sage يكتب')
  })
})
