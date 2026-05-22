# CDAi Pilot PWA — UI/UX Audit Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all P0 and P1 findings from the 2026-05-21 multi-agent UI/UX audit before the Gitex 2026 demo, re-prioritised by clinical and regulatory risk per architect review.

**Architecture:** Three sessions in dependency order — (1) safety + bilingual integrity, (2) onboarding + chat robustness, (3) design system + admin hardening. Each session is independently deployable. No new packages are added until Task 13 (framer-motion); all other tasks modify existing files only.

**Tech Stack:** Next.js 15 App Router, TypeScript 5, Tailwind CSS v4, Zustand, Recharts, framer-motion (Task 13 only), Vitest + React Testing Library. Codebase root: `/Users/knowledgebase/Documents/Sage/cdai/`.

---

## Constraints (read before touching any task)

1. **Crisis hotline number (Task 1):** Do NOT guess any phone number. The plan specifies a placeholder and a required confirmation step with CDA. No code ships with a guessed number.
2. **No code changes without architect approval.** This plan is for review only until approved.
3. **All tasks modify files in `apps/web/` or `packages/` only.** No schema or infrastructure changes.
4. **Test every task.** Each task includes a manual or automated verification step before committing.

---

## File Map

| File | Change type | Task(s) |
|---|---|---|
| `apps/web/components/chat/crisis-card.tsx` | Modify | 1, 2, 15 |
| `apps/web/components/chat/chat-interface.tsx` | Modify | 2, 12 |
| `apps/web/public/manifest.json` | Modify | 3 |
| `apps/web/app/layout.tsx` | Modify | 4, 7 |
| `apps/web/components/chat/chat-header.tsx` | Modify | 5 |
| `apps/web/components/chat/empty-state.tsx` | Modify | 6 |
| `apps/web/components/onboarding/steps/personalising.tsx` | Modify | 8, 10 |
| `apps/web/app/(onboarding)/layout.tsx` | Modify | 8 |
| `apps/web/app/(onboarding)/[step]/page.tsx` | Modify | 9 |
| `apps/web/components/chat/settings-panel.tsx` | Modify | 11 |
| `apps/web/lib/stores/text-size-store.ts` | Create | 11 |
| `apps/web/components/providers.tsx` | Modify | 11 |
| `apps/web/packages/theme/src/css-vars.ts` | Modify | 14 |
| `apps/web/packages/ui/src/components/button.tsx` | Modify | 14 |
| `apps/web/packages/ui/src/components/input.tsx` | Modify | 14 |
| `apps/web/components/chat/input-bar.tsx` | Modify | 14 |
| `apps/web/components/progress/topics-scroll.tsx` | Modify | 16 |
| `apps/web/packages/ui/src/components/bottom-sheet.tsx` | Modify | 17 |
| `apps/web/packages/ui/src/components/responsive-panel.tsx` | Modify | 17 |
| `apps/web/lib/admin-seed.ts` | Modify | 18 |
| `apps/web/components/admin/alerts-panel.tsx` | Modify | 18, 19 |
| `apps/web/app/admin/page.tsx` | Modify | 19, 20 |
| `apps/web/components/admin/admin-sidebar.tsx` | Modify | 20 |
| `apps/web/components/admin/charts.tsx` | Modify | 21 |
| `apps/web/app/page.tsx` | Modify | 22 |
| `apps/web/app/(app)/chat/page.tsx` | Modify | 13 |

---

## SESSION 1 — Safety + Bilingual Integrity

*Clinical and regulatory priority. Fix these before anything else ships.*

---

### Task 1: Replace US Crisis Hotline With UAE Number

**Context:** `crisis-card.tsx` currently links `tel:800HOPE`, the US SAMHSA hotline. A user in crisis in Dubai tapping this reaches a US service that cannot help and may not even connect from a UAE SIM. This is P0 patient safety.

**⚠ REQUIRED BEFORE CODING:** Confirm the correct UAE number with CDA before changing the `href`. Recommended candidates confirmed from public MoHAP/Dubai Health sources:

| Line | Number | Description |
|---|---|---|
| MoHAP National Counselling | `800 46342` | Ministry of Health and Prevention — free 24/7 |
| Dubai Careline | `800 4673` | General social support |
| Dubai Police (immediate danger) | `999` | Emergency services only |

**Use `800 46342` as default pending CDA confirmation.** Add a code comment marking the value as requiring CDA sign-off so it can't be deployed silently.

**Files:**
- Modify: `apps/web/components/chat/crisis-card.tsx`

- [ ] **Step 1: Update the hotline link with confirmed UAE number and flag comment**

Replace the entire file content:

```tsx
// CRISIS HOTLINE NUMBER — must be confirmed with CDA before shipping.
// Current value: 800 46342 (MoHAP UAE counselling line, 24/7).
// Do not change without written sign-off from Sage Clinics clinical lead.
const UAE_CRISIS_LINE = '800 46342'
const UAE_CRISIS_HREF = 'tel:800-46342'

export function CrisisCard({ content }: { content: string }) {
  return (
    <div className="mx-4 rounded-xl border-2 border-[var(--color-crisis)] bg-[var(--color-crisis)]/10 p-4">
      <p className="mb-2 text-sm font-medium text-[var(--color-crisis)]">
        You&apos;re not alone — support is available
      </p>
      <p className="text-sm text-[var(--color-text-primary)]">{content}</p>
      <a
        href={UAE_CRISIS_HREF}
        className="mt-3 inline-flex min-h-[44px] items-center rounded-full bg-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-white"
      >
        Call {UAE_CRISIS_LINE} — Talk to someone now
      </a>
    </div>
  )
}
```

Note: this also fixes P1-D3 (`bg-red-50` → `bg-[var(--color-crisis)]/10` — now uses design system token).

- [ ] **Step 2: Verify RTL rendering of the crisis card**

In the browser at `http://localhost:3000`, open settings and switch to Arabic. Navigate to chat. Type a crisis keyword (e.g., "أريد أن أموت") to trigger `CRISIS_SIGNAL`. Verify:
- The card renders in the message list (inline position)
- Text reads correctly right-to-left
- The call button does not overflow or clip
- The UAE number is visible and tappable

