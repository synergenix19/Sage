# Sprint C — Architectural Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve 9 architectural consistency issues in `cdai/apps/web`: dead code deletion, render-flash guard, shared constant, navigation convention fix, locale-aware formatting, React purity fix, progress page Server Component conversion, Next.js error boundaries, and Framer Motion removal.

**Architecture:** Tasks 1–4 are independent Day 1 quick wins (deletions, one-liners, constant extraction, Link fix) that commit separately but can be worked in sequence in one session. Tasks 5–6 are contained refactors with clear before/after. Task 7 (ARCH-1) is the largest item — it splits `progress/page.tsx` into a server leaf + client view, placing `ProgressView` in `components/progress/` alongside the other progress components. Tasks 8–9 are independent of Task 7 and of each other.

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, Zustand, Vitest, Playwright, Tailwind CSS v3, Supabase server client (`@/lib/supabase/server`), pnpm monorepo (Turborepo)

---

## Files Created / Modified

| Action | Path | Responsibility |
|--------|------|----------------|
| Delete | `lib/stores/chat-store.ts` | Dead Zustand store — zero imports |
| Modify | `components/onboarding/step-guard.tsx` | null return on redirect + constant import |
| Create | `lib/onboarding-constants.ts` | Single source of `TOTAL_ONBOARDING_STEPS` |
| Modify | `app/(onboarding)/layout.tsx` | Use constant for `totalSteps` prop |
| Modify | `components/onboarding/steps/what-matters.tsx` | Use constant for final step number |
| Modify | `middleware.ts` | Dynamic step regex from constant |
| Modify | `components/chat/history-panel.tsx` | Session list buttons → `<Link>` |
| Modify | `lib/format-relative-time.ts` | Accept optional locale param |
| Modify | `lib/__tests__/format-relative-time.test.ts` | Add Arabic locale tests |
| Modify | `components/app-side-nav.tsx` | Pass locale to `formatRelativeTime` |
| Modify | `components/voice-biomarker/voice-biomarker.tsx` | Separate countdown side effect |
| Create | `components/progress/progress-view.tsx` | `'use client'` leaf for progress UI |
| Modify | `app/(app)/progress/page.tsx` | Rewrite as async Server Component |
| Create | `app/loading.tsx` | Global loading skeleton |
| Create | `app/error.tsx` | Global error boundary (must be `'use client'`) |
| Create | `app/not-found.tsx` | Global 404 page |
| Create | `app/(app)/loading.tsx` | App-shell loading skeleton (covers chat) |
| Modify | `components/chat/chat-fade-in.tsx` | Replace framer-motion with CSS class |
| Modify | `app/globals.css` | Add `animate-fade-in` keyframe + `prefers-reduced-motion` block |
| Modify | `package.json` | Remove `framer-motion` dependency |

---

## Task 1: STATE-4 — Delete dead chat-store.ts

**Files:**
- Delete: `lib/stores/chat-store.ts`

- [ ] **Step 1: Verify zero imports**

```bash
grep -r "chat-store\|useChatStore" cdai/apps/web --include="*.ts" --include="*.tsx" -l
```

Expected: no output. If any file appears, stop — do not delete until all imports are removed.

- [ ] **Step 2: Delete the file**

```bash
rm cdai/apps/web/lib/stores/chat-store.ts
```

- [ ] **Step 3: Run unit tests to confirm nothing broke**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: same pass count as before (185+), zero new failures.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete unused chat-store (dead code, zero imports) [STATE-4]"
```

---

## Task 2: ARCH-3 — StepGuard renders children during redirect

**Files:**
- Modify: `components/onboarding/step-guard.tsx`
- Create: `components/onboarding/__tests__/step-guard.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `components/onboarding/__tests__/step-guard.test.tsx`:

```tsx
import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { StepGuard } from '../step-guard'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn() }),
}))

const mockStep = vi.fn()
vi.mock('@/lib/stores/onboarding-store', () => ({
  useOnboardingStore: (selector: (s: { step: number }) => unknown) =>
    selector({ step: mockStep() }),
}))

describe('StepGuard', () => {
  beforeEach(() => { mockStep.mockReturnValue(1) })

  it('renders children when stored step matches page step', () => {
    const { getByText } = render(
      <StepGuard pageStep={1}><p>content</p></StepGuard>
    )
    expect(getByText('content')).toBeTruthy()
  })

  it('returns null when stored step is ahead of page step', () => {
    mockStep.mockReturnValue(3)
    const { container } = render(
      <StepGuard pageStep={1}><p>content</p></StepGuard>
    )
    expect(container.firstChild).toBeNull()
  })

  it('returns null when stored step is behind page step', () => {
    mockStep.mockReturnValue(1)
    const { container } = render(
      <StepGuard pageStep={3}><p>content</p></StepGuard>
    )
    expect(container.firstChild).toBeNull()
  })
})
```

- [ ] **Step 2: Run to confirm 2 tests fail**

```bash
cd cdai/apps/web && pnpm vitest run components/onboarding/__tests__/step-guard.test.tsx
```

Expected: the "renders children" test passes; the two null-return tests fail.

- [ ] **Step 3: Apply the fix**

