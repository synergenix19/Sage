import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// ─── Amendment 6 rendered-output diff harness (P4 Task 2, Step 1) ───────────
// Renders every Task 2 migration-target component in BOTH locales BEFORE extraction and
// records every user-visible string (text nodes + aria-label/placeholder/title/alt attrs)
// to a committed snapshot. After extraction (Step 2), this file is re-run with ZERO edits —
// any snapshot delta means a call site drifted from its original string and must be reverted
// (Amendment 6). Crisis files (lib/crisis.ts, lib/crisis-config.ts, crisis-card.tsx,
// crisis-resource-list.tsx, crisis-help-panel.tsx, the chat-interface.tsx crisis-pinning path,
// and the "Get help now" crisis-help-panel trigger in chat-header.tsx) are OUT OF SCOPE for
// Task 2 and are rendered here unmodified/unmocked where they appear incidentally (e.g. inside
// ChatHeader) — this harness verifies they stay byte-identical too, but never edits them.

// --- Shared controllable mocks (module-level, switched per-test) ---

let mockLocale: 'en' | 'ar' = 'en'
vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (sel?: (s: { locale: string; setLocale: (l: string) => void }) => unknown) => {
    const state = { locale: mockLocale, setLocale: vi.fn() }
    return sel ? sel(state) : state
  },
}))

const mockPush = vi.fn()
const mockRefresh = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, refresh: vi.fn() }),
  usePathname: () => '/chat',
  useSearchParams: () => new URLSearchParams('session=sess-1'),
}))

vi.mock('next/link', () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}))

const mockResetPasswordForEmail = vi.fn().mockResolvedValue({ error: null })
const mockUpdateUser = vi.fn().mockResolvedValue({ error: null })
const mockSignInWithPassword = vi.fn().mockResolvedValue({ error: null })
const mockSignUp = vi.fn().mockResolvedValue({ error: null })
const mockGetUser = vi.fn().mockResolvedValue({ data: { user: { email: 'test@example.com' } } })
vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      resetPasswordForEmail: (...args: unknown[]) => mockResetPasswordForEmail(...args),
      updateUser: (...args: unknown[]) => mockUpdateUser(...args),
      signInWithPassword: (...args: unknown[]) => mockSignInWithPassword(...args),
      signUp: (...args: unknown[]) => mockSignUp(...args),
      getUser: (...args: unknown[]) => mockGetUser(...args),
    },
  }),
}))

vi.mock('@/lib/hooks/use-chat-sessions', () => ({
  useChatSessions: vi.fn(),
}))

vi.mock('@/lib/format-relative-time', () => ({
  // format-relative-time.ts is OUT OF SCOPE for Task 2 (follow-up (d) — Intl fix, own PR/tests).
  // Fixed so this harness never flakes on wall-clock drift between snapshot commit and re-run.
  formatRelativeTime: () => '2h ago',
}))

vi.mock('@/lib/auth-actions', () => ({
  signOutUser: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@/lib/stores/onboarding-store', () => ({
  useOnboardingStore: () => ({ setStep: vi.fn() }),
}))

vi.mock('@/lib/stores/text-size-store', () => ({
  useTextSizeStore: () => ({ size: 'md', setSize: vi.fn() }),
}))

// --- Imports after mocks (real @cdai/ui, @cdai/tenant, lib/crisis-config — none migrated/mocked) ---

import { HistoryPanel } from '@/components/chat/history-panel'
import { EmptyState } from '@/components/chat/empty-state'
import { Welcome } from '@/components/onboarding/steps/welcome'
import ForgotPasswordPage from '@/app/(auth)/forgot-password/page'
import ResetPasswordPage from '@/app/(auth)/reset-password/page'
import { TabBar } from '@/components/tab-bar'
import { AppSideNav } from '@/components/app-side-nav'
import { InputBar } from '@/components/chat/input-bar'
import { ChatHeader } from '@/components/chat/chat-header'
import { SignInForm } from '@/components/auth/sign-in-form'
import { SignUpForm } from '@/components/auth/sign-up-form'
import { PresenceIndicator } from '@/components/chat/presence-indicator'
import { LanguageToggle } from '@/components/auth/language-toggle'
import { SettingsPanel } from '@/components/chat/settings-panel'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'

// --- Helper: extract every user-visible string from a rendered container ---

function visibleStrings(container: HTMLElement) {
  const text = Array.from(container.querySelectorAll('*'))
    .flatMap((el) => Array.from(el.childNodes))
    .filter((n) => n.nodeType === Node.TEXT_NODE && (n.textContent ?? '').trim().length > 0)
    .map((n) => (n.textContent as string).trim())
  const attrNames = ['aria-label', 'placeholder', 'title', 'alt']
  const attrs: Record<string, string[]> = {}
  for (const name of attrNames) {
    attrs[name] = Array.from(container.querySelectorAll(`[${name}]`)).map((el) => el.getAttribute(name) as string)
  }
  return { text, attrs }
}

beforeEach(() => {
  mockLocale = 'en'
  vi.clearAllMocks()
  mockResetPasswordForEmail.mockResolvedValue({ error: null })
  mockUpdateUser.mockResolvedValue({ error: null })
  mockSignInWithPassword.mockResolvedValue({ error: null })
  mockSignUp.mockResolvedValue({ error: null })
  mockGetUser.mockResolvedValue({ data: { user: { email: 'test@example.com' } } })
  vi.mocked(useChatSessions).mockReturnValue({
    sessions: [
      { id: 'sess-1', title: 'Feeling stressed', updated_at: '2026-05-23T10:00:00Z' },
      { id: 'sess-2', title: null, updated_at: '2026-05-22T09:00:00Z' },
    ],
    loading: false,
    error: null,
    refresh: mockRefresh,
  })
})

