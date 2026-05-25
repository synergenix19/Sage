import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { HistoryPanel } from '../history-panel'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'

// --- Mocks ---

const mockRefresh = vi.fn()
const mockPush = vi.fn()

vi.mock('@/lib/hooks/use-chat-sessions', () => ({
  useChatSessions: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('@cdai/ui', () => ({
  ResponsivePanel: ({
    open,
    children,
  }: {
    open: boolean
    onClose: () => void
    title: string
    children: React.ReactNode
  }) => (open ? <div data-testid="panel">{children}</div> : null),
}))

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
}))

const DEFAULT_HOOK_STATE = {
  sessions: [
    { id: 'sess-1', title: 'Feeling stressed', updated_at: '2026-05-23T10:00:00Z' },
    { id: 'sess-2', title: null, updated_at: '2026-05-22T09:00:00Z' },
  ],
  loading: false,
  error: null,
  refresh: mockRefresh,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useChatSessions).mockReturnValue(DEFAULT_HOOK_STATE)
})

// --- Tests ---

describe('HistoryPanel — visibility', () => {
  it('renders nothing when open=false', () => {
    render(<HistoryPanel open={false} onClose={vi.fn()} />)
    expect(screen.queryByTestId('panel')).not.toBeInTheDocument()
  })

  it('renders panel content when open=true', () => {
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    expect(screen.getByTestId('panel')).toBeInTheDocument()
  })
})

describe('HistoryPanel — session list', () => {
  it('shows session title when available', () => {
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    expect(screen.getByText('Feeling stressed')).toBeInTheDocument()
  })

  it('shows "Untitled conversation" for null title', () => {
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    expect(screen.getByText('Untitled conversation')).toBeInTheDocument()
  })

  it('renders session items as anchor links, not buttons', () => {
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    const link = screen.getByRole('link', { name: 'Feeling stressed' })
    expect(link).toBeTruthy()
    expect(link.getAttribute('href')).toBe('/chat?session=sess-1')
  })

  it('calls onClose when a session link is clicked', () => {
    const onClose = vi.fn()
    render(<HistoryPanel open={true} onClose={onClose} />)
    fireEvent.click(screen.getByRole('link', { name: 'Feeling stressed' }))
    expect(onClose).toHaveBeenCalled()
  })
})

describe('HistoryPanel — loading state', () => {
  it('shows loading text when loading=true', () => {
    vi.mocked(useChatSessions).mockReturnValue({ ...DEFAULT_HOOK_STATE, loading: true, sessions: [] })
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })
})

describe('HistoryPanel — error state', () => {
  it('shows error message when error is set', () => {
    vi.mocked(useChatSessions).mockReturnValue({
      ...DEFAULT_HOOK_STATE,
      error: 'Connection refused',
      sessions: [],
    })
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    expect(screen.getByText(/couldn’t load history/i)).toBeInTheDocument()
  })

  it('calls refresh() when retry button is clicked', () => {
    vi.mocked(useChatSessions).mockReturnValue({
      ...DEFAULT_HOOK_STATE,
      error: 'Connection refused',
      sessions: [],
    })
    render(<HistoryPanel open={true} onClose={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(mockRefresh).toHaveBeenCalled()
  })
})

describe('HistoryPanel — new conversation', () => {
  it('navigates to /chat?new=... when New conversation button is clicked', () => {
    const onClose = vi.fn()
    render(<HistoryPanel open={true} onClose={onClose} />)
    fireEvent.click(screen.getByText(/\+ new conversation/i))
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringMatching(/^\/chat\?new=\d+-[a-z0-9]+$/)
    )
    expect(onClose).toHaveBeenCalled()
  })
})