In `components/onboarding/step-guard.tsx`, replace the final `return` on line 18:

```tsx
  return <>{children}</>
```

with:

```tsx
  if (storedStep !== pageStep) return null
  return <>{children}</>
```

Full file after change:

```tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export function StepGuard({ pageStep, children }: { pageStep: number; children: React.ReactNode }) {
  const storedStep = useOnboardingStore((s) => s.step)
  const router = useRouter()

  useEffect(() => {
    if (storedStep > pageStep) {
      router.replace(`/step-${Math.min(storedStep, 6)}`)
    } else if (storedStep < pageStep) {
      router.replace(`/step-${Math.max(storedStep, 1)}`)
    }
  }, [storedStep, pageStep, router])

  if (storedStep !== pageStep) return null
  return <>{children}</>
}
```

The `6` in `Math.min(storedStep, 6)` will become `TOTAL_ONBOARDING_STEPS` in Task 3.

- [ ] **Step 4: Run tests to confirm all three pass**

```bash
cd cdai/apps/web && pnpm vitest run components/onboarding/__tests__/step-guard.test.tsx
```

Expected: 3/3 PASS.

- [ ] **Step 5: Commit**

```bash
git add components/onboarding/step-guard.tsx components/onboarding/__tests__/step-guard.test.tsx
git commit -m "fix: StepGuard returns null during redirect, preventing wrong-step content flash [ARCH-3]"
```

---

## Task 3: TS-7 — Consolidate magic number 6 for onboarding step count

**Files:**
- Create: `lib/onboarding-constants.ts`
- Modify: `components/onboarding/step-guard.tsx` (line 12)
- Modify: `app/(onboarding)/layout.tsx` (line 6)
- Modify: `components/onboarding/steps/what-matters.tsx` (lines 20–21)
- Modify: `middleware.ts` (line 62)

**Note:** `about-you.tsx` uses `setStep(5)` (step 5 specifically, not the total) — leave it unchanged.

- [ ] **Step 1: Create the constants file**

Create `lib/onboarding-constants.ts`:

```ts
// Single-digit only — if step count ever exceeds 9, rewrite the middleware regex in middleware.ts
// (character class [1-N] breaks for N >= 10: [1-10] matches '0', '1', '-', '1' not "integers 1–10")
export const TOTAL_ONBOARDING_STEPS = 6
```

- [ ] **Step 2: Update step-guard.tsx**

Replace the top of `components/onboarding/step-guard.tsx` to add the import and use the constant:

```tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'

export function StepGuard({ pageStep, children }: { pageStep: number; children: React.ReactNode }) {
  const storedStep = useOnboardingStore((s) => s.step)
  const router = useRouter()

  useEffect(() => {
    if (storedStep > pageStep) {
      router.replace(`/step-${Math.min(storedStep, TOTAL_ONBOARDING_STEPS)}`)
    } else if (storedStep < pageStep) {
      router.replace(`/step-${Math.max(storedStep, 1)}`)
    }
  }, [storedStep, pageStep, router])

  if (storedStep !== pageStep) return null
  return <>{children}</>
}
```

- [ ] **Step 3: Update onboarding layout**

Replace `app/(onboarding)/layout.tsx`:

```tsx
import { ProgressBar } from '@/components/onboarding/progress-bar'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col bg-[var(--color-surface)]">
      <ProgressBar totalSteps={TOTAL_ONBOARDING_STEPS} />
      <main id="main-content" className="flex flex-1 flex-col items-center justify-center px-6 py-8">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  )
}
```

- [ ] **Step 4: Update what-matters.tsx**

In `components/onboarding/steps/what-matters.tsx`, add the import after the existing imports:

```ts
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'
```

In the `next()` function, replace:

```ts
    setStep(6)
    router.push('/step-6')
```

with:

```ts
    setStep(TOTAL_ONBOARDING_STEPS)
    router.push(`/step-${TOTAL_ONBOARDING_STEPS}`)
```

- [ ] **Step 5: Update middleware.ts**

In `middleware.ts`, add the import at the top (before `const AUTH_PATHS`):

```ts
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'
```

Replace line 62:

```ts
    const isOnboardingStep = /^\/step-[1-6]$/.test(pathname)
```

with:

```ts
    // Character class [1-N] assumes single-digit step count — see comment in lib/onboarding-constants.ts
    const isOnboardingStep = new RegExp(`^/step-[1-${TOTAL_ONBOARDING_STEPS}]$`).test(pathname)
```

- [ ] **Step 6: Run unit tests**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: same pass count, no new failures. The StepGuard tests from Task 2 must still pass.

- [ ] **Step 7: Commit**

```bash
git add lib/onboarding-constants.ts components/onboarding/step-guard.tsx app/\(onboarding\)/layout.tsx components/onboarding/steps/what-matters.tsx middleware.ts
git commit -m "refactor: extract TOTAL_ONBOARDING_STEPS constant, replace magic 6 across 4 files [TS-7]"
```

---

## Task 4: ARCH-4 — Replace button+router.push with Link in HistoryPanel session list

**Files:**
- Modify: `components/chat/history-panel.tsx`
- Create: `components/chat/__tests__/history-panel.test.tsx`