If RTL renders incorrectly, add `dir="ltr"` only to the `<a href="tel:...">` element (phone numbers should always display LTR regardless of page direction).

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/chat/crisis-card.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(crisis): replace US SAMHSA hotline with UAE MoHAP 800-46342 and use design token for bg"
```

---

### Task 2: Pin Crisis Card Above Input Bar

**Context:** The crisis card currently renders inline inside the scrollable message list. If the user scrolls up, the card disappears. The v7 spec is explicit: crisis state must be visually distinct and **persistent**. The inline render stays for conversational context; a second pinned render appears between the scroll area and `<InputBar>` whenever any crisis message exists in the thread.

**Files:**
- Modify: `apps/web/components/chat/chat-interface.tsx`

- [ ] **Step 1: Derive `pinnedCrisis` state from messages**

In `chat-interface.tsx`, add this derived value inside the `ChatInterface` function body, after the `useStreamingChat` call (around line 143):

```tsx
// Derive the most recent crisis message content for the pinned card.
// The inline render in the message list remains for context; this pin
// ensures the card is always visible regardless of scroll position.
const pinnedCrisis = (() => {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'assistant' && messages[i].content.startsWith(CRISIS_SIGNAL)) {
      return messages[i].content.replace(CRISIS_SIGNAL, '').trimStart()
    }
  }
  return null
})()
```

- [ ] **Step 2: Add pinned crisis render between scroll div and InputBar**

In the JSX return, locate the two existing elements:

```tsx
      </div>   {/* closes the overflow-y-auto scroll div */}

      <InputBar onSend={handleSend} disabled={isLoading} />
```

Insert the pinned card between them:

```tsx
      </div>   {/* closes the overflow-y-auto scroll div */}

      {pinnedCrisis !== null && (
        <div className="px-0 py-2">
          <CrisisCard content={pinnedCrisis} />
        </div>
      )}

      <InputBar onSend={handleSend} disabled={isLoading} />
```

- [ ] **Step 3: Verify pinning behavior**

Start dev server (`npm run dev --workspace=apps/web`). Sign in. In the chat input, type a message containing `[[CRISIS_DETECTED]]` to simulate crisis (or use the actual crisis keyword that the backend detects). Verify:
- A `CrisisCard` appears above the input bar
- Scrolling the message list up does NOT move the pinned card
- The inline `CrisisCard` in the message list is still visible when scrolled to that position
- There is exactly one pinned card even if multiple crisis messages exist (always shows the most recent)

- [ ] **Step 4: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/chat/chat-interface.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(crisis): pin crisis card above input bar so it persists on scroll"
```

---

### Task 3: Fix manifest.json (theme color, missing fields)

**Context:** `theme_color` and `background_color` are `#ffffff` (pure white) — the Android status bar will render stark white instead of the Sage Warm White. Also missing: `scope`, `dir`, `lang` — all required by spec.

**Files:**
- Modify: `apps/web/public/manifest.json`

- [ ] **Step 1: Rewrite manifest.json**

```json
{
  "name": "Sage by CDA",
  "short_name": "Sage",
  "description": "Your AI wellbeing companion — مرافقك الذكي للصحة النفسية",
  "start_url": "/chat",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#F9F8F6",
  "theme_color": "#F9F8F6",
  "dir": "auto",
  "lang": "en",
  "icons": [
    { "src": "/icons/icon-192.png",          "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/icons/icon-512.png",          "sizes": "512x512", "type": "image/png", "purpose": "any" },
    { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

Note: `icon-maskable-512.png` is a **new required asset** — a version of the app icon with 10% safe-zone padding around the visible mark so it looks correct on rounded-square Android launchers. The file must be created by a designer. Until then, copy `icon-512.png` to `icon-maskable-512.png` as a placeholder (`cp apps/web/public/icons/icon-512.png apps/web/public/icons/icon-maskable-512.png`). Tag the placeholder for designer handoff.

- [ ] **Step 2: Create maskable icon placeholder**

```bash
cp /Users/knowledgebase/Documents/Sage/cdai/apps/web/public/icons/icon-512.png \
   /Users/knowledgebase/Documents/Sage/cdai/apps/web/public/icons/icon-maskable-512.png
```

Add a note in `public/icons/README.md` (create if needed): "icon-maskable-512.png is a placeholder copy of icon-512.png. Replace before Gitex with a properly padded maskable variant (safe zone = 10% on each edge)."

- [ ] **Step 3: Verify in browser**

In Chrome DevTools → Application → Manifest. Confirm:
- `theme_color` shows `#F9F8F6`
- `scope` shows `/`
- `dir` shows `auto`
- All 3 icons listed with correct purposes
- No manifest parse errors in the console

- [ ] **Step 4: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/public/manifest.json apps/web/public/icons/
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(pwa): manifest theme_color #F9F8F6, add scope/dir/lang, correct icon structure"
```

---

### Task 4: Fix `theme-color` Meta Tag in layout.tsx

**Context:** The `<meta name="theme-color">` in `app/layout.tsx` is `#ffffff`. Android uses this for the browser chrome/status bar color on first load before the PWA manifest takes effect. Must match `--color-surface`.

**Files:**
- Modify: `apps/web/app/layout.tsx`

- [ ] **Step 1: Update the meta tag**

Locate line 48 in `app/layout.tsx`:

```tsx
<meta name="theme-color" content="#ffffff" />
```

Replace with:

```tsx
<meta name="theme-color" content="#F9F8F6" />
```

This is the one permitted location for a hardcoded hex value per spec (HTML meta attributes cannot consume CSS variables at runtime).

- [ ] **Step 2: Verify**

In Chrome on Android emulation (DevTools → Device toolbar), load `http://localhost:3000/sign-in`. The browser toolbar should show warm off-white, not pure white.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/app/layout.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(pwa): theme-color meta tag corrected to #F9F8F6 (Warm White)"
```

---

### Task 5: Add [EN|AR] Locale Toggle to Chat Header

**Context:** Spec layout shows `[🕐 history] [EN|AR] [⚙]` in the header. Currently the locale switch is two taps deep (settings → language toggle). For a bilingual Gitex demo, presenters need a one-tap affordance in the header.

The existing `LanguageToggle` component (`components/auth/language-toggle.tsx`) reloads the page after switching — this is the correct behavior (flips the SSR-rendered `dir` attribute) and is already the same pattern used in the settings panel.

**Files:**
- Modify: `apps/web/components/chat/chat-header.tsx`

- [ ] **Step 1: Import LanguageToggle and insert between history and settings buttons**

Replace the full content of `chat-header.tsx`:

```tsx
'use client'
import { useState } from 'react'
import type { ChatSession } from '@cdai/types'
import { tenant } from '@cdai/tenant'
import { LanguageToggle } from '@/components/auth/language-toggle'
import { HistoryPanel } from './history-panel'
import { SettingsPanel } from './settings-panel'

export function ChatHeader({ session }: { session: ChatSession | null }) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <>
      <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <div className="flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-7 w-7" />
          <span className="max-w-[140px] truncate text-sm font-medium text-[var(--color-text-secondary)]">
            {session?.name ?? 'New conversation'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setHistoryOpen(true)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label="History"
          >
            🕐
          </button>
          <LanguageToggle />
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full hover:bg-[var(--color-surface-tinted)]"
            aria-label="Settings"
          >
            ⚙
          </button>
        </div>
      </header>
      <HistoryPanel open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  )
}
```

- [ ] **Step 2: Verify**

Load chat page. Confirm the header shows three buttons: history clock, language toggle (showing `عربي` in EN mode), settings gear. Tap the language toggle — page reloads in RTL Arabic mode with the toggle now showing `EN`. Tap again — returns to LTR English.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/chat/chat-header.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(chat): add EN|AR locale toggle to chat header per spec"
```

