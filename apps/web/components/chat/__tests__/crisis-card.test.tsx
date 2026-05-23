import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CrisisCard } from '../crisis-card'
import { useLocaleStore } from '@/lib/stores/locale-store'

vi.mock('@/lib/stores/locale-store', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en', setLocale: () => {} })),
}))

describe('CrisisCard', () => {
  it('has role="alert" on the outermost container', () => {
    const { container } = render(<CrisisCard content="You are not alone." />)
    expect(container.firstChild).toHaveAttribute('role', 'alert')
    expect(container.firstChild).toHaveAttribute('aria-atomic', 'true')
  })

  it('renders the content text inside the alert', () => {
    render(<CrisisCard content="Support is available now." />)
    expect(screen.getByText('Support is available now.')).toBeInTheDocument()
  })

  it('renders the UAE counselling call link', () => {
    render(<CrisisCard content="Test." />)
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === 'tel:800-46342')).toBe(true)
  })

  it('renders the emergency call link', () => {
    render(<CrisisCard content="Test." />)
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === 'tel:999')).toBe(true)
  })
})

describe('CrisisCard — Arabic locale', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en', setLocale: () => {} }))
  })

  it('renders Arabic heading and both call links', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar', setLocale: () => {} }))
    render(<CrisisCard content="أنت لست وحدك." />)
    expect(screen.getByText('لست وحدك — الدعم متاح')).toBeInTheDocument()
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href') === 'tel:800-46342')).toBe(true)
    expect(links.some((l) => l.getAttribute('href') === 'tel:999')).toBe(true)
  })
})