**Note:** The "New conversation" button at the top generates a URL with `Date.now()` and `Math.random()` at click time — it must stay a `<button>`. Only the session list items (lines 40–49, one `<button>` per session) become `<Link>`.

- [ ] **Step 1: Write the failing test**

Create `components/chat/__tests__/history-panel.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { HistoryPanel } from '../history-panel'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-chat-sessions', () => ({
  useChatSessions: () => ({
    sessions: [
      { id: 'abc-123', title: 'My session', updated_at: new Date().toISOString() },
    ],
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}))

vi.mock('@cdai/ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@cdai/ui')>()
  return {
    ...actual,
    ResponsivePanel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  }
})

describe('HistoryPanel', () => {
  it('renders session items as anchor links, not buttons', () => {
    render(<HistoryPanel open onClose={vi.fn()} />)
    const link = screen.getByRole('link', { name: 'My session' })
    expect(link).toBeTruthy()
    expect(link.getAttribute('href')).toBe('/chat?session=abc-123')
  })
})
```

- [ ] **Step 2: Run to confirm the test fails**

```bash
cd cdai/apps/web && pnpm vitest run components/chat/__tests__/history-panel.test.tsx
```

Expected: FAIL — `getByRole('link')` throws because session items are `<button>` elements.

- [ ] **Step 3: Apply the fix**

Replace `components/chat/history-panel.tsx`:

```tsx
'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { useChatSessions } from '@/lib/hooks/use-chat-sessions'

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { sessions, loading, error, refresh } = useChatSessions()
  const router = useRouter()

  return (
    <ResponsivePanel open={open} onClose={onClose} title="Past conversations">
      <button
        onClick={() => {
          router.push(`/chat?new=${Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
          onClose()
        }}
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-primary)] px-4 text-sm font-medium text-white hover:bg-[var(--color-primary-dark)]"
      >
        + New conversation
      </button>
      {loading && (
        <p className="text-sm text-[var(--color-text-secondary)]">Loading…</p>
      )}
      {error && (
        <p className="text-sm text-[var(--color-crisis)]">
          Couldn&apos;t load history —{' '}
          <button onClick={refresh} className="underline">
            retry
          </button>
        </p>
      )}
      {!loading && !error && sessions.length === 0 && (
        <p className="text-sm text-[var(--color-text-secondary)]">
          No past conversations yet.
        </p>
      )}
      {!loading &&
        !error &&
        sessions.map((s) => (
          <Link
            key={s.id}
            href={`/chat?session=${s.id}`}
            onClick={onClose}
            className="block w-full min-h-[44px] rounded-lg px-3 py-2 text-start text-sm hover:bg-[var(--color-surface-tinted)]"
          >
            {s.title ?? 'Untitled conversation'}
          </Link>
        ))}
    </ResponsivePanel>
  )
}
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd cdai/apps/web && pnpm vitest run components/chat/__tests__/history-panel.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: same pass count + 1 new test passing.

- [ ] **Step 6: Commit**

```bash
git add components/chat/history-panel.tsx components/chat/__tests__/history-panel.test.tsx
git commit -m "fix: replace button+router.push with Link for session list in HistoryPanel [ARCH-4]"
```

---

## Task 5: TS-8 — formatRelativeTime locale param

**Files:**
- Modify: `lib/format-relative-time.ts`
- Modify: `lib/__tests__/format-relative-time.test.ts`
- Modify: `components/app-side-nav.tsx`

**Context:** The function hardcodes `'en-US'` in two `toLocaleDateString` calls. The only call site is `components/app-side-nav.tsx:64`. The existing test file has comprehensive coverage of the `en-US` path — the task adds Arabic tests and the locale param without breaking existing tests.

- [ ] **Step 1: Add failing tests for Arabic locale**

In `lib/__tests__/format-relative-time.test.ts`, append after the last `describe` block. Check the top of the file for existing imports — add `vi, beforeEach, afterEach` to the import line if not present:

```ts
describe('formatRelativeTime — Arabic locale', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-25T14:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('uses ar-AE locale for day-of-week display', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString')
    const fourDaysAgo = new Date('2026-05-21T14:00:00Z').toISOString()
    formatRelativeTime(fourDaysAgo, 'ar')
    expect(spy).toHaveBeenCalledWith('ar-AE', expect.objectContaining({ weekday: 'long' }))
    spy.mockRestore()
  })

  it('uses ar-AE locale for month/day display', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString')
    const twoWeeksAgo = new Date('2026-05-11T14:00:00Z').toISOString()
    formatRelativeTime(twoWeeksAgo, 'ar')
    expect(spy).toHaveBeenCalledWith('ar-AE', expect.objectContaining({ month: 'short', day: 'numeric' }))
    spy.mockRestore()
  })

  it('returns same relative string for under-1-hour regardless of locale', () => {
    const thirtyMinsAgo = new Date('2026-05-25T13:30:00Z').toISOString()
    expect(formatRelativeTime(thirtyMinsAgo, 'ar')).toBe('30m ago')
  })

  it('defaults to en-US when no locale passed (backward compat)', () => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleDateString')
    const twoWeeksAgo = new Date('2026-05-11T14:00:00Z').toISOString()
    formatRelativeTime(twoWeeksAgo)
    expect(spy).toHaveBeenCalledWith('en-US', expect.any(Object))
    spy.mockRestore()
  })
})
```