---

### Task 6: Bilingual Prompt Chips and Empty State Greeting

**Context:** The `EmptyState` `PROMPT_CHIPS` array is hardcoded English. Spec: "chips appear in the current locale." Also the greeting ("Hello, name! I'm Sage...") is English-only. First thing reviewers switching to Arabic will see.

**Files:**
- Modify: `apps/web/components/chat/empty-state.tsx`

- [ ] **Step 1: Add Arabic chips and locale-aware greeting**

Replace the full file content:

```tsx
'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'

const PROMPT_CHIPS: Record<'en' | 'ar', string[]> = {
  en: [
    'How are you feeling today?',
    "I've been feeling stressed lately",
    'I have a question about…',
  ],
  ar: [
    'كيف حالك اليوم؟',
    'أشعر بالتوتر مؤخرًا',
    'لديّ سؤال عن…',
  ],
}

const GREETING: Record<'en' | 'ar', (name: string) => string> = {
  en: (name) => `Hello${name ? `, ${name}` : ''}! I'm Sage. How can I support you today?`,
  ar: (name) => `مرحبًا${name ? `، ${name}` : ''}! أنا Sage. كيف يمكنني دعمك اليوم؟`,
}

interface EmptyStateProps {
  userName: string
  onChipClick: (text: string) => void
}

