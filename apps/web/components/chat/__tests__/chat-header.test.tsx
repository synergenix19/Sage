import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'

// --- Setup environment before imports ---
vi.stubGlobal('process', {
  ...process,
  env: {
    ...process.env,
    NEXT_PUBLIC_SUPABASE_URL: 'https://test.supabase.co',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-key',
  },
})

// --- Mocks (MUST be before any module imports) ---

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('@cdai/tenant', () => ({
  tenant: { brand: { logo: '/logo.png' }, copy: { appName: 'Sage by CDA' } },
}))

let mockLocale = 'en'
vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (sel?: (s: { locale: string; setLocale: (l: string) => void }) => unknown) => {
    const state = { locale: mockLocale, setLocale: vi.fn() }
    return sel ? sel(state) : state
  },
}))

vi.mock('@/components/auth/language-toggle', () => ({
  LanguageToggle: () => React.createElement('button', {}, 'EN/AR'),
}))

vi.mock('../history-panel', () => ({
  HistoryPanel: ({ open }: { open: boolean }) =>
    open ? React.createElement('div', { 'data-testid': 'history-panel' }) : null,
}))

vi.mock('../settings-panel', () => ({
  SettingsPanel: ({ open }: { open: boolean }) =>
    open ? React.createElement('div', { 'data-testid': 'settings-panel' }) : null,
}))

vi.mock('../testing-guide-panel', () => ({
  TestingGuidePanel: ({ open }: { open: boolean }) =>
    open ? React.createElement('div', { 'data-testid': 'testing-guide-panel' }) : null,
}))

vi.mock('../crisis-help-panel', () => ({
  CrisisHelpPanel: ({ open }: { open: boolean }) =>
    open ? React.createElement('div', { 'data-testid': 'crisis-help-panel' }) : null,
}))

// --- Import after all mocks ---
import { ChatHeader } from '../chat-header'

beforeEach(() => {
  vi.clearAllMocks()
  mockLocale = 'en'
})

// --- Tests ---

describe('ChatHeader — compose icon', () => {
  it('renders a compose button with md:hidden class', () => {
    render(<ChatHeader session={null} />)
    const composeBtn = screen.getByRole('button', { name: /new conversation/i })
    expect(composeBtn.className).toMatch(/md:hidden/)
  })

  it('compose button has aria-label "New conversation" in English', () => {
    render(<ChatHeader session={null} />)
    expect(
      screen.getByRole('button', { name: 'New conversation' })
    ).toBeInTheDocument()
  })

  it('compose button has Arabic aria-label when locale is ar', () => {
    mockLocale = 'ar'
    render(<ChatHeader session={null} />)
    expect(
      screen.getByRole('button', { name: 'محادثة جديدة' })
    ).toBeInTheDocument()
  })

  it('navigates to /chat?new=<timestamp>-<random> when compose is clicked', () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: /new conversation/i }))
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringMatching(/^\/chat\?new=\d+-[a-z0-9]+$/)
    )
  })
})

describe('ChatHeader — clock icon', () => {
  it('renders the clock button with md:hidden class', () => {
    render(<ChatHeader session={null} />)
    const clockBtn = screen.getByRole('button', { name: /history/i })
    expect(clockBtn.className).toMatch(/md:hidden/)
  })

  it('opens HistoryPanel when clock button is clicked', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: /history/i }))
    await waitFor(() => {
      expect(screen.getByTestId('history-panel')).toBeInTheDocument()
    })
  })
})

describe('ChatHeader — settings', () => {
  it('renders settings button (visible on all viewports — no md:hidden)', () => {
    render(<ChatHeader session={null} />)
    const settingsBtn = screen.getByRole('button', { name: /settings/i })
    expect(settingsBtn.className).not.toMatch(/md:hidden/)
  })

  it('opens SettingsPanel when settings button is clicked', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    await waitFor(() => {
      expect(screen.getByTestId('settings-panel')).toBeInTheDocument()
    })
  })
})

describe('ChatHeader — persistent "Get help now" affordance', () => {
  it('renders a "Get help now" button available every turn (off crisis detection)', () => {
    render(<ChatHeader session={null} />)
    expect(screen.getByRole('button', { name: 'Get help now' })).toBeInTheDocument()
  })

  it('exposes an Arabic aria-label when locale is ar (bilingual from day one)', () => {
    mockLocale = 'ar'
    render(<ChatHeader session={null} />)
    expect(screen.getByRole('button', { name: 'احصل على المساعدة الآن' })).toBeInTheDocument()
  })

  it('opens the CrisisHelpPanel when clicked', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: 'Get help now' }))
    await waitFor(() => {
      expect(screen.getByTestId('crisis-help-panel')).toBeInTheDocument()
    })
  })
})

describe('ChatHeader — session title', () => {
  it('shows "New conversation" when session is null', () => {
    render(<ChatHeader session={null} />)
    expect(screen.getByText('New conversation')).toBeInTheDocument()
  })

  it('shows session name when session is provided', () => {
    const session = {
      id: 's1',
      userId: 'u1',
      name: 'Anxiety about work',
      createdAt: '',
      updatedAt: '',
    }
    render(<ChatHeader session={session} />)
    expect(screen.getByText('Anxiety about work')).toBeInTheDocument()
  })
})

describe('ChatHeader — testing guide', () => {
  it('renders the testing guide button with aria-label "Testing guide"', () => {
    render(<ChatHeader session={null} />)
    expect(screen.getByRole('button', { name: 'Testing guide' })).toBeInTheDocument()
  })

  it('opens TestingGuidePanel when testing guide button is clicked', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: 'Testing guide' }))
    await waitFor(() => {
      expect(screen.getByTestId('testing-guide-panel')).toBeInTheDocument()
    })
  })
})
