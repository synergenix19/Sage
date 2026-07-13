import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CrisisCard } from '../crisis-card'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CRISIS_CONFIG, CRISIS_RESOURCES } from '@/lib/crisis-config'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

// Pin the wall clock to NOON so the hours-aware lead-logic is deterministic: at noon the National
// line (8am-8pm) is open and leads, so it is inline in the top-3 alongside 999 and a 24/7 line. The
// component reads only `new Date().getHours()`, so spying that keeps timers/React untouched.
let getHoursSpy: ReturnType<typeof vi.spyOn>
beforeEach(() => {
  getHoursSpy = vi.spyOn(Date.prototype, 'getHours').mockReturnValue(12)
})
afterEach(() => {
  getHoursSpy.mockRestore()
})

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
    // Doc composition (6 entries) → top-3 inline, the remaining sit behind "More options".
    expect(list!.querySelectorAll('li').length).toBe(3)
    expect(CRISIS_RESOURCES.length).toBeGreaterThan(3)
    expect(screen.getByText(/More options/i)).toBeInTheDocument()
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

  it('top-3 invariant: 999 and a 24/7 line are inline; extra resources sit behind "More options"', () => {
    render(<CrisisCard content="Test." />)
    const links = screen.getAllByRole('link')
    // The 6-entry doc composition DOES show a "More options" expander. The National line is 8am-8pm,
    // so the guaranteed-inline anchors are 999 + a distinct 24/7 line (never hidden by the expander).
    expect(screen.getByText(/More options/i)).toBeInTheDocument()
    // At noon (mocked) the National line is open, so its tel is inline too.
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
    expect(screen.getByText('خط الدعم النفسي الوطني')).toBeInTheDocument()
    expect(screen.getByText('خدمات الطوارئ')).toBeInTheDocument()
  })

  it('wraps the Latin number in <span dir="ltr"> inside the RTL call button', () => {
    useArabic()
    const { container } = render(<CrisisCard content="أنت لست وحدك." />)
    const ltrSpans = Array.from(container.querySelectorAll('span[dir="ltr"]'))
    // The National line number "800-HOPE (800-4673)" must be LTR-wrapped so it never bidi-reverses.
    expect(ltrSpans.some((s) => s.textContent === '800-HOPE (800-4673)')).toBe(true)
    expect(ltrSpans.some((s) => s.textContent === '999')).toBe(true)
  })
})
