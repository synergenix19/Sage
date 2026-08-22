import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CrisisHelpPanel } from '../crisis-help-panel'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CRISIS_CONFIG } from '@/lib/crisis-config'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

// P4-1 (A11Y-4/5/11 promotion, task 7): "one tap away, no gates" property. A focus trap is exactly
// the well-intentioned mechanism that can accidentally lock a distressed user OUT of the very
// content it wraps. This suite asserts the trap promoted from AppSideNav into
// ResponsivePanel/BottomSheet does NOT impede (a) closing the crisis help panel — Escape AND the
// close button, both reachable/operable — or (b) reaching the helpline tel: links inside the trap.
// It renders CrisisHelpPanel exactly as shipped (through ResponsivePanel, unmodified) — no crisis
// file is edited by this change; only the shared panel plumbing underneath it.
describe('CrisisHelpPanel — focus trap does not gate closing or reaching the helpline (A11Y-4/5/11)', () => {
  let getHoursSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    // Pin to noon, matching the sibling suite, so the National line is inline (not behind the
    // "More options" expander) and tab-order assertions are not clock-dependent.
    getHoursSpy = vi.spyOn(Date.prototype, 'getHours').mockReturnValue(12)
    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        throw new Error('CrisisHelpPanel must NOT hit the network')
      }),
    )
  })

  afterEach(() => {
    getHoursSpy.mockRestore()
    vi.unstubAllGlobals()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en', setLocale: () => {} }))
  })

  it('Escape closes the panel (calls onClose) even while focus is inside the trap', async () => {
    const onClose = vi.fn()
    render(<CrisisHelpPanel open onClose={onClose} />)
    const dialog = screen.getByRole('dialog')
    // Move focus into the trap before dismissing, so this proves Escape works FROM inside it.
    const telLink = screen.getAllByRole('link').find((l) => l.getAttribute('href') === CRISIS_CONFIG.tel)!
    telLink.focus()
    expect(dialog.contains(document.activeElement)).toBe(true)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('the close button receives initial focus (first tab stop) inside the trap and is operable', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<CrisisHelpPanel open onClose={onClose} />)
    const closeButton = screen.getByRole('button', { name: 'Close' })
    const dialog = screen.getByRole('dialog')
    expect(dialog.contains(closeButton)).toBe(true)

    // The trap places initial focus on the close button directly (it is the first focusable
    // element in DOM order) — no Tab press needed to reach it, no gate in front of it.
    expect(document.activeElement).toBe(closeButton)

    await user.keyboard('{Enter}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Tab order inside the trap reaches every dialable helpline link — nothing is stranded unreachable', async () => {
    const user = userEvent.setup()
    render(<CrisisHelpPanel open onClose={() => {}} />)
    const dialog = screen.getByRole('dialog')
    const telLinks = screen
      .getAllByRole('link')
      .filter((l) => (l.getAttribute('href') ?? '').startsWith('tel:'))
    expect(telLinks.length).toBeGreaterThan(0) // sanity: the property under test is non-vacuous

    // Tab through the whole dialog (generously bounded) and record every element focus visits.
    const visited = new Set<Element>()
    const maxTabs = 25
    for (let i = 0; i < maxTabs; i++) {
      await user.tab()
      const active = document.activeElement
      if (!active || active === document.body) break
      visited.add(active)
    }

    for (const link of telLinks) {
      expect(visited.has(link)).toBe(true)
    }
    // Reachability without escape: every focused element stayed inside the dialog the whole time.
    for (const el of visited) {
      expect(dialog.contains(el)).toBe(true)
    }
  })

  it('Tab cycles within the dialog (loops back to the start) instead of leaking focus to the obscured page behind the backdrop', async () => {
    const user = userEvent.setup()
    render(<CrisisHelpPanel open onClose={() => {}} />)
    const dialog = screen.getByRole('dialog')
    const closeButton = screen.getByRole('button', { name: 'Close' })

    // Initial focus is already the close button (first focusable element in the dialog).
    expect(document.activeElement).toBe(closeButton)

    // Tab exactly `focusableCount` times from the first element: never leaks outside the dialog
    // mid-cycle, and lands back on the close button — proving the wrap-around, not just a trap.
    const focusableCount = dialog.querySelectorAll('a[href], button:not([disabled])').length
    for (let i = 0; i < focusableCount; i++) {
      await user.tab()
      expect(dialog.contains(document.activeElement)).toBe(true)
    }
    expect(document.activeElement).toBe(closeButton)
  })

  it('initial focus lands inside the dialog on open (no orphaned focus on the obscured page)', () => {
    render(<CrisisHelpPanel open onClose={() => {}} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog.contains(document.activeElement)).toBe(true)
  })
})
