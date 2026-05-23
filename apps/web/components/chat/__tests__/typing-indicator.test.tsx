import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TypingIndicator } from '../typing-indicator'

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
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
