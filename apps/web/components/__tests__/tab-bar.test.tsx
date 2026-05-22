import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TabBar, ALL_TABS } from '../tab-bar'

vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
}))
vi.mock('next/link', () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}))
vi.mock('@cdai/tenant', () => ({
  tenant: { capabilities: { voiceBiomarker: false } },
}))
vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
}))

describe('TabBar', () => {
  it('applies a custom className to the nav element', () => {
    render(<TabBar className="md:hidden" />)
    expect(screen.getByRole('navigation')).toHaveClass('md:hidden')
  })

  it('renders without className when none provided', () => {
    render(<TabBar />)
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })
})

describe('ALL_TABS', () => {
  it('includes Chat and Progress tabs', () => {
    const hrefs = ALL_TABS.map((t) => t.href)
    expect(hrefs).toContain('/chat')
    expect(hrefs).toContain('/progress')
  })
})
