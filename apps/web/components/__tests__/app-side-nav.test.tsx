import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppSideNav } from '../app-side-nav'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'

// --- Mocks ---

const mockPush = vi.fn()
const mockRefresh = vi.fn()

vi.mock('next/link', () => ({
  default: ({ href, children, className, 'aria-current': ariaCurrent }: { href: string; children: React.ReactNode; className?: string; 'aria-current'?: string }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>{children}</a>
  ),
}))
vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams('session=sess-1'),
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

vi.mock('@/lib/hooks/use-chat-sessions', () => ({
  useChatSessions: vi.fn(),
}))

vi.mock('@/lib/format-relative-time', () => ({
  formatRelativeTime: () => '2h ago',
}))

// --- Tests ---

beforeEach(() => {
  mockPush.mockClear()
  mockRefresh.mockClear()
  vi.mocked(useChatSessions).mockReturnValue({
    sessions: [
      { id: 'sess-1', title: 'Feeling stressed lately', updated_at: '2026-05-23T10:00:00Z' },
      { id: 'sess-2', title: 'Anxiety about work', updated_at: '2026-05-22T09:00:00Z' },
    ],
    loading: false,
    error: null,
    refresh: mockRefresh,
  })
})

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

describe('AppSideNav — new conversation button', () => {
  it('renders the "+ New conversation" button', async () => {
    render(<AppSideNav />)
    expect(
      screen.getByRole('button', { name: /new conversation/i })
    ).toBeInTheDocument()
  })

  it('navigates to /chat?new=... when button is clicked', async () => {
    render(<AppSideNav />)
    fireEvent.click(screen.getByRole('button', { name: /new conversation/i }))
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringMatching(/^\/chat\?new=\d+-[a-z0-9]+$/)
    )
  })
})

describe('AppSideNav — session list', () => {
  it('renders session titles from useChatSessions', async () => {
    render(<AppSideNav />)
    await waitFor(() => {
      expect(screen.getByText('Feeling stressed lately')).toBeInTheDocument()
      expect(screen.getByText('Anxiety about work')).toBeInTheDocument()
    })
  })

  it('shows "Untitled conversation" for null title session', async () => {
    vi.mocked(useChatSessions).mockReturnValue({
      sessions: [{ id: 's3', title: null, updated_at: '2026-05-21T10:00:00Z' }],
      loading: false,
      error: null,
      refresh: mockRefresh,
    })
    render(<AppSideNav />)
    await waitFor(() => {
      expect(screen.getByText('Untitled conversation')).toBeInTheDocument()
    })
  })

  it('applies active styling to the session matching ?session= param', async () => {
    // useSearchParams mock returns 'session=sess-1'
    render(<AppSideNav />)
    await waitFor(() => {
      const activeLink = screen.getByRole('link', { name: /feeling stressed lately/i })
      expect(activeLink).toHaveAttribute('aria-current', 'page')
    })
  })

  it('renders session items as links to /chat?session=<id>', async () => {
    render(<AppSideNav />)
    await waitFor(() => {
      const link = screen.getByRole('link', { name: /feeling stressed lately/i })
      expect(link).toHaveAttribute('href', '/chat?session=sess-1')
    })
  })

  it('shows relative timestamps', async () => {
    render(<AppSideNav />)
    await waitFor(() => {
      // formatRelativeTime is mocked to return '2h ago'
      expect(screen.getAllByText('2h ago').length).toBeGreaterThan(0)
    })
  })
})

describe('AppSideNav — session list states', () => {
  it('shows loading text when loading=true', async () => {
    vi.mocked(useChatSessions).mockReturnValue({
      sessions: [],
      loading: true,
      error: null,
      refresh: mockRefresh,
    })
    render(<AppSideNav />)
    await waitFor(() => {
      expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })
  })

  it('shows error state with retry button', async () => {
    vi.mocked(useChatSessions).mockReturnValue({
      sessions: [],
      loading: false,
      error: 'Failed to load',
      refresh: mockRefresh,
    })
    render(<AppSideNav />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(mockRefresh).toHaveBeenCalled()
  })
})

describe('AppSideNav — nav links position', () => {
  it('Chat nav link is still rendered', async () => {
    render(<AppSideNav />)
    expect(screen.getByRole('link', { name: 'Chat' })).toBeInTheDocument()
  })

  it('nav links appear after the session list in the DOM', async () => {
    render(<AppSideNav />)
    await waitFor(() => {
      const sessionItem = screen.getByText('Feeling stressed lately')
      const chatLink = screen.getByRole('link', { name: 'Chat' })
      // In the DOM, session list comes before nav links
      expect(
        sessionItem.compareDocumentPosition(chatLink) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy()
    })
  })
})
