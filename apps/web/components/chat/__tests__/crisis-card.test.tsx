import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CrisisCard } from '../crisis-card'

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
}))

describe('CrisisCard', () => {
  it('has role="alert" so screen readers announce it immediately', () => {
    render(<CrisisCard content="You are not alone." />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
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
