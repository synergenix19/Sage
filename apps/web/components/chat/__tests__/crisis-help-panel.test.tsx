import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CrisisHelpPanel } from '../crisis-help-panel'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CRISIS_CONFIG } from '@/lib/crisis-config'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

// Safety property (spec): the persistent "Get help now" affordance renders the resource list
// ENTIRELY client-side — never a server round-trip. We hard-fail any fetch to prove it: a user
// reaching for help while the backend is slow/down must still get dialable numbers.
describe('CrisisHelpPanel — deterministic, offline-capable (no server round-trip)', () => {
  let getHoursSpy: ReturnType<typeof vi.spyOn>
  beforeEach(() => {
    // Pin the clock to NOON so the hours-aware lead-logic is deterministic: the National line
    // (8am-8pm) is open and inline in the top-3. Without this the national tel would be behind the
    // "More options" expander at night, making these assertions clock-dependent.
    getHoursSpy = vi.spyOn(Date.prototype, 'getHours').mockReturnValue(12)
    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        throw new Error('CrisisHelpPanel must NOT hit the network — it renders from the static array')
      }),
    )
  })

  afterEach(() => {
    getHoursSpy.mockRestore()
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en', setLocale: () => {} }))
  })

  it('renders nothing when closed', () => {
    const { container } = render(<CrisisHelpPanel open={false} onClose={() => {}} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders working tel: links with the API killed (fetch throws), without ever calling fetch', () => {
    render(<CrisisHelpPanel open onClose={() => {}} />)
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.tel)).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.emergencyTel)).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('is bilingual — renders localized Arabic labels and title when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar', setLocale: () => {} }))
    render(<CrisisHelpPanel open onClose={() => {}} />)
    expect(screen.getByText('احصل على المساعدة الآن')).toBeInTheDocument()
    expect(screen.getByText('خط الدعم النفسي الوطني')).toBeInTheDocument()
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === CRISIS_CONFIG.tel)).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
  })
})