// --- HistoryPanel ---

describe('copy-snapshot: HistoryPanel', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<HistoryPanel open={true} onClose={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`loading (${locale})`, () => {
      mockLocale = locale
      vi.mocked(useChatSessions).mockReturnValue({ sessions: [], loading: true, error: null, refresh: mockRefresh })
      const { container } = render(<HistoryPanel open={true} onClose={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`error (${locale})`, () => {
      mockLocale = locale
      vi.mocked(useChatSessions).mockReturnValue({ sessions: [], loading: false, error: 'boom', refresh: mockRefresh })
      const { container } = render(<HistoryPanel open={true} onClose={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- EmptyState ---

describe('copy-snapshot: EmptyState', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`no name (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<EmptyState userName="" onChipClick={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`with name (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<EmptyState userName="Alex" onChipClick={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- Welcome ---

describe('copy-snapshot: Welcome', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<Welcome />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- ForgotPasswordPage ---

describe('copy-snapshot: ForgotPasswordPage', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<ForgotPasswordPage />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`sent (${locale})`, async () => {
      mockLocale = locale
      const { container } = render(<ForgotPasswordPage />)
      const email = screen.getByPlaceholderText(locale === 'ar' ? 'البريد الإلكتروني' : 'Email')
      await userEvent.type(email, 'a@b.com')
      await userEvent.click(screen.getByRole('button'))
      await waitFor(() => expect(mockResetPasswordForEmail).toHaveBeenCalled())
      await waitFor(() => expect(screen.queryByPlaceholderText(/email|البريد/i)).not.toBeInTheDocument())
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- ResetPasswordPage ---

describe('copy-snapshot: ResetPasswordPage', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<ResetPasswordPage />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`updating (${locale})`, async () => {
      mockLocale = locale
      let resolveUpdate: (v: { error: null }) => void = () => {}
      mockUpdateUser.mockImplementationOnce(() => new Promise((res) => { resolveUpdate = res }))
      const { container } = render(<ResetPasswordPage />)
      const password = screen.getByPlaceholderText(locale === 'ar' ? 'كلمة المرور الجديدة' : 'New password')
      await userEvent.type(password, 'longenough1')
      await userEvent.click(screen.getByRole('button'))
      await waitFor(() => expect(mockUpdateUser).toHaveBeenCalled())
      await waitFor(() => expect(screen.getByRole('button')).toBeDisabled())
      expect(visibleStrings(container)).toMatchSnapshot()
      await act(async () => { resolveUpdate({ error: null }) })
    })
  }
})

// --- TabBar ---

describe('copy-snapshot: TabBar', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<TabBar />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- AppSideNav ---

describe('copy-snapshot: AppSideNav', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, async () => {
      mockLocale = locale
      const { container } = render(<AppSideNav />)
      await waitFor(() => expect(screen.getByText('test@example.com')).toBeInTheDocument())
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`loading session list (${locale})`, async () => {
      mockLocale = locale
      vi.mocked(useChatSessions).mockReturnValue({ sessions: [], loading: true, error: null, refresh: mockRefresh })
      const { container } = render(<AppSideNav />)
      await waitFor(() => expect(screen.getByText('test@example.com')).toBeInTheDocument())
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`error session list (${locale})`, async () => {
      mockLocale = locale
      vi.mocked(useChatSessions).mockReturnValue({ sessions: [], loading: false, error: 'boom', refresh: mockRefresh })
      const { container } = render(<AppSideNav />)
      await waitFor(() => expect(screen.getByText('test@example.com')).toBeInTheDocument())
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`sign-out confirm dialog (${locale})`, async () => {
      mockLocale = locale
      const { container } = render(<AppSideNav />)
      await waitFor(() => expect(screen.getByText('test@example.com')).toBeInTheDocument())
      fireEvent.click(screen.getByRole('button', { name: locale === 'ar' ? 'تسجيل الخروج' : 'Sign out' }))
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- InputBar ---

describe('copy-snapshot: InputBar', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`voice unsupported (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<InputBar onSend={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`voice supported (${locale})`, () => {
      mockLocale = locale
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(window as any).SpeechRecognition = function () {}
      const { container } = render(<InputBar onSend={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window as any).SpeechRecognition
    })
  }
})

// --- ChatHeader (crisis "Get help now" trigger renders unmodified — verified not migrated) ---

describe('copy-snapshot: ChatHeader', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`no session (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<ChatHeader session={null} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
    it(`with session (${locale})`, () => {
      mockLocale = locale
      const { container } = render(
        <ChatHeader session={{ id: 's1', userId: 'u1', name: 'Anxiety about work', createdAt: '', updatedAt: '' }} />
      )
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- SignInForm ---

describe('copy-snapshot: SignInForm', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<SignInForm />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- SignUpForm ---

describe('copy-snapshot: SignUpForm', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<SignUpForm />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- PresenceIndicator ---

describe('copy-snapshot: PresenceIndicator', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`initial dot phase (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<PresenceIndicator />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- LanguageToggle ---

describe('copy-snapshot: LanguageToggle', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`default (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<LanguageToggle />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})

// --- SettingsPanel ---

describe('copy-snapshot: SettingsPanel', () => {
  for (const locale of ['en', 'ar'] as const) {
    it(`open (${locale})`, () => {
      mockLocale = locale
      const { container } = render(<SettingsPanel open={true} onClose={vi.fn()} />)
      expect(visibleStrings(container)).toMatchSnapshot()
    })
  }
})