export function EmptyState({ userName, onChipClick }: EmptyStateProps) {
  const locale = useLocaleStore((s) => s.locale)
  const chips = PROMPT_CHIPS[locale] ?? PROMPT_CHIPS.en
  const greeting = GREETING[locale] ?? GREETING.en

  return (
    <div className="flex flex-1 flex-col items-center justify-end gap-4 px-4 pb-4">
      <div className="w-full rounded-2xl bg-[var(--color-surface-tinted)] px-4 py-3 text-sm">
        {greeting(userName)}
      </div>
      <div className="flex w-full flex-wrap gap-2">
        {chips.map((chip) => (
          <button
            key={chip}
            onClick={() => onChipClick(chip)}
            className="min-h-[44px] rounded-full border border-[var(--color-primary)] px-4 py-2 text-sm text-[var(--color-primary)] transition-colors hover:bg-[var(--color-surface-tinted)]"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify**

Load chat page in English — chips show English. Switch to Arabic via header toggle — reload, chips show Arabic text, greeting shows Arabic.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/chat/empty-state.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(chat): bilingual prompt chips and greeting in EmptyState"
```

---

### Task 7: Locale-Split Font Loading

**Context:** Both Plus Jakarta Sans and IBM Plex Sans Arabic are loaded unconditionally for every user. Spec: "locale-split fonts — neither audience pays for the other's font budget." Language switches always cause a full page reload (via `window.location.reload()`), so the server always re-renders with the correct locale cookie, making locale-split safe.

**Files:**
- Modify: `apps/web/app/layout.tsx`

- [ ] **Step 1: Change className to load only the locale-appropriate font**

Locate line 43 in `app/layout.tsx`:

```tsx
<html lang={locale} dir={dir} className={`${jakartaSans.variable} ${ibmPlexArabic.variable}`}>
```

Replace with:

```tsx
<html lang={locale} dir={dir} className={locale === 'ar' ? ibmPlexArabic.variable : jakartaSans.variable}>
```

Both font instances (`jakartaSans` and `ibmPlexArabic`) remain instantiated at the top of the file so Next.js pre-loads both in its static analysis — but only one's CSS variable is applied to `<html>` per render, so only one font file is fetched by the browser.

- [ ] **Step 2: Verify both locales**

1. Visit `/sign-in` with `cdai-locale=en` cookie (or clear cookies). Body font should be Plus Jakarta Sans. DevTools → Network → filter "font" — only Plus Jakarta Sans woff2 files appear.
2. Set `cdai-locale=ar` cookie (`document.cookie = 'cdai-locale=ar;path=/'`) and hard reload. Body font should be IBM Plex Sans Arabic. DevTools → Network → only IBM Plex Arabic font files appear.
3. Switch back to English via the language toggle. Verify English font re-appears.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/app/layout.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "perf(fonts): locale-split font loading — one font family per locale per spec"
```

---

## SESSION 2 — Onboarding + Chat Robustness

---

### Task 8: Progress Bar Reaches 100% on Final Step

**Context:** Formula `((step-1)/6)*100` gives 83% on step 6 (personalising) — never 100%. The user's last onboarding experience is a bar stuck at 83%. Fix: advance `step` to 7 (giving `((7-1)/6)*100 = 100%`) just before the router pushes to `/chat`, then call `reset()` after a brief pause to let the 100% state render.

**Files:**
- Modify: `apps/web/components/onboarding/steps/personalising.tsx`

- [ ] **Step 1: Advance step to 7 before navigation**

In `personalising.tsx`, locate the `persist()` function. Find the success path (after the `if (error)` check, starting around line 42). Replace the success block:

**Before:**
```tsx
    clearTimeout(failTimerRef.current!)
    reset()
    router.push('/chat')
```

**After:**
```tsx
    clearTimeout(failTimerRef.current!)
    // Advance to step 7 so the progress bar shows 100% before we leave.
    // reset() is called after a short delay to let the 100% state render.
    setStep(7)
    setTimeout(() => {
      reset()
      router.push('/chat')
    }, 350)
```

You'll need to import `setStep` from `useOnboardingStore`. Update the destructure on the first line of `Personalising()`:

**Before:**
```tsx
  const { reset } = useOnboardingStore()
```

**After:**
```tsx
  const { reset, setStep } = useOnboardingStore()
```

- [ ] **Step 2: Verify**

Run through onboarding steps 1–6. On step 6 (Personalising screen), watch the progress bar at the top — it should jump to 100% just before the page transitions to `/chat`. The pulse animation plays, then 100% fills, then navigation happens.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/onboarding/steps/personalising.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(onboarding): progress bar advances to 100% before navigating to chat"
```

---

### Task 9: Step Guard for Returning Authenticated Users

**Context:** A user who completed step 4 and returns via URL to `/step-1` can re-enter the wizard from the beginning. Spec: "authenticated users with progress → redirect to their last valid step." The Zustand store persists `step` to localStorage; use it for a client-side guard.

**Files:**
- Modify: `apps/web/app/(onboarding)/[step]/page.tsx`

- [ ] **Step 1: Add a client-side StepGuard wrapper component**

Add this component to the page file (above the `OnboardingStepPage` export):

```tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

function StepGuard({ pageStep, children }: { pageStep: number; children: React.ReactNode }) {
  const storedStep = useOnboardingStore((s) => s.step)
  const router = useRouter()

  useEffect(() => {
    // If the user's stored progress is ahead of this page, redirect forward.
    // This prevents re-entering earlier steps via direct URL navigation.
    if (storedStep > pageStep) {
      router.replace(`/step-${storedStep}`)
    }
  }, [storedStep, pageStep, router])

  return <>{children}</>
}
```

- [ ] **Step 2: Wrap each step component in StepGuard**

Update `OnboardingStepPage` to pass the step index and wrap:

```tsx
export default async function OnboardingStepPage({ params }: Props) {
  const { step } = await params
  const idx = STEPS.indexOf(step)
  if (idx === -1) notFound()
  const StepComponent = STEP_COMPONENTS[idx]
  const pageStep = idx + 1 // step-1 → pageStep 1, step-6 → pageStep 6
  return (
    <StepGuard pageStep={pageStep}>
      <StepComponent />
    </StepGuard>
  )
}
```

The full updated file (combining client and server components — the guard uses `'use client'` which is a directive on the component, not the file, so the page itself remains a Server Component):

```tsx
import { notFound } from 'next/navigation'
import { Welcome } from '@/components/onboarding/steps/welcome'
import { Language } from '@/components/onboarding/steps/language'
import { Name } from '@/components/onboarding/steps/name'
import { AboutYou } from '@/components/onboarding/steps/about-you'
import { WhatMatters } from '@/components/onboarding/steps/what-matters'
import { Personalising } from '@/components/onboarding/steps/personalising'
import { StepGuard } from '@/components/onboarding/step-guard'

const STEPS = ['step-1', 'step-2', 'step-3', 'step-4', 'step-5', 'step-6']
const STEP_COMPONENTS = [Welcome, Language, Name, AboutYou, WhatMatters, Personalising]

interface Props { params: Promise<{ step: string }> }

export default async function OnboardingStepPage({ params }: Props) {
  const { step } = await params
  const idx = STEPS.indexOf(step)
  if (idx === -1) notFound()
  const StepComponent = STEP_COMPONENTS[idx]
  return (
    <StepGuard pageStep={idx + 1}>
      <StepComponent />
    </StepGuard>
  )
}

export function generateStaticParams() {
  return STEPS.map((step) => ({ step }))
}
```

- [ ] **Step 3: Create `components/onboarding/step-guard.tsx`**

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
    }
  }, [storedStep, pageStep, router])

  return <>{children}</>
}
```

- [ ] **Step 4: Verify**

1. Complete steps 1–3 (stored step = 3 or 4).
2. Manually navigate to `http://localhost:3000/step-1` in the browser URL bar.
3. Verify you are immediately redirected back to the current step, not shown step 1.

- [ ] **Step 5: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/app/\(onboarding\)/\[step\]/page.tsx apps/web/components/onboarding/step-guard.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(onboarding): step guard redirects returning users to their last valid step"
```

---

### Task 10: Framer Motion Entry Animation (Onboarding → Chat)

**Context:** Spec: "No hard navigation flash, no white-screen between onboarding and the main surface." `framer-motion` is in the spec's tech stack but not installed. The cross-layout animation is implemented as: (1) Personalising step plays its pulse animation through 100% completion, then (2) the chat page fades in on mount. This avoids complex cross-page coordination while eliminating the flash.

**Files:**
- `apps/web/package.json` (install framer-motion)
- Modify: `apps/web/app/(app)/chat/page.tsx`

- [ ] **Step 1: Install framer-motion in apps/web**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && npm install framer-motion --workspace=apps/web
```

Expected: `framer-motion` added to `apps/web/package.json` dependencies. No errors.

- [ ] **Step 2: Add fade-in wrapper to chat page**

In `apps/web/app/(app)/chat/page.tsx`, wrap the `<ChatInterface>` render in a motion div.

The page is a Server Component so the motion wrapper must be a separate Client Component. Create `apps/web/components/chat/chat-fade-in.tsx`:

```tsx
'use client'
import { motion } from 'framer-motion'

export function ChatFadeIn({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      className="flex h-full flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}
```

Update `apps/web/app/(app)/chat/page.tsx` — replace the final return statement:

**Before:**
```tsx
  return (
    <ChatInterface
      initialSession={activeSession}
      initialMessages={initialMessages}
      userName={profile?.name ?? ''}
      userId={user.id}
    />
  )
```

**After:**
```tsx
  return (
    <ChatFadeIn>
      <ChatInterface
        initialSession={activeSession}
        initialMessages={initialMessages}
        userName={profile?.name ?? ''}
        userId={user.id}
      />
    </ChatFadeIn>
  )
```

Add the import at the top of `chat/page.tsx`:

```tsx
import { ChatFadeIn } from '@/components/chat/chat-fade-in'
```

- [ ] **Step 3: Verify**

Complete the onboarding flow from step 1 through personalising. When the page transitions to `/chat`, the content should fade in over ~350ms rather than appearing instantly. The transition is subtle — the spec goal is "no flash," not a dramatic animation.

- [ ] **Step 4: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/package.json apps/web/components/chat/chat-fade-in.tsx apps/web/app/\(app\)/chat/page.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(onboarding): framer-motion fade-in on chat page entry, eliminates hard navigation flash"
```

---

### Task 11: Text Size Preference in Settings Panel

**Context:** Spec lists "language toggle, text size preference, sign-out" as the three settings panel items. Text size is missing.

**Files:**
- Create: `apps/web/lib/stores/text-size-store.ts`
- Modify: `apps/web/components/providers.tsx`
- Modify: `apps/web/components/chat/settings-panel.tsx`

- [ ] **Step 1: Create text-size Zustand store**

```typescript
// apps/web/lib/stores/text-size-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type TextSize = 'sm' | 'md' | 'lg'

interface TextSizeStore {
  size: TextSize
  setSize: (size: TextSize) => void
}

export const useTextSizeStore = create<TextSizeStore>()(
  persist(
    (set) => ({
      size: 'md',
      setSize: (size) => set({ size }),
    }),
    { name: 'cdai-text-size' }
  )
)
```

- [ ] **Step 2: Apply text size class at provider level**

In `apps/web/components/providers.tsx`, import the store and apply a CSS class to the providers wrapper:

**Before:**
```tsx
'use client'
import { useEffect } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import type { Locale } from '@cdai/types'

interface ProvidersProps {
  children: React.ReactNode
  initialLocale: Locale
}

export function Providers({ children, initialLocale }: ProvidersProps) {
  const setLocale = useLocaleStore((s) => s.setLocale)

  useEffect(() => {
    useLocaleStore.setState({ locale: initialLocale })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>
}
```

**After:**
```tsx
'use client'
import { useEffect } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { useTextSizeStore } from '@/lib/stores/text-size-store'
import { cn } from '@cdai/ui'
import type { Locale } from '@cdai/types'

interface ProvidersProps {
  children: React.ReactNode
  initialLocale: Locale
}

export function Providers({ children, initialLocale }: ProvidersProps) {
  const setLocale = useLocaleStore((s) => s.setLocale)
  const textSize = useTextSizeStore((s) => s.size)

  useEffect(() => {
    useLocaleStore.setState({ locale: initialLocale })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={cn(
      textSize === 'sm' && '[&_*]:text-[0.875em]',
      textSize === 'lg' && '[&_*]:text-[1.125em]'
    )}>
      {children}
    </div>
  )
}
```

- [ ] **Step 3: Add text size selector to settings panel**

In `apps/web/components/chat/settings-panel.tsx`, add the text size control between the language toggle and sign-out. Full updated file:

```tsx
'use client'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { cn } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { useTextSizeStore, type TextSize } from '@/lib/stores/text-size-store'
import { createClient } from '@/lib/supabase/client'

const TEXT_SIZES: { value: TextSize; label: string; labelAr: string }[] = [
  { value: 'sm', label: 'Small',  labelAr: 'صغير'  },
  { value: 'md', label: 'Medium', labelAr: 'متوسط' },
  { value: 'lg', label: 'Large',  labelAr: 'كبير'  },
]

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { locale, setLocale } = useLocaleStore()
  const { size, setSize } = useTextSizeStore()
  const router = useRouter()

  function toggleLocale() {
    const next = locale === 'en' ? 'ar' : 'en'
    setLocale(next)
    document.cookie = `cdai-locale=${next};path=/;max-age=31536000;SameSite=Lax;Secure`
    window.location.reload()
  }

  async function signOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/sign-in')
  }

  return (
    <ResponsivePanel open={open} onClose={onClose} title="Settings">
      <div className="flex flex-col gap-4">
        <button
          onClick={toggleLocale}
          className="min-h-[44px] rounded-xl border border-[var(--color-border)] px-4 py-3 text-start text-sm"
        >
          {locale === 'en' ? 'Language: English → العربية' : 'اللغة: العربية → English'}
        </button>

        <div>
          <p className="mb-2 text-xs text-[var(--color-text-secondary)]">
            {locale === 'en' ? 'Text size' : 'حجم النص'}
          </p>
          <div className="flex gap-2">
            {TEXT_SIZES.map(({ value, label, labelAr }) => (
              <button
                key={value}
                onClick={() => setSize(value)}
                className={cn(
                  'min-h-[44px] flex-1 rounded-xl border py-3 text-sm transition-colors duration-200',
                  size === value
                    ? 'border-[var(--color-primary)] bg-[var(--color-surface-tinted)] text-[var(--color-primary)]'
                    : 'border-[var(--color-border)] text-[var(--color-text-secondary)]'
                )}
              >
                {locale === 'en' ? label : labelAr}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={signOut}
          className="min-h-[44px] rounded-xl border border-[var(--color-crisis)] px-4 py-3 text-start text-sm text-[var(--color-crisis)]"
        >
          {locale === 'en' ? 'Sign out' : 'تسجيل الخروج'}
        </button>
      </div>
    </ResponsivePanel>
  )
}
```

- [ ] **Step 4: Verify**

Open settings panel. Confirm three sections: language toggle, text size (Small / Medium / Large), sign-out. Tap Large — all text in the app should enlarge. Tap Small — text shrinks. Reload — preference persists via localStorage.

- [ ] **Step 5: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/lib/stores/text-size-store.ts apps/web/components/providers.tsx apps/web/components/chat/settings-panel.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(settings): add text size preference (Small/Medium/Large) to settings panel"
```

---

### Task 12: Discard Partial Stream Content on Error

**Context:** The `catch` block in `useStreamingChat` keeps partial assistant content if `m.content.length > 0`. Spec: "partial AI response on stream failure is discarded entirely." In a therapeutic context, a truncated sentence ("You might want to consider—") is clinically worse than nothing. This also connects to the v7 `output_gate` principle — un-gated partial content should never be displayed.

**Files:**
- Modify: `apps/web/components/chat/chat-interface.tsx`

- [ ] **Step 1: Fix the catch block filter predicate**

Locate the `catch` block in `useStreamingChat` (around line 87–92):

**Before:**
```tsx
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        setError(err as Error)
        // Drop the empty placeholder assistant message on failure.
        setMessages((curr) => curr.filter((m) => m.id !== assistantId || m.content.length > 0))
      }
```

**After:**
```tsx
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        setError(err as Error)
        // Discard the assistant message entirely on any failure — partial content
        // must never be shown. Spec: "partial AI response on stream failure is
        // discarded entirely." v7 output_gate: un-gated content must not display.
        setMessages((curr) => curr.filter((m) => m.id !== assistantId))
      }
```

- [ ] **Step 2: Verify**

In the dev server with `OPENROUTER_API_KEY` unset or invalid, send a message. Verify:
- No assistant message appears in the chat list
- The error text "Something went wrong — tap to retry" appears
- Tapping retry re-sends the last user message

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/chat/chat-interface.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(chat): discard partial stream content on error — never show un-gated partial AI output"
```

---

## SESSION 3 — Design System + Admin Hardening

---

### Task 13: Add `--focus-ring` Token and Standardise Focus Rings

**Context:** Spec: "`--focus-ring` token for focus states — no per-component invention." The token is missing from `css-vars.ts`. Result: button uses `ring-offset-2`, input uses `ring-offset-1`, textarea has no offset. Keyboard navigation looks inconsistent. Adding the token and standardising all three components.

**Files:**
- Modify: `packages/theme/src/css-vars.ts`
- Modify: `packages/ui/src/components/button.tsx`
- Modify: `packages/ui/src/components/input.tsx`
- Modify: `apps/web/components/chat/input-bar.tsx`

- [ ] **Step 1: Add focus ring token to `css-vars.ts`**

In `packages/theme/src/css-vars.ts`, add two entries to the `buildCssVars` return object:

```typescript
'--focus-ring-color':  brand.colors.primary,
'--focus-ring-offset': '2px',
```

Full updated `buildCssVars` return:

```typescript
export function buildCssVars(brand: TenantBrand): Record<string, string> {
  return {
    '--color-primary':        brand.colors.primary,
    '--color-primary-dark':   brand.colors.primaryDark,
    '--color-secondary':      brand.colors.secondary,
    '--color-surface':        brand.colors.surface,
    '--color-surface-tinted': brand.colors.surfaceTinted,
    '--color-text-primary':   brand.colors.textPrimary,
    '--color-text-secondary': brand.colors.textSecondary,
    '--color-border':         brand.colors.border,
    '--color-crisis':         brand.colors.crisis,
    '--font-body':            `'${brand.fonts.body}', sans-serif`,
    '--font-arabic':          `'${brand.fonts.arabic}', sans-serif`,
    '--focus-ring-color':     brand.colors.primary,
    '--focus-ring-offset':    '2px',
  }
}
```

Update the theme test to expect 13 vars instead of 11 (`packages/theme/src/__tests__/theme.test.ts` line: `expect(Object.keys(vars)).toHaveLength(13)`).

- [ ] **Step 2: Run theme tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && npx vitest run packages/theme
```

Expected: test fails on the `toHaveLength(11)` assertion. Update to `toHaveLength(13)`, run again. Expected: PASS.

- [ ] **Step 3: Standardise focus ring in `button.tsx`**

Replace the focus-visible classes in the `cva` base string in `packages/ui/src/components/button.tsx`:

**Before:**
```
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2
```

**After:**
```
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)] focus-visible:ring-offset-[var(--focus-ring-offset)]
```

- [ ] **Step 4: Standardise focus ring in `input.tsx`**

In `packages/ui/src/components/input.tsx`, replace:

```
focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-1
```

With:

```
focus:ring-2 focus:ring-[var(--focus-ring-color)] focus:ring-offset-[var(--focus-ring-offset)]
```

- [ ] **Step 5: Add focus ring to textarea in `input-bar.tsx`**

In `apps/web/components/chat/input-bar.tsx`, find the `textarea` className and replace:

```
focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]
```

With:

```
focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring-color)] focus:ring-offset-[var(--focus-ring-offset)]
```

- [ ] **Step 6: Run package tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && npx vitest run packages/ui packages/theme
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add packages/theme/src/css-vars.ts packages/theme/src/__tests__/theme.test.ts packages/ui/src/components/button.tsx packages/ui/src/components/input.tsx apps/web/components/chat/input-bar.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(design-system): add --focus-ring-color/offset tokens, standardise all focus ring implementations"
```

---

### Task 14: Topics Chip Horizontal Scroll with Fade Mask

**Context:** Spec: horizontal chip scroll with `mask-image: linear-gradient(to right, black 85%, transparent)` fade. Current: `flex-wrap` grid with no scroll. Wrapping wastes vertical space and hides the "more topics" affordance.

**Files:**
- Modify: `apps/web/components/progress/topics-scroll.tsx`

- [ ] **Step 1: Replace flex-wrap with horizontal scroll and mask**

```tsx
export function TopicsScroll({ topics }: { topics: string[] }) {
  return (
    <div
      className="flex gap-2 overflow-x-auto pb-1"
      style={{
        maskImage: 'linear-gradient(to right, black 85%, transparent)',
        WebkitMaskImage: 'linear-gradient(to right, black 85%, transparent)',
        scrollbarWidth: 'none',
      }}
    >
      {topics.map((t) => (
        <span
          key={t}
          className="flex-shrink-0 rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)] whitespace-nowrap"
        >
          {t}
        </span>
      ))}
    </div>
  )
}
```

Notes: `flex-shrink-0` prevents chips from compressing. `whitespace-nowrap` on each chip prevents line wrap. `scrollbar-width: none` hides the scrollbar visually (the mask gradient provides the affordance). The `mask-image` is always applied — if there is no overflow it gracefully fades the last chip slightly, which is acceptable.

- [ ] **Step 2: Verify**

Load the progress page. Topics should appear as a single horizontal scrollable row. Swipe/drag horizontally on mobile or scroll horizontally on desktop. The rightmost chip should fade out into the right edge, implying more content. The mask gradient should be visible.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/progress/topics-scroll.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(progress): topics chip row horizontal scroll with mask-image fade per spec"
```

---

### Task 15: Add Title Bar to BottomSheet and Wire Through ResponsivePanel

**Context:** `ResponsivePanel` renders a title header only in the desktop sidebar. On mobile, it passes children to `BottomSheet` which has no header — the title prop is silently dropped. Settings and History panels open on mobile with no label and no visible close button.

**Files:**
- Modify: `packages/ui/src/components/bottom-sheet.tsx`
- Modify: `packages/ui/src/components/responsive-panel.tsx`

- [ ] **Step 1: Add title and close button to BottomSheet**

Replace `packages/ui/src/components/bottom-sheet.tsx`:

```tsx
'use client'
import * as React from 'react'
import { cn } from '../lib/utils'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
  title?: string
}

export function BottomSheet({ open, onClose, children, className, title }: BottomSheetProps) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-[var(--color-surface)] shadow-xl',
          className
        )}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
            <h2 className="font-semibold text-[var(--color-text-primary)]">{title}</h2>
            <button
              onClick={onClose}
              className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Wire title prop through ResponsivePanel to BottomSheet**

In `packages/ui/src/components/responsive-panel.tsx`, locate the mobile branch and pass `title`:

**Before:**
```tsx
  if (!isDesktop) return <BottomSheet open={open} onClose={onClose}>{children}</BottomSheet>
```

**After:**
```tsx
  if (!isDesktop) return <BottomSheet open={open} onClose={onClose} title={title}>{children}</BottomSheet>
```

- [ ] **Step 3: Run UI package tests**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai && npx vitest run packages/ui
```

Expected: all tests pass.

- [ ] **Step 4: Verify on mobile viewport**

In DevTools mobile emulation, open Settings and History panels. Both should now show a title header ("Settings" / "Past conversations") and a visible ✕ close button. The backdrop tap should still close both panels.

- [ ] **Step 5: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add packages/ui/src/components/bottom-sheet.tsx packages/ui/src/components/responsive-panel.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(ui): BottomSheet title bar and close button; wire title through ResponsivePanel on mobile"
```

---

### Task 16: Gitex Alert Narrative Copy

**Context:** The two specific Gitex narrative alert strings are absent. The AlertsPanel renders `alert.userId` (e.g. "usr_demo_01") as content — not descriptive text. The Parenting topic alert is entirely missing. Both alerts need spec-precise narrative copy for the government demo.

**Files:**
- Modify: `apps/web/lib/admin-seed.ts`
- Modify: `apps/web/components/admin/alerts-panel.tsx`

- [ ] **Step 1: Add `message` and `targetSection` to alert seed data**

In `lib/admin-seed.ts`, replace the `recentAlerts` array:

```typescript
recentAlerts: [
  {
    id: '1',
    message: '⚠ Elevated stress signals in Al Quoz district — last 72 hours',
    severity: 'high'   as const,
    timestamp: '2026-05-20T09:14:00Z',
    targetSection: 'district-stress',
  },
  {
    id: '2',
    message: '⚠ Parenting topic volume +34% this week vs. prior week',
    severity: 'medium' as const,
    timestamp: '2026-05-19T16:33:00Z',
    targetSection: 'top-topics',
  },
],
```

Remove `userId` and `district` from alert objects — they are no longer needed.

- [ ] **Step 2: Update AlertsPanel to render message text and handle scroll-to**

Replace `components/admin/alerts-panel.tsx` entirely:

```tsx
'use client'

interface Alert {
  id: string
  message: string
  timestamp: string
  severity: 'high' | 'medium'
  targetSection: string
}

interface AlertsPanelProps {
  alerts: Alert[]
  onAlertClick?: (targetSection: string) => void
}

export function AlertsPanel({ alerts, onAlertClick }: AlertsPanelProps) {
  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="mb-4 text-base font-semibold text-[var(--color-text-primary)]">
        Recent Alerts
      </h2>
      {alerts.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No recent alerts.</p>
      ) : (
        <ul className="space-y-3">
          {alerts.map((alert) => (
            <li key={alert.id}>
              <button
                onClick={() => onAlertClick?.(alert.targetSection)}
                className="flex w-full min-h-11 items-start gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-tinted)] px-4 py-3 text-start hover:bg-[var(--color-surface-tinted)]/80 transition-colors duration-200"
              >
                <span
                  className={`mt-0.5 h-2.5 w-2.5 flex-shrink-0 rounded-full ${
                    alert.severity === 'high'
                      ? 'bg-[var(--color-crisis)]'
                      : 'bg-yellow-400'
                  }`}
                  aria-hidden="true"
                />
                <span className="flex-1 text-sm text-[var(--color-text-primary)]">
                  {alert.message}
                </span>
                <span className="flex-shrink-0 text-xs text-[var(--color-text-secondary)]">
                  {new Date(alert.timestamp).toLocaleDateString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/lib/admin-seed.ts apps/web/components/admin/alerts-panel.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(admin): Gitex alert narrative copy and AlertsPanel renders message text"
```

---

### Task 17: Alert Click — Scroll-to and Highlight Chart Section

**Context:** Spec: clicking an alert scrolls to the relevant chart section with the target element at full opacity and all others dimmed to 20%. This turns the alert panel from decorative into an interactive demo story beat.

**Files:**
- Modify: `apps/web/app/admin/page.tsx`
- Modify: `apps/web/components/admin/charts.tsx`

- [ ] **Step 1: Add `highlightSection` state and section IDs to admin page**

Replace `app/admin/page.tsx`:

```tsx
'use client'
import { useState, useCallback } from 'react'
import { MetricCard } from '@/components/admin/metric-card'
import { MoodTrendChart, TopTopicsChart, DistrictStressChart } from '@/components/admin/charts'
import { AlertsPanel } from '@/components/admin/alerts-panel'
import { getAdminDemoData } from '@/lib/admin-seed'
import { cn } from '@cdai/ui'

export default function AdminPage() {
  const data = getAdminDemoData()
  const [highlightSection, setHighlightSection] = useState<string | null>(null)

  const handleAlertClick = useCallback((targetSection: string) => {
    setHighlightSection(targetSection)
    setTimeout(() => {
      const el = document.getElementById(targetSection)
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
    // Clear highlight after 4 seconds
    setTimeout(() => setHighlightSection(null), 4000)
  }, [])

  function sectionClass(id: string) {
    if (highlightSection === null) return ''
    return highlightSection === id ? '' : 'opacity-20 transition-opacity duration-300'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Admin Dashboard</h1>
        <div className="flex items-center gap-2">
          <select
            disabled
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] opacity-50 cursor-not-allowed"
          >
            <option>Last 30 days</option>
          </select>
          <button
            disabled
            title="Export available in full release"
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] opacity-50 cursor-not-allowed"
          >
            Export CSV
          </button>
        </div>
      </div>

      <div id="overview" className={cn('grid grid-cols-2 gap-4 lg:grid-cols-4', sectionClass('overview'))}>
        <MetricCard label="Total Users"    value={data.totalUsers}           subtext="All registered accounts" />
        <MetricCard label="Active Today"   value={data.activeToday}          subtext="Sessions in last 24 h" />
        <MetricCard label="Avg Mood Score" value={data.avgMoodScore}         subtext="Out of 5.0 this week" />
        <MetricCard label="Crisis Alerts"  value={data.crisisAlertsThisWeek} subtext="This week" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div id="mood-trend" className={sectionClass('mood-trend')}>
          <MoodTrendChart data={data.moodTrend} />
        </div>
        <div id="top-topics" className={sectionClass('top-topics')}>
          <TopTopicsChart data={data.topTopics} />
        </div>
      </div>

      <div id="district-stress" className={cn('grid grid-cols-1 gap-4', sectionClass('district-stress'))}>
        <DistrictStressChart data={data.districtStress} />
      </div>

      <div id="alerts" className={sectionClass('alerts')}>
        <AlertsPanel alerts={data.recentAlerts} onAlertClick={handleAlertClick} />
      </div>
    </div>
  )
}
```

Also add `title="Export available in full release"` tooltip to the Export button (fixes P2-11 at the same time).

- [ ] **Step 2: Verify alert click behavior**

Load the admin dashboard. Click the "Al Quoz district" alert. Verify:
- Page scrolls smoothly to the District Stress section
- All other sections dim to ~20% opacity
- The district stress section remains at full opacity
- After 4 seconds all sections return to full opacity

Click the "Parenting topic" alert. Verify scroll to Top Topics section with same dim pattern.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/app/admin/page.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(admin): alert click scrolls to and highlights relevant chart section"
```

---

### Task 18: Admin Sidebar — IntersectionObserver Scroll Anchors

**Context:** Spec: sidebar items are scroll anchors on a single scrollable page, with `IntersectionObserver` driving the active state. Current: `usePathname()` matching linking to non-existent routes. The single-page scroll-anchor architecture creates the "feels like navigation, builds like one page" effect critical for the Gitex admin demo walkthrough.

**Files:**
- Modify: `apps/web/components/admin/admin-sidebar.tsx`

- [ ] **Step 1: Rewrite AdminSidebar with IntersectionObserver**

```tsx
'use client'
import { useEffect, useState } from 'react'
import { cn } from '@cdai/ui'
import { tenant } from '@cdai/tenant'

const SECTIONS = [
  { id: 'overview',        label: 'Overview'  },
  { id: 'mood-trend',      label: 'Mood Trend' },
  { id: 'top-topics',      label: 'Topics'    },
  { id: 'district-stress', label: 'Districts' },
  { id: 'alerts',          label: 'Alerts'    },
]

export function AdminSidebar() {
  const [activeId, setActiveId] = useState<string>('overview')

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        // Use the topmost intersecting section as the active one
        const intersecting = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (intersecting.length > 0) {
          setActiveId(intersecting[0].target.id)
        }
      },
      { threshold: 0.3 }
    )

    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [])

  return (
    <aside className="bg-[var(--color-surface)] border-e border-[var(--color-border)] w-60 flex-shrink-0 flex flex-col p-4 gap-1">
      <div className="mb-4 ps-2">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          {tenant.copy.appName}
        </span>
        <p className="text-xs text-[var(--color-text-secondary)]">Admin</p>
      </div>
      <nav className="flex flex-col gap-1">
        {SECTIONS.map(({ id, label }) => (
          <a
            key={id}
            href={`#${id}`}
            onClick={(e) => {
              e.preventDefault()
              document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
            className={cn(
              'flex min-h-11 items-center rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-150',
              activeId === id
                ? 'bg-[var(--color-primary)] text-white'
                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
            )}
          >
            {label}
          </a>
        ))}
      </nav>
    </aside>
  )
}
```

- [ ] **Step 2: Verify**

Load the admin dashboard. Scroll down slowly — sidebar active indicator should move between Overview → Mood Trend → Topics → Districts → Alerts as each section enters the viewport. Clicking a sidebar link should smooth-scroll to that section.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/admin/admin-sidebar.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "feat(admin): IntersectionObserver scroll-anchor sidebar per spec"
```

---

### Task 19: District Stress Chart — Token-Based Color Gradient

**Context:** Current `districtColor()` uses three hardcoded hex thresholds including `#E67E22` (amber) which is not in the design token system. Spec: bars use a `--color-surface-tinted` → `--color-crisis` gradient mapping stress level to color. This requires RGB interpolation since Recharts SVG `fill` attributes cannot consume CSS custom properties.

**Files:**
- Modify: `apps/web/components/admin/charts.tsx`

- [ ] **Step 1: Replace `districtColor()` with RGB interpolation between token values**

In `components/admin/charts.tsx`, replace the `districtColor` function:

```typescript
// Color interpolation between design token values.
// --color-surface-tinted: #EAF0EA = rgb(234, 240, 234)
// --color-crisis:         #DC2626 = rgb(220,  38,  38)
// These values are derived from the tenant brand token system.
// If tokens change, update these constants to match.
const LOW_RGB  = { r: 234, g: 240, b: 234 } // --color-surface-tinted (#EAF0EA)
const HIGH_RGB = { r: 220, g: 38,  b: 38  } // --color-crisis        (#DC2626)

function districtColor(index: number): string {
  const ratio = Math.min(Math.max((index - 20) / 80, 0), 1) // 20–100 scale
  const r = Math.round(LOW_RGB.r + (HIGH_RGB.r - LOW_RGB.r) * ratio)
  const g = Math.round(LOW_RGB.g + (HIGH_RGB.g - LOW_RGB.g) * ratio)
  const b = Math.round(LOW_RGB.b + (HIGH_RGB.b - LOW_RGB.b) * ratio)
  return `rgb(${r}, ${g}, ${b})`
}
```

The function signature and usage (`districtColor(entry.index)`) are unchanged — only the internal implementation changes. The `<Cell>` usage in `DistrictStressChartImpl` remains exactly as-is.

- [ ] **Step 2: Verify**

Load the admin dashboard. The district stress chart bars should now show a continuous color progression: low-stress districts (Nad Al Sheba ~28) in soft sage green, high-stress districts (Al Quoz ~78) in deep red, with smooth intermediate colors. There should be no amber/orange tone in any bar.

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/components/admin/charts.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(admin): district stress chart uses token-derived color gradient (no hardcoded hex)"
```

---

### Task 20: Fix Root Page Stub

**Context:** `app/page.tsx` renders `<main>CDAi</main>`. Middleware handles all authenticated/unauthenticated redirects, so the root page never renders in normal flow — but on middleware cold-start failure or edge timeout at a Gitex kiosk, users see a blank "CDAi" stub.

**Files:**
- Modify: `apps/web/app/page.tsx`

- [ ] **Step 1: Replace stub with server-side redirect**

```tsx
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/chat')
}
```

This provides a fallback redirect for cases where middleware doesn't fire. Unauthenticated users will be caught by the `/chat` middleware guard and redirected to `/sign-in`.

- [ ] **Step 2: Verify**

Visit `http://localhost:3000/` directly. Should redirect to `/chat` (and then to `/sign-in` if not authenticated).

- [ ] **Step 3: Commit**

```bash
git -C /Users/knowledgebase/Documents/Sage/cdai add apps/web/app/page.tsx
git -C /Users/knowledgebase/Documents/Sage/cdai commit -m "fix(routing): root page redirects to /chat instead of rendering stub"
```

---

## Self-Review Against Audit Findings

Checking each P0 and P1 from the audit report:

| Finding | Task | Status |
|---|---|---|
| P0-1: Crisis card scrolls out of view | Task 2 | ✅ Covered |
| P0-2: US crisis hotline (800-HOPE) | Task 1 | ✅ Covered + CDA confirm gate |
| P0-3: manifest theme_color #ffffff | Task 3 | ✅ Covered |
| P0-4: manifest dir:auto missing | Task 3 | ✅ Covered |
| P1-O1: Progress bar never reaches 100% | Task 8 | ✅ Covered |
| P1-O2: No Framer Motion exit animation | Task 10 | ✅ Covered |
| P1-O3: No step guard for returning users | Task 9 | ✅ Covered |
| P1-O4: Both fonts loaded unconditionally | Task 7 | ✅ Covered |
| P1-C1: [EN\|AR] toggle absent from header | Task 5 | ✅ Covered |
| P1-C2: Prompt chips English-only | Task 6 | ✅ Covered |
| P1-C3: Settings missing text size preference | Task 11 | ✅ Covered |
| P1-C4: Partial stream content retained on error | Task 12 | ✅ Covered |
| P1-D1: --focus-ring token missing | Task 13 | ✅ Covered |
| P1-D2: theme-color meta #ffffff | Task 4 | ✅ Covered |
| P1-D3: bg-red-50 in crisis card | Task 1 | ✅ Covered (combined with hotline fix) |
| P1-D4: Topics chip no scroll/mask | Task 14 | ✅ Covered |
| P1-D5: BottomSheet drops title on mobile | Task 15 | ✅ Covered |
| P1-A1: Gitex alert narrative copy absent | Task 16 | ✅ Covered |
| P1-A2: Alert click scroll+highlight missing | Task 17 | ✅ Covered |
| P1-A3: District stress hardcoded hex | Task 19 | ✅ Covered |
| P1-A4: Sidebar usePathname not IntersectionObserver | Task 18 | ✅ Covered |
| P1-A5: Admin route /admin vs /admin/dashboard | Not in plan | ℹ️ Low risk — noted but intentionally deferred. URL visible at Gitex? If yes, add a redirect from `/admin/dashboard` to `/admin` as a one-liner in `app/admin/dashboard/page.tsx`. |
| P1-P1: Icon maskable asset wrong | Task 3 | ✅ Covered (placeholder created, designer handoff flagged) |
| P1-P2: Root page stub | Task 20 | ✅ Covered |
| P2-11: Export button no tooltip | Task 17 | ✅ Covered (title attribute added) |
| RTL crisis card check (architect note) | Task 1 | ✅ Covered in Step 2 verification |

**Not in this plan (P2 polish, lower risk):**
- Tab bar icons (P2-6): Requires icon assets from design. Out of scope until assets ready.
- Panel open/close animation (P2-8): Framer Motion is now installed (Task 10), add in follow-up.
- Streak card copy as single narrative (P2-10): Minor; add in follow-up.
- Skeleton shape mismatch (P2-9): Minor; add in follow-up.
- Personalising race condition (P2-2): Add a `persisting` flag in follow-up session.
- Language heading bilingual (P2-3): Add in follow-up.

**Total tasks in this plan: 20** (Sessions 1–3 above).
