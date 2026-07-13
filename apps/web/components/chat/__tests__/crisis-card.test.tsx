import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CrisisCard } from '../crisis-card'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CRISIS_CONFIG, CRISIS_RESOURCES } from '@/lib/crisis-config'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

describe('CrisisCard', () => {
  it('has role="alert" and aria-atomic on the outermost container', () => {
    const { container } = render(<CrisisCard content="You are not alone." />)
    expect(container.firstChild).toHaveAttribute('role', 'alert')
    expect(container.firstChild).toHaveAttribute('aria-atomic', 'true')
  })

  it('renders the content text inside the alert', () => {
    render(<CrisisCard content="Support is available now." />)
    expect(screen.getByText('Support is available now.')).toBeInTheDocument()
  })

  it('renders the resources as an ordered list (.map), one <li> per inline resource', () => {
    const { container } = render(<CrisisCard content="Test." />)
    const list = container.querySelector('ol')
    expect(list).not.toBeNull()
    // Current production array is 2 entries; both fit inline (no expander needed).
    expect(list!.querySelectorAll('li').length).toBe(CRISIS_RESOURCES.length)
  })

  it('renders the UAE counselling call link (tel:)', () => {
    render(<CrisisCard content="Test." />)
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.tel)).toBe(true)
  })

  it('renders the emergency (999) call link — the always-present 24/7 line', () => {
    render(<CrisisCard content="Test." />)
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.emergencyTel)).toBe(true)
  })

  it('top-3 invariant: both 999 and the 24/7 national line are inline (not behind an expander)', () => {
    render(<CrisisCard content="Test." />)
    const links = screen.getAllByRole('link')
    // No "More options" expander with the current 2-entry array.
    expect(screen.queryByText(/More options/i)).not.toBeInTheDocument()
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.tel)).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.emergencyTel)).toBe(true)
  })

  it('every call button meets the 44px touch-target minimum', () => {
    render(<CrisisCard content="Test." />)
    const callLinks = screen
      .getAllByRole('link')
      .filter((l) => l.getAttribute('href')?.startsWith('tel:'))
    expect(callLinks.length).toBeGreaterThanOrEqual(2)
    for (const l of callLinks) expect(l.className).toMatch(/min-h-\[44px\]/)
  })
})

describe('CrisisCard — Arabic locale (bilingual + RTL number handling)', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en', setLocale: () => {} }))
  })

  function useArabic() {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar', setLocale: () => {} }))
  }

  it('renders the Arabic heading and both call links', () => {
    useArabic()
    render(<CrisisCard content="أنت لست وحدك." />)
    expect(screen.getByText('لست وحدك — الدعم متاح')).toBeInTheDocument()
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.tel)).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.emergencyTel)).toBe(true)
  })

  it('renders localized Arabic resource labels', () => {
    useArabic()
    render(<CrisisCard content="أنت لست وحدك." />)
    expect(screen.getByText('خط وزارة الصحة للدعم النفسي')).toBeInTheDocument()
    expect(screen.getByText('خدمات الطوارئ')).toBeInTheDocument()
  })

  it('wraps the Latin number in <span dir="ltr"> inside the RTL call button', () => {
    useArabic()
    const { container } = render(<CrisisCard content="أنت لست وحدك." />)
    const ltrSpans = Array.from(container.querySelectorAll('span[dir="ltr"]'))
    // The MoHAP number "800 46342" must be LTR-wrapped so it never bidi-reverses inside Arabic.
    expect(ltrSpans.some((s) => s.textContent === '800 46342')).toBe(true)
    expect(ltrSpans.some((s) => s.textContent === '999')).toBe(true)
  })
})
