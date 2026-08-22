import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
      user_id: 'u1',
      name: 'Anxiety about work',
      created_at: '',
      updated_at: '',
    }
    render(<ChatHeader session={session} />)
    expect(screen.getByText('Anxiety about work')).toBeInTheDocument()
  })
})

describe('ChatHeader — panel mutual exclusion', () => {
  // Old (pre-union-state) implementation used four independent booleans with no
  // explicit mutual-exclusion calls between the setters, so clicking a second
  // panel trigger while a panel was open left BOTH panels mounted (a latent
  // double-open). The `useState<PanelId | null>` union makes only one panel
  // open at a time by construction. This test pins the union's new,
  // behavior-CHANGING guarantee — see PR body for the determination.
  it('opens HistoryPanel and closes it when SettingsPanel is opened next', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: /history/i }))
    await waitFor(() => {
      expect(screen.getByTestId('history-panel')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    await waitFor(() => {
      expect(screen.getByTestId('settings-panel')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('history-panel')).not.toBeInTheDocument()
  })

  it('opens CrisisHelpPanel and closes it when TestingGuidePanel is opened next', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: 'Get help now' }))
    await waitFor(() => {
      expect(screen.getByTestId('crisis-help-panel')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Testing guide' }))
    await waitFor(() => {
      expect(screen.getByTestId('testing-guide-panel')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('crisis-help-panel')).not.toBeInTheDocument()
  })

  // Arrival direction: the trigger most tied to the crisis affordance is "Get help now"
  // itself. This pins that the crisis panel always wins on arrival — opening it while
  // another panel is already open closes that other panel and the help panel mounts,
  // same as the reverse direction pinned above.
  it('opens CrisisHelpPanel and closes SettingsPanel when help is opened after settings', async () => {
    render(<ChatHeader session={null} />)
    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    await waitFor(() => {
      expect(screen.getByTestId('settings-panel')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Get help now' }))
    await waitFor(() => {
      expect(screen.getByTestId('crisis-help-panel')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('settings-panel')).not.toBeInTheDocument()
  })

  // Keyboard-navigation documentation (MEDIUM review finding).
  //
  // No focus trap exists on the main chat surface today. Under the OLD four-boolean
  // implementation, tabbing out of an open crisis help panel to another header trigger
  // and activating it left the help panel mounted underneath (the old double-mount kept
  // it "on top" — reachable or not, it was never displaced). Under the new union state,
  // the same keyboard sequence DISMISSES the crisis panel: activating any other trigger
  // — by mouse OR keyboard — always displaces whichever panel is currently open, because
  // there is exactly one `openPanel` slot.
  //
  // This test pins that current, keyboard-reachable behavior precisely: it programmatically
  // focuses the "Get help now" trigger (data-testid="get-help-now") and activates it with
  // Enter, then focuses the settings trigger and activates it with Enter, and asserts the
  // help panel unmounts while the settings panel mounts.
  //
  // The displacement is reachable via keyboard ONLY because no focus trap exists at this
  // base. PR #560 (dialog-semantics draft) adds a focus trap that removes this
  // reachability — once a panel is open, focus will be confined inside it, so Tab can no
  // longer reach another header trigger while help is open. When #560 merges, THIS TEST
  // STILL PASSES (it moves focus programmatically via `.focus()`, not by tabbing through
  // the DOM), but the user-reachable keyboard path this test documents will be closed.
  // This comment is the ledger entry: if this test's assertions ever need to change
  // because #560 (or its successor) altered reachability, that is expected and this note
  // is the record of why.
  it('keyboard: Enter on Get help now opens help; Enter on settings after tabbing away closes help and opens settings', async () => {
    render(<ChatHeader session={null} />)

    const helpTrigger = screen.getByTestId('get-help-now')
    helpTrigger.focus()
    await userEvent.keyboard('{Enter}')
    await waitFor(() => {
      expect(screen.getByTestId('crisis-help-panel')).toBeInTheDocument()
    })

    const settingsTrigger = screen.getByRole('button', { name: /settings/i })
    settingsTrigger.focus()
    await userEvent.keyboard('{Enter}')
    await waitFor(() => {
      expect(screen.getByTestId('settings-panel')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('crisis-help-panel')).not.toBeInTheDocument()
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