- [ ] **Step 2: Run to confirm new tests fail**

```bash
cd cdai/apps/web && pnpm vitest run lib/__tests__/format-relative-time.test.ts
```

Expected: existing tests PASS, the 4 new Arabic tests FAIL (wrong locale used).

- [ ] **Step 3: Update the function**

Replace `lib/format-relative-time.ts`:

```ts
export function formatRelativeTime(updatedAt: string, locale = 'en'): string {
  const now = Date.now()
  const then = new Date(updatedAt).getTime()
  const diffMs = now - then
  const diffMins = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)

  if (diffHours < 1) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`

  const nowDate = new Date(now)
  const thenDate = new Date(then)

  const yesterday = new Date(nowDate)
  yesterday.setDate(nowDate.getDate() - 1)
  if (
    thenDate.getFullYear() === yesterday.getFullYear() &&
    thenDate.getMonth() === yesterday.getMonth() &&
    thenDate.getDate() === yesterday.getDate()
  ) {
    return 'Yesterday'
  }

  const displayLocale = locale === 'ar' ? 'ar-AE' : 'en-US'
  const diffDays = Math.floor(diffMs / 86_400_000)
  if (diffDays < 7) {
    return thenDate.toLocaleDateString(displayLocale, { weekday: 'long' })
  }

  return thenDate.toLocaleDateString(displayLocale, { month: 'short', day: 'numeric' })
}
```

- [ ] **Step 4: Run all formatRelativeTime tests**

```bash
cd cdai/apps/web && pnpm vitest run lib/__tests__/format-relative-time.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Pass locale from app-side-nav.tsx**

In `components/app-side-nav.tsx`, add `useLocaleStore` import alongside the existing imports:

```tsx
import { useLocaleStore } from '@/lib/stores/locale-store'
```

Inside the component function body, add:

```tsx
const locale = useLocaleStore((s) => s.locale)
```

Update the call site (currently line 64):

```tsx
{formatRelativeTime(s.updated_at, locale)}
```

- [ ] **Step 6: Run full test suite**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add lib/format-relative-time.ts lib/__tests__/format-relative-time.test.ts components/app-side-nav.tsx
git commit -m "fix: pass locale to formatRelativeTime, use ar-AE for Arabic session timestamps [TS-8]"
```

---

## Task 6: TS-3 — VoiceBiomarker side effect in state updater

**Files:**
- Modify: `components/voice-biomarker/voice-biomarker.tsx`
- Create: `components/voice-biomarker/__tests__/voice-biomarker.test.tsx`

**Context:** The current `setInterval` callback calls `stopRecording()` (which calls `setPhase`) inside a `setCountdown` updater. React 19 in Strict Mode calls updaters twice in development, making `stopRecording` fire twice per countdown expiry. The fix: make the updater pure (`Math.max(0, prev - 1)`), and add a `useEffect` that watches `countdown === 0 && phase === 'recording'` to call `stopRecording()` as a proper side effect. The analysis `setTimeout` also needs its handle stored in a ref so it clears on unmount.

**ESLint note:** The `useEffect` depends on `stopRecording`, but `stopRecording` is defined inside the component and not in the deps array — ESLint's `exhaustive-deps` rule will warn. The correct fix is to wrap `stopRecording` in `useCallback` with an empty deps array (its body only references `timerRef`, `analysisTimerRef`, `mountedRef` — all stable refs — and `setPhase`, which is stable from `useState`). Then add `stopRecording` to the `useEffect` deps. Do not silence the warning with a disable comment: fix it properly.

- [ ] **Step 1: Write the failing test**

Create `components/voice-biomarker/__tests__/voice-biomarker.test.tsx`:

```tsx
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { VoiceBiomarker } from '../voice-biomarker'

