import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InputBar } from '../input-bar'

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
}))

describe('InputBar accessibility', () => {
  it('textarea has an accessible name', () => {
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByRole('textbox', { name: 'Message' })).toBeInTheDocument()
  })

  it('voice button has aria-label in English', () => {
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Voice input' })).toBeInTheDocument()
  })

  it('voice button has aria-pressed=false by default', () => {
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    expect(btn).toHaveAttribute('aria-pressed', 'false')
  })

  it('send button is present', () => {
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument()
  })
})
