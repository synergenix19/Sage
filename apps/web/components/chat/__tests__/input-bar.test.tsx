import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InputBar } from '../input-bar'
import { useLocaleStore } from '@/lib/stores/locale-store'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en' })),
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

describe('InputBar — Arabic locale', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en' }))
  })

  it('textarea has Arabic accessible name when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar' }))
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByRole('textbox', { name: 'اكتب رسالتك' })).toBeInTheDocument()
  })

  it('voice button has Arabic aria-label when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar' }))
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'الإدخال الصوتي' })).toBeInTheDocument()
  })

  it('send button has Arabic aria-label when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar' }))
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'إرسال' })).toBeInTheDocument()
  })
})