describe('VoiceBiomarker', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('shows idle state initially', () => {
    render(<VoiceBiomarker />)
    expect(screen.getByText('Start Recording')).toBeTruthy()
  })

  it('transitions idle → recording → analysing → result', async () => {
    render(<VoiceBiomarker />)

    await userEvent.click(screen.getByText('Start Recording'))
    expect(screen.getByText('Recording…')).toBeTruthy()

    act(() => { vi.advanceTimersByTime(30_000) })
    expect(screen.getByText('Analysing your voice sample…')).toBeTruthy()

    act(() => { vi.advanceTimersByTime(2_500) })
    expect(screen.getByText('Record Again')).toBeTruthy()
  })

  it('resets to idle from result', async () => {
    render(<VoiceBiomarker />)
    await userEvent.click(screen.getByText('Start Recording'))
    act(() => { vi.advanceTimersByTime(30_000) })
    act(() => { vi.advanceTimersByTime(2_500) })
    await userEvent.click(screen.getByText('Record Again'))
    expect(screen.getByText('Start Recording')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run to establish baseline**

```bash
cd cdai/apps/web && pnpm vitest run components/voice-biomarker/__tests__/voice-biomarker.test.tsx
```

Note the result. If Strict Mode double-invocation causes failures, that confirms the bug.

- [ ] **Step 3: Apply the fix**

Replace `components/voice-biomarker/voice-biomarker.tsx`:

```tsx
'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { cn } from '@cdai/ui'

type Phase = 'idle' | 'recording' | 'analysing' | 'result'

const DEMO_RESULT = {
  stressScore: 32,
  energyLevel: 'Moderate',
  recommendation: 'Your vocal patterns suggest moderate stress. Consider a short breathing exercise.',
}

export function VoiceBiomarker() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [countdown, setCountdown] = useState(30)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const analysisTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => {
      mountedRef.current = false
      if (timerRef.current) clearInterval(timerRef.current)
      if (analysisTimerRef.current) clearTimeout(analysisTimerRef.current)
    }
  }, [])

  // useCallback so stopRecording is a stable reference for the exhaustive-deps rule below.
  // Empty deps are correct: all references (timerRef, analysisTimerRef, mountedRef, setPhase) are stable.
  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setPhase('analysing')
    analysisTimerRef.current = setTimeout(() => {
      if (mountedRef.current) setPhase('result')
    }, 2500)
  }, [])

  // Side effect separated from state updater: transition when countdown hits 0 during recording.
  useEffect(() => {
    if (countdown === 0 && phase === 'recording') stopRecording()
  }, [countdown, phase, stopRecording])

  function startRecording() {
    setPhase('recording')
    setCountdown(30)
    timerRef.current = setInterval(() => {
      setCountdown((prev) => Math.max(0, prev - 1))
    }, 1000)
  }

  function reset() {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
    if (analysisTimerRef.current) { clearTimeout(analysisTimerRef.current); analysisTimerRef.current = null }
    setPhase('idle')
    setCountdown(30)
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
        Voice Wellbeing Analysis
      </h1>

      {phase === 'idle' && (
        <>
          <p className="max-w-xs text-center text-sm text-[var(--color-text-secondary)]">
            Record a 30-second voice sample for AI wellbeing analysis.
          </p>
          <button
            onClick={startRecording}
            className="min-h-[44px] rounded-full bg-[var(--color-primary)] px-6 text-sm text-white"
          >
            Start Recording
          </button>
        </>
      )}

      {phase === 'recording' && (
        <>
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-crisis)] animate-pulse" />
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">{countdown}s</p>
          <p className="text-sm text-[var(--color-text-secondary)]">Recording…</p>
          <button
            onClick={stopRecording}
            className="min-h-[44px] rounded-full border border-[var(--color-border)] px-6 text-sm text-[var(--color-text-primary)]"
          >
            Stop
          </button>
        </>
      )}

      {phase === 'analysing' && (
        <p className="text-sm text-[var(--color-text-secondary)]">Analysing your voice sample…</p>
      )}

      {phase === 'result' && (
        <div className={cn(
          'w-full max-w-sm rounded-2xl border border-[var(--color-border)]',
          'bg-[var(--color-surface)] p-5 flex flex-col gap-3'
        )}>
          <div className="flex justify-between">
            <span className="text-sm text-[var(--color-text-secondary)]">Stress Score</span>
            <span className="font-semibold text-[var(--color-text-primary)]">{DEMO_RESULT.stressScore}/100</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-[var(--color-text-secondary)]">Energy Level</span>
            <span className="font-semibold text-[var(--color-text-primary)]">{DEMO_RESULT.energyLevel}</span>
          </div>
          <p className="text-sm text-[var(--color-text-secondary)] border-t border-[var(--color-border)] pt-3">
            {DEMO_RESULT.recommendation}
          </p>
          <button
            onClick={reset}
            className="min-h-[44px] rounded-full bg-[var(--color-primary)] text-sm text-white"
          >
            Record Again
          </button>
        </div>
      )}
    </div>
  )
}
```

**Key changes vs original:**
- `setInterval` callback: `setCountdown((prev) => Math.max(0, prev - 1))` — pure, no `stopRecording` call inside
- New `useEffect` on `[countdown, phase]` calls `stopRecording()` at the right time, cleanly
- `analysisTimerRef` stores the `setTimeout` handle and clears it on unmount and reset

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd cdai/apps/web && pnpm vitest run components/voice-biomarker/__tests__/voice-biomarker.test.tsx
```

Expected: 3/3 PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add components/voice-biomarker/voice-biomarker.tsx components/voice-biomarker/__tests__/voice-biomarker.test.tsx
git commit -m "fix: separate countdown side effect from state updater in VoiceBiomarker [TS-3]"
```

---

## Task 7: ARCH-1 + ARCH-7 — Convert progress page to async Server Component

**Files:**
- Create: `components/progress/progress-view.tsx` (new client leaf — alongside EngagementCard, MoodChart, etc.)
- Modify: `app/(app)/progress/page.tsx` (rewrite as Server Component)
- Create: `components/progress/__tests__/progress-view.test.tsx`

**Context:** Currently `progress/page.tsx` is `'use client'` and uses a `useEffect` to auth-check and then fetch all data from the browser. Unauthenticated users see a skeleton flash before redirect. `chat/page.tsx` does this correctly as an async Server Component — this task matches that pattern.

`ProgressView` is placed in `components/progress/` (not `app/(app)/progress/`) to sit alongside `EngagementCard`, `MoodChart`, `TopicsScroll`, and `InsightsList`. The server component imports it from `@/components/progress/progress-view`.

Error handling shifts from local `error` state to Next.js error boundaries (created in Task 8). `ProgressView` receives data directly and renders it; if `fetchAllProgressData` throws, the `error.tsx` boundary catches it.

ARCH-7 is bundled: the `<a href="/chat">` raw anchor in the empty state becomes `<Link href="/chat">`.

- [ ] **Step 0: Verify ProgressData is exported from progress-queries.ts**

```bash
grep -n "export.*ProgressData\|ProgressData" cdai/apps/web/lib/progress-queries.ts | head -5
```

Expected output includes a line like `export interface ProgressData {` (currently at line 190). If the export is missing, add it to `lib/progress-queries.ts` before the `fetchAllProgressData` function:

```ts
export interface ProgressData {
  engagement: EngagementStats
  moodTrajectory: MoodPoint[]
  topics: TopicStat[]
  skills: SkillStat[]
  clinicalFlags: { flag: string; copy: string }[]
}
```

If the export exists, continue to Step 1.

- [ ] **Step 1: Write the ProgressView tests**

Create `components/progress/__tests__/progress-view.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ProgressView } from '../progress-view'
import type { ProgressData } from '@/lib/progress-queries'

vi.mock('@cdai/tenant', () => ({
  tenant: { copy: { progressHeader: 'Your Progress' } },
}))
vi.mock('../mood-chart', () => ({ MoodChart: () => <div data-testid="mood-chart" /> }))
vi.mock('../topics-scroll', () => ({ TopicsScroll: () => <div data-testid="topics-scroll" /> }))
vi.mock('../insights-list', () => ({ InsightsList: () => <div data-testid="insights-list" /> }))
vi.mock('../engagement-card', () => ({ EngagementCard: () => <div data-testid="engagement-card" /> }))

const emptyData: ProgressData = {
  engagement: { sessionCount: 0, skillsUsedCount: 0 },
  moodTrajectory: [],
  topics: [],
  skills: [],
  clinicalFlags: [],
}

describe('ProgressView', () => {
  it('shows empty state with Start chatting link when no data', () => {
    render(<ProgressView data={emptyData} />)
    expect(screen.getByText(/Your progress will appear here/)).toBeTruthy()
    const link = screen.getByRole('link', { name: 'Start chatting' })
    expect(link.getAttribute('href')).toBe('/chat')
  })

  it('renders engagement card when session count > 0', () => {
    render(<ProgressView data={{ ...emptyData, engagement: { sessionCount: 3, skillsUsedCount: 1 } }} />)
    expect(screen.getByTestId('engagement-card')).toBeTruthy()
  })

  it('renders mood chart when trajectory data exists', () => {
    render(<ProgressView data={{ ...emptyData, moodTrajectory: [{ day: '2026-05-24', avgIntensity: 3, sessionName: null }] }} />)
    expect(screen.getByTestId('mood-chart')).toBeTruthy()
  })

  it('does not show empty state when there is data', () => {
    render(<ProgressView data={{ ...emptyData, engagement: { sessionCount: 1, skillsUsedCount: 0 } }} />)
    expect(screen.queryByText(/Your progress will appear here/)).toBeNull()
  })
})
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd cdai/apps/web && pnpm vitest run components/progress/__tests__/progress-view.test.tsx
```

Expected: FAIL — `ProgressView` does not exist yet.

- [ ] **Step 3: Create progress-view.tsx**

Create `components/progress/progress-view.tsx`:

```tsx
'use client'
import Link from 'next/link'
import { tenant } from '@cdai/tenant'
import { EngagementCard } from './engagement-card'
import { MoodChart } from './mood-chart'
import { TopicsScroll } from './topics-scroll'
import { InsightsList } from './insights-list'
import { INTENT_TOPIC_LABELS, type ProgressData } from '@/lib/progress-queries'
import type { SessionInsight } from '@cdai/types'

export function ProgressView({ data }: { data: ProgressData }) {
  const hasAnyData =
    data.engagement.sessionCount > 0 ||
    data.moodTrajectory.length > 0 ||
    data.topics.length > 0

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 pb-8">
      <h1 className="text-xl font-semibold">{tenant.copy.progressHeader}</h1>

      {!hasAnyData && (
        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-16">
          Your progress will appear here after your first conversation.
          <br />
          <Link href="/chat" className="mt-2 inline-block text-[var(--color-primary)] underline">
            Start chatting
          </Link>
        </p>
      )}

      {hasAnyData && (
        <>
          <EngagementCard stats={data.engagement} />
          <MoodChart points={data.moodTrajectory} />
          {data.topics.length > 0 && (
            <TopicsScroll
              topics={data.topics.map(t => INTENT_TOPIC_LABELS[t.topic] ?? t.topic)}
            />
          )}
          {data.skills.length > 0 && (
            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
              <p className="mb-2 text-sm font-medium">Techniques you have explored</p>
              <div className="flex flex-wrap gap-2">
                {data.skills.map(s => (
                  <span
                    key={s.skillId}
                    className="rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)]"
                  >
                    {s.skillId.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
          {data.clinicalFlags.length > 0 && (
            <div className="space-y-2">
              {data.clinicalFlags.map(({ flag, copy }) => (
                <div
                  key={flag}
                  className="rounded-xl border border-[var(--color-surface-tinted)] bg-[var(--color-surface-tinted)] px-4 py-3"
                >
                  <p className="text-xs leading-relaxed text-[var(--color-text-primary)]">{copy}</p>
                </div>
              ))}
            </div>
          )}
          <InsightsList insights={[] as SessionInsight[]} />
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run ProgressView tests to confirm they pass**

```bash
cd cdai/apps/web && pnpm vitest run components/progress/__tests__/progress-view.test.tsx
```

Expected: 4/4 PASS.

- [ ] **Step 5: Rewrite progress/page.tsx as Server Component**

Replace the entire contents of `app/(app)/progress/page.tsx`:

```tsx
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { fetchAllProgressData } from '@/lib/progress-queries'
import { ProgressView } from '@/components/progress/progress-view'

export default async function ProgressPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')
  const data = await fetchAllProgressData(supabase, user.id)
  return <ProgressView data={data} />
}
```

- [ ] **Step 6: Run full test suite**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: all tests pass. The server component is not unit-tested directly — the `ProgressView` unit tests and E2E cover the full path.

- [ ] **Step 7: Commit**

```bash
git add app/\(app\)/progress/page.tsx components/progress/progress-view.tsx components/progress/__tests__/progress-view.test.tsx
git commit -m "refactor: convert progress page to async Server Component, extract ProgressView client leaf [ARCH-1, ARCH-7]"
```

---

## Task 8: ARCH-5 — Add loading.tsx, error.tsx, not-found.tsx

**Files:**
- Create: `app/loading.tsx`
- Create: `app/error.tsx` (must be `'use client'` — Next.js requires this for error boundaries)
- Create: `app/not-found.tsx`
- Create: `app/(app)/loading.tsx` (highest impact — covers ChatPage async awaits)

**Context:** `ChatPage` is an async Server Component with multiple `await` calls. Without `app/(app)/loading.tsx`, users see a blank white screen during navigation. `error.tsx` catches errors thrown from async Server Components including the new `ProgressPage`. Any route calling `notFound()` currently gets the default Next.js 404 screen.

- [ ] **Step 1: Create app/loading.tsx**

```tsx
import { Skeleton } from '@cdai/ui'

export default function Loading() {
  return (
    <div className="flex h-dvh items-center justify-center p-8">
      <div className="w-full max-w-sm space-y-3">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create app/error.tsx**

```tsx
'use client'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
        Something went wrong
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)]">
        We could not load this page. Please try again.
      </p>
      <button
        onClick={reset}
        className="min-h-[44px] rounded-full bg-[var(--color-primary)] px-6 text-sm text-white"
      >
        Try again
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Create app/not-found.tsx**

```tsx
import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
        Page not found
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)]">
        This page does not exist or has been moved.
      </p>
      <Link
        href="/chat"
        className="min-h-[44px] inline-flex items-center rounded-full bg-[var(--color-primary)] px-6 text-sm text-white"
      >
        Go to chat
      </Link>
    </div>
  )
}
```

- [ ] **Step 4: Create app/(app)/loading.tsx**

This is the most impactful file — it shows during ChatPage's async `await` chain on navigation.

```tsx
import { Skeleton } from '@cdai/ui'

export default function AppLoading() {
  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex items-center gap-3 border-b border-[var(--color-border)] pb-3">
        <Skeleton className="h-8 w-8 rounded-full" />
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="flex flex-1 flex-col gap-3 pt-2">
        <Skeleton className="h-10 w-2/3 self-end rounded-2xl" />
        <Skeleton className="h-16 w-3/4 rounded-2xl" />
        <Skeleton className="h-10 w-1/2 self-end rounded-2xl" />
        <Skeleton className="h-20 w-4/5 rounded-2xl" />
      </div>
      <Skeleton className="h-12 w-full rounded-full" />
    </div>
  )
}
```

- [ ] **Step 5: Run full test suite**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: same pass count, no new failures.

- [ ] **Step 6: Commit**

```bash
git add app/loading.tsx app/error.tsx app/not-found.tsx app/\(app\)/loading.tsx
git commit -m "feat: add loading, error, and not-found boundaries for app and chat routes [ARCH-5]"
```

---

## Task 9: PERF-4 — Remove Framer Motion, add CSS animation + prefers-reduced-motion

**Files:**
- Modify: `components/chat/chat-fade-in.tsx`
- Modify: `app/globals.css`
- Modify: `package.json`

**Context:** `framer-motion` (~60KB gzipped) is used exactly once: a `opacity: 0 → 1` fade with `duration: 0.35s ease-out` in `chat-fade-in.tsx`. No `prefers-reduced-motion` handling exists anywhere in the codebase — WCAG 2.3.3 AA failure. The `animate-fade-in` Tailwind class does not yet exist; it must be added to `globals.css` as a custom utility with a matching `@keyframes` declaration.

- [ ] **Step 1: Write the failing tests**

Create `components/chat/__tests__/chat-fade-in.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ChatFadeIn } from '../chat-fade-in'

