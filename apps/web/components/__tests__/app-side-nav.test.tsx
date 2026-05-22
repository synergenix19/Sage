import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppSideNav } from '../app-side-nav'

// --- Mocks ---

vi.mock('next/link', () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}))
vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('@cdai/tenant', () => ({
  tenant: {
    copy: { appName: 'Sage by CDA' },
    capabilities: { voiceBiomarker: false },
  },
}))
vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
}))
vi.mock('@/components/auth/language-toggle', () => ({
  LanguageToggle: () => <button>EN/AR</button>,
}))

const mockSignOutUser = vi.fn().mockResolvedValue(undefined)
vi.mock('@/lib/auth-actions', () => ({
  signOutUser: (...args: Parameters<typeof mockSignOutUser>) => mockSignOutUser(...args),
}))

const mockGetUser = vi.fn().mockResolvedValue({
  data: { user: { email: 'test@example.com' } },
})
vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: { getUser: mockGetUser },
  }),
}))

// --- Tests ---

describe('AppSideNav — nav links', () => {
  it('renders the app name', async () => {
    render(<AppSideNav />)
    expect(screen.getByText('Sage by CDA')).toBeInTheDocument()
  })

  it('renders Chat and Progress nav links', async () => {
    render(<AppSideNav />)
    expect(screen.getByRole('link', { name: 'Chat' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Progress' })).toBeInTheDocument()
  })

  it('does not render Voice link when voiceBiomarker is disabled', async () => {
    render(<AppSideNav />)
    expect(screen.queryByRole('link', { name: 'Voice' })).not.toBeInTheDocument()
  })

  it('marks the active route link', async () => {
    render(<AppSideNav />)
    // usePathname returns '/chat', so Chat link should have active styling
    const chatLink = screen.getByRole('link', { name: 'Chat' })
    expect(chatLink.className).toMatch(/bg-\[var\(--color-primary\)\]/)
  })
})

describe('AppSideNav — user identity', () => {
  it('shows the first letter of the user email as avatar initial', async () => {
    render(<AppSideNav />)
    await waitFor(() => {
      expect(screen.getByText('T')).toBeInTheDocument() // first letter of 'test@example.com'
    })
  })

  it('shows the user email', async () => {
    render(<AppSideNav />)
    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument()
    })
  })
})

describe('AppSideNav — sign-out confirmation', () => {
  beforeEach(() => {
    mockSignOutUser.mockClear()
  })

  it('does not show confirmation by default', () => {
    render(<AppSideNav />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows confirmation when sign-out icon button is clicked', async () => {
    render(<AppSideNav />)
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('hides confirmation when Cancel is clicked', async () => {
    render(<AppSideNav />)
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('hides confirmation when Escape is pressed', async () => {
    render(<AppSideNav />)
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('calls signOutUser when Sign out confirmation button is clicked', async () => {
    render(<AppSideNav />)
    // Open confirmation (trigger button disappears once dialog is shown)
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    // "Sign out" now refers to the confirmation button — trigger is no longer rendered
    fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    await waitFor(() => {
      expect(mockSignOutUser).toHaveBeenCalled()
    })
  })
})

describe('AppSideNav — keyboard accessibility', () => {
  it('moves focus to Cancel button when confirmation opens', async () => {
    render(<AppSideNav />)
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /sign out/i }))
    })
    await waitFor(() => {
      expect(document.activeElement).toBe(screen.getByRole('button', { name: /cancel/i }))
    })
  })
})
