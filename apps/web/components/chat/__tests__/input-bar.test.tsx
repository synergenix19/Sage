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

describe('InputBar — QW4 placeholder & mic icon', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en' }))
  })

  it('shows the warmer English placeholder', () => {
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByPlaceholderText("What's on your mind?")).toBeInTheDocument()
  })

  it('shows the gender-neutral Khaleeji placeholder when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar' }))
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByPlaceholderText('وش في البال؟')).toBeInTheDocument()
  })

  it('renders the voice button as an SVG icon, not the raw emoji', () => {
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    expect(btn.querySelector('svg')).not.toBeNull()
    expect(btn.textContent ?? '').not.toContain('🎙')
  })
})

describe('InputBar — QW4 honest voice affordance', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).SpeechRecognition
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).webkitSpeechRecognition
  })

  it('disables the voice button with a "coming soon" title when unsupported', async () => {
    // jsdom has no SpeechRecognition by default
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    await vi.waitFor(() => expect(btn).toBeDisabled())
    expect(btn).toHaveAttribute('title', expect.stringMatching(/coming soon/i))
  })

  it('enables the voice button when SpeechRecognition is available', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(window as any).SpeechRecognition = vi.fn()
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    await vi.waitFor(() => expect(btn).toBeEnabled())
  })
})