describe('ChatFadeIn', () => {
  it('renders children', () => {
    render(<ChatFadeIn><p>hello</p></ChatFadeIn>)
    expect(screen.getByText('hello')).toBeTruthy()
  })

  it('does not use a framer-motion motion element', () => {
    const { container } = render(<ChatFadeIn><p>hello</p></ChatFadeIn>)
    // framer-motion motion.div injects data-projection-id
    expect(container.querySelector('[data-projection-id]')).toBeNull()
  })

  it('applies animate-fade-in class to wrapper div', () => {
    const { container } = render(<ChatFadeIn><p>hello</p></ChatFadeIn>)
    expect(container.firstElementChild?.classList.contains('animate-fade-in')).toBe(true)
  })
})
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd cdai/apps/web && pnpm vitest run components/chat/__tests__/chat-fade-in.test.tsx
```

Expected: "does not use framer-motion" and "applies animate-fade-in" both FAIL.

- [ ] **Step 3: Replace chat-fade-in.tsx**

```tsx
import type { ReactNode } from 'react'

export function ChatFadeIn({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full flex-col animate-fade-in">
      {children}
    </div>
  )
}
```

Note: `'use client'` is removed — no hooks or browser APIs remain.

- [ ] **Step 4: Add the keyframe and reduced-motion block to globals.css**

Do not replace the file. Sprint A/B or a parallel branch may have added rules that a full replacement would silently drop. Check current contents first:

```bash
cat cdai/apps/web/app/globals.css
```

Then **append** these three blocks to the end of the existing file:

```css
@layer utilities {
  .animate-fade-in {
    animation: fade-in 0.35s ease-out both;
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

The final file must contain everything that was already there, plus these three blocks. Do not remove any existing rules.

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd cdai/apps/web && pnpm vitest run components/chat/__tests__/chat-fade-in.test.tsx
```

Expected: 3/3 PASS.

- [ ] **Step 6: Remove framer-motion from package.json**

In `package.json`, delete the line:

```json
    "framer-motion": "^12.39.0",
```

Then reinstall to update the lockfile:

```bash
cd cdai/apps/web && pnpm install
```

- [ ] **Step 7: Confirm no remaining framer-motion references**

```bash
grep -r "framer-motion\|motion\." cdai/apps/web/components cdai/apps/web/app --include="*.tsx" --include="*.ts"
```

Expected: no output.

- [ ] **Step 8: Run full test suite**

```bash
cd cdai/apps/web && pnpm vitest run
```

Expected: all tests pass.

- [ ] **Step 9: Run Playwright E2E to confirm chat still loads**

```bash
cd cdai/apps/web && pnpm playwright test --grep "chat"
```

Expected: all chat-related E2E tests pass.

- [ ] **Step 10: Commit**

```bash
git add components/chat/chat-fade-in.tsx components/chat/__tests__/chat-fade-in.test.tsx app/globals.css package.json pnpm-lock.yaml
git commit -m "perf: replace framer-motion with CSS fade-in animation, add prefers-reduced-motion [PERF-4]"
```

---

## Self-Review

**1. Spec coverage:**

| Item | Task | Coverage |
|------|------|----------|
| STATE-4 — delete chat-store.ts | Task 1 | Full |
| ARCH-3 — StepGuard null on redirect | Task 2 | Full |
| TS-7 — TOTAL_ONBOARDING_STEPS constant | Task 3 | Full — all 4 files updated |
| ARCH-4 — HistoryPanel session Link | Task 4 | Full |
| TS-8 — formatRelativeTime locale param | Task 5 | Full — function + call site + tests |
| TS-3 — VoiceBiomarker state updater | Task 6 | Full — pure updater + useEffect side effect + analysisTimerRef cleanup |
| ARCH-1 — progress Server Component | Task 7 | Full |
| ARCH-7 — raw anchor in progress empty state | Task 7 (bundled) | Full — `<Link>` in ProgressView |
| ARCH-5 — loading/error/not-found | Task 8 | Full — 4 files |
| PERF-4 — remove Framer Motion | Task 9 | Full |
| PERF-4 — prefers-reduced-motion | Task 9 | Full |

**2. Placeholder scan:** No TBD, no "implement later", no "similar to Task N". All code blocks are complete. All test assertions are concrete values or spy matchers.

**3. Type consistency:**
- `ProgressData` type is imported from `@/lib/progress-queries` in both `progress-view.tsx` (Task 7) and `progress-view.test.tsx` (Task 7) — consistent
- `TOTAL_ONBOARDING_STEPS` is defined in Task 3 Step 1 and referenced by that exact name in all four usage sites — consistent
- `formatRelativeTime(updatedAt: string, locale = 'en')` signature in Task 5 Step 3 matches the call site `formatRelativeTime(s.updated_at, locale)` in Task 5 Step 5 — consistent
- `ProgressView` is a named export from `components/progress/progress-view.tsx`; Task 7 Step 5 imports it as `import { ProgressView } from '@/components/progress/progress-view'` — consistent
- `ProgressView` test in Task 7 Step 1 imports from `'../progress-view'` (relative path from `components/progress/__tests__/`) which resolves correctly to `components/progress/progress-view.tsx` — consistent
