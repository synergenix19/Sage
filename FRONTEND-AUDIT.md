# Frontend Audit Report
**Date:** 2026-05-23  
**Scope:** `cdai/apps/web` + `cdai/packages` — Next.js 15, React 19, Turborepo monorepo  
**Methodology:** 6 parallel specialist agents — PWA, Architecture, State/API, Accessibility, TypeScript, Performance

---

## Quick Stats

| Severity | Count |
|----------|-------|
| HIGH     | 26    |
| MEDIUM   | 30    |
| LOW      | 11    |

---

## Category 1 — PWA & Service Worker

### [PWA-1] HIGH — Service worker is never compiled or registered. Offline mode is completely broken.
**Files:** `sw.ts`, `next.config.ts`, `app/layout.tsx`

`sw.ts` is a TypeScript file at the project root. Next.js only serves `public/` statically. There is no PWA plugin in `next.config.ts` to compile or emit `sw.js`. No component calls `navigator.serviceWorker.register()`. The PWA banner may appear (browsers fire `beforeinstallprompt` before checking for SW), but installing the app gives users a shell with zero offline capability.

**Fix — Step 1:** Install `@serwist/next` and wire it in `next.config.ts`:
```ts
import withSerwist from '@serwist/next'
const withPWA = withSerwist({ swSrc: 'sw.ts', swDest: 'public/sw.js' })
export default withPWA(nextConfig)
```
**Fix — Step 2:** Add a registration component:
```tsx
// components/pwa/sw-registration.tsx
'use client'
import { useEffect } from 'react'
export function SwRegistration() {
  useEffect(() => {
    if ('serviceWorker' in navigator)
      navigator.serviceWorker.register('/sw.js').catch(console.error)
  }, [])
  return null
}
```
Then render `<SwRegistration />` in `app/layout.tsx`.

---

### [PWA-2] HIGH — SW update banner reloads before `controllerchange` fires (race condition)
**File:** `components/pwa/sw-update-banner.tsx:37`

```ts
waitingWorker!.postMessage({ type: 'SKIP_WAITING' })
window.location.reload()  // fires before skipWaiting() activates the new SW
```
The page can reload while the old SW is still the controller, serving stale assets.

**Fix:**
```ts
function handleUpdate() {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    window.location.reload()
  }, { once: true })
  waitingWorker!.postMessage({ type: 'SKIP_WAITING' })
}
```

---

### [PWA-3] HIGH — Maskable icon is a confirmed placeholder (Gitex hard blocker)
**File:** `public/icons/README.md`

`README.md` explicitly states `icon-maskable-512.png` is a placeholder requiring the 10% safe-zone padding. The manifest references it with `"purpose": "maskable"`. Android will clip it into a circle at runtime.

**Fix:** Generate a proper maskable icon using maskable.app ensuring meaningful content sits within the inner 80% (safe zone). Replace `public/icons/icon-maskable-512.png` before any user-facing deployment.

---

### [PWA-4] HIGH — PWA scope `"/"` too broad — auth and admin routes render in standalone shell
**File:** `public/manifest.json`

`scope: "/"` means `/sign-in`, `/sign-up`, `/admin` all render inside the installed app shell with no browser chrome. Auth flows without an address bar is disorienting UX; the admin panel should never be accessible inside a standalone PWA.

**Fix:**
```json
{ "scope": "/chat", "start_url": "/chat" }
```

---

### [PWA-5] MEDIUM — No `activate` handler; old caches never evicted
**File:** `sw.ts`

When `CACHE_NAME` is bumped in a future update, `cdai-v1` will remain forever.

**Fix:** Add a standard activate handler with `clients.claim()`:
```ts
self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))))
      .then(() => (self as unknown as ServiceWorkerGlobalScope).clients.claim())
  )
})
```

---

### [PWA-6] MEDIUM — `<link rel="manifest">` duplicated in `layout.tsx`
**File:** `app/layout.tsx:47`

The `metadata` export already causes Next.js to emit `<link rel="manifest">`. The manual tag on line 47 creates a duplicate. Add `themeColor` to the metadata export and remove both manual tags:
```ts
export const metadata: Metadata = {
  manifest: '/manifest.json',
  themeColor: '#F9F8F6',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: tenant.copy.appName },
}
// Remove manual <link rel="manifest"> and <meta name="theme-color"> from <head>
```

---

### [PWA-7] MEDIUM — Install prompt dismissed state not persisted after native OS prompt dismissal
**File:** `components/pwa/install-prompt.tsx:53`

`localStorage.setItem(DISMISSED_KEY, '1')` is only written in `handleDismiss()`. If the user clicks Install but then dismisses the OS native prompt, the banner disappears for the session but reappears on next page load.

**Fix:** Write the dismissed key after `userChoice` resolves, regardless of outcome:
```ts
async function handleInstall() {
  if (!promptRef.current) return
  await promptRef.current.prompt()
  await promptRef.current.userChoice
  localStorage.setItem(DISMISSED_KEY, '1')
  setShowBanner(false)
}
```

---

### [PWA-8] LOW — No `shortcuts` in manifest
**File:** `public/manifest.json`

Add a direct-to-chat shortcut for Android/Windows home screens:
```json
"shortcuts": [{ "name": "Open Chat", "url": "/chat", "icons": [{ "src": "/icons/icon-192.png", "sizes": "192x192" }] }]
```

---

### [PWA-9] LOW — `offline.html` missing `lang`/`dir` on `<html>`; Arabic paragraph not marked
**File:** `public/offline.html`

```html
<html lang="en">
<!-- Arabic paragraph: -->
<p class="ar" lang="ar" dir="rtl">أنت غير متصل…</p>
```

---

## Category 2 — Next.js 15 Architecture

### [ARCH-1] HIGH — `progress/page.tsx` is a full `'use client'` page doing server-side auth and data fetching
**File:** `app/(app)/progress/page.tsx`

Auth guard uses `useEffect` + `router.push('/sign-in')` — unauthenticated users see a skeleton flash before redirect. All 5 Supabase progress queries run from the browser. `chat/page.tsx` does this correctly as an async Server Component. This is the most significant architectural inconsistency in the app.

**Fix:** Convert to an async Server Component:
```tsx
export default async function ProgressPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')
  const data = await fetchAllProgressData(supabase, user.id)
  return <ProgressView data={data} />
}
```
Move `'use client'` to a new `ProgressView` leaf component.

---

### [ARCH-2] HIGH — `CRISIS_SIGNAL` constant duplicated across two files
**Files:** `app/(app)/chat/page.tsx:6`, `components/chat/chat-interface.tsx:12`

Both independently define `const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'`. If the sentinel changes in one place, crisis detection silently breaks.

**Fix:** Export from a single canonical location (`lib/constants.ts` or `@cdai/types`) and import in both files.

---

### [ARCH-3] HIGH — `StepGuard` renders children during redirect — wrong step content flashes
**File:** `components/onboarding/step-guard.tsx:18`

The component always returns `<>{children}</>` even when it is about to redirect. The wrong step is visible for one render frame.

**Fix:**
```tsx
if (storedStep !== pageStep) return null
return <>{children}</>
```

---

### [ARCH-4] HIGH — `<button>+router.push` used for URL navigation in `HistoryPanel`
**Files:** `components/chat/history-panel.tsx:40–50`, `history-panel.tsx:12`

Violates explicit project convention. Right-click, browser history, and screen reader navigation semantics are all broken.

**Fix:** Replace with `<Link>`:
```tsx
<Link key={s.id} href={`/chat?session=${s.id}`} onClick={onClose} className="block ...">
  {s.title ?? 'Untitled conversation'}
</Link>
```

---

### [ARCH-5] MEDIUM — No `loading.tsx`, `error.tsx`, or `not-found.tsx` files anywhere
**File:** Entire `app/` directory

`ChatPage` is an async Server Component with multiple awaits — no streaming skeleton exists. Any navigation to a non-existent `[step]` calls `notFound()` but gets the default Next.js 404 page.

**Minimum required files:**
```
app/loading.tsx
app/error.tsx        ('use client')
app/not-found.tsx
app/(app)/loading.tsx   (highest impact — covers chat page fetch)
```

---

### [ARCH-6] MEDIUM — `forgot-password` and `reset-password` pages are page-level `'use client'`
**Files:** `app/(auth)/forgot-password/page.tsx:1`, `app/(auth)/reset-password/page.tsx:1`

Prevents `metadata` export for SEO. Inconsistent with `sign-in` and `sign-up` which correctly delegate `'use client'` to form components.

**Fix:** Extract `ForgotPasswordForm` and `ResetPasswordForm` components. Remove `'use client'` from the page files and add `export const metadata`.

---

### [ARCH-7] MEDIUM — `<a href="/chat">` raw anchor in progress page
**File:** `app/(app)/progress/page.tsx:66`

Causes a full browser navigation. Replace with `<Link href="/chat">`.

---

### [ARCH-8] MEDIUM — No page-level `metadata` exports — only root layout has SEO metadata
**Files:** All route pages

Sign-in, sign-up, onboarding, progress, chat, and biomarker pages all inherit only the root `title`. For a Gitex launch, at minimum the auth and onboarding pages need distinct titles.

---

### [ARCH-9] MEDIUM — Raw `<img>` instead of `next/image` for logos (two above-fold instances)
**Files:** `components/chat/chat-header.tsx:26`, `components/onboarding/steps/welcome.tsx:18`

Both suppress the lint warning with comments rather than fixing it. Use `<Image>` with `priority` and explicit `width`/`height`.

---

### [ARCH-10] LOW — `totalSteps={6}` hardcoded; `STEPS` array is the canonical source
**File:** `app/(onboarding)/layout.tsx:6`

Adding or removing a step requires updating both files manually. Extract a `TOTAL_ONBOARDING_STEPS` constant from `STEPS.length` and import it in the layout.

---

### [ARCH-11] LOW — Admin shell layout has no auth guard
**File:** `app/admin/layout.tsx`

The middleware guards `/admin`, but the layout itself renders the admin shell unconditionally. Add an in-layout `getUser()` + `is_admin` check as a belt-and-suspenders defence.

---

## Category 3 — State Management, Hooks & API Routes

### [STATE-1] HIGH — Admin page bypasses its own auth gate via `revalidate = 60`
**File:** `app/admin/page.tsx`

`export const revalidate = 60` means Next.js serves cached responses for 60 seconds without re-running middleware. During that window, the middleware auth gate is bypassed for requests that hit the cached page. This page exposes clinical crisis counts and aggregated user data.

**Fix:** Add explicit in-page auth check and switch to `force-dynamic`:
```ts
export const dynamic = 'force-dynamic'

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')
  const { data: profile } = await supabase.from('user_profiles').select('is_admin').eq('id', user.id).single()
  if (!profile?.is_admin) return new Response(null, { status: 403 })
  // ...
}
```

---

### [STATE-2] HIGH — No Zod validation on `/api/chat` — prompt injection risk
**File:** `app/api/chat/route.ts:43–52`

`messages` content is interpolated directly into the LLM classifier prompt with no sanitisation. `sessionId` ownership is only checked *after* the classifier LLM call fires, wasting tokens on unauthorised requests. `crisisState`, `clinicalFlags`, and `distressTrajectory` are passed unchecked to the sage backend.

**Fix:** Add a Zod schema and parse before any LLM or auth call:
```ts
const ChatRequestSchema = z.object({
  sessionId: z.string().uuid(),
  messages: z.array(z.object({ role: z.enum(['user', 'assistant']), content: z.string().max(8000) })).min(1),
  crisisState: z.string().optional().default('none'),
  clinicalFlags: z.array(z.string()).optional().default([]),
  distressTrajectory: z.array(z.number()).optional().default([]),
})
```

---

### [STATE-3] HIGH — No Zod validation on `/api/feedback` — `messageId` unvalidated
**File:** `app/api/feedback/route.ts:5`

`messageId` is cast from JSON with no type or UUID check. Fix with:
```ts
const FeedbackSchema = z.object({ messageId: z.string().uuid(), value: z.union([z.literal(1), z.literal(-1)]) })
```

---

### [STATE-4] HIGH — `chat-store.ts` is entirely unused dead code
**File:** `lib/stores/chat-store.ts`

Zero imports across the entire web app. The store shadows state already managed by `useStreamingChat`'s local `useState`. If a future developer wires it up thinking it's the source of truth, they will produce split state.

**Fix:** Delete `lib/stores/chat-store.ts`.

---

### [STATE-5] HIGH — Sign-out does not reset persisted Zustand stores — PII leaks on shared devices
**File:** `lib/auth-actions.ts`

`signOutUser` calls `supabase.auth.signOut()` and redirects. It does not clear `useOnboardingStore` (persisted as `cdai-onboarding` in localStorage), which retains the previous user's `name`, `ageRange`, `role`, `wellnessQ1`, and `wellnessQ2`. On a shared device, the next sign-up flow is pre-populated with another user's PII.

**Fix:**
```ts
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export async function signOutUser(push: (href: string) => void) {
  useOnboardingStore.getState().reset()
  const supabase = createClient()
  await supabase.auth.signOut()
  push('/sign-in')
}
```

---

### [STATE-6] MEDIUM — No rate limiting on `/api/chat`
**File:** `app/api/chat/route.ts`

Each authenticated request triggers 2 LLM calls (classifier + sage backend) and 2 Supabase writes. A single user can exhaust OpenRouter credits with no throttle. Use Vercel Edge Middleware rate limiting or Upstash Ratelimit before production user exposure.

---

### [STATE-7] MEDIUM — `useChatSessions` discards `getUser()` error — auth failure looks like empty history
**File:** `lib/hooks/use-chat-sessions.ts:30`

```ts
supabase.auth.getUser().then(({ data: { user } }) => {
```
The `error` field is destructured away. A network error or token expiry silently renders "No past conversations yet."

**Fix:** Destructure and handle `error`:
```ts
.then(({ data: { user }, error: userError }) => {
  if (userError || !user) { if (userError) setError(userError.message); setLoading(false); return }
```

---

### [STATE-8] MEDIUM — `settings-panel.tsx` subscribes to entire store objects
**File:** `components/chat/settings-panel.tsx:15`

```ts
const { locale, setLocale } = useLocaleStore()
```
Inconsistent with every other store consumer in the codebase which uses selector form `(s) => s.field`. Fix:
```ts
const locale = useLocaleStore((s) => s.locale)
const setLocale = useLocaleStore((s) => s.setLocale)
```

---

### [STATE-9] MEDIUM — Progress queries fetch all-time sessions with no date cutoff (4 of 5 functions)
**File:** `lib/progress-queries.ts`

`fetchMoodTrajectory`, `fetchRecentTopics`, `fetchSkillsUsed`, `fetchClinicalFlagsForUser` all pull all chat sessions for a user with no date filter. `fetchEngagement` correctly applies a 21-day cutoff. As users accumulate history, these become unbounded table scans.

**Fix:** Apply the same `.gte('created_at', cutoffDate)` date filter to the session query in each function (or document the intentional all-time scope for `fetchClinicalFlagsForUser`).

---

### [STATE-10] LOW — Admin Supabase client recreated on every request
**File:** `lib/supabase/admin.ts`

**Fix:** Use a module-level singleton:
```ts
let _adminClient: ReturnType<typeof createClient> | null = null
export function createAdminClient() {
  if (_adminClient) return _adminClient
  _adminClient = createClient(url, key, { auth: { autoRefreshToken: false, persistSession: false } })
  return _adminClient
}
```

---

## Category 4 — Accessibility & Internationalization

### [A11Y-1] HIGH — No ARIA live region on the chat message container
**File:** `components/chat/chat-interface.tsx:245`

Screen reader users receive no notification when a new message arrives or streaming begins. WCAG 4.1.3 failure. For a mental health app this includes safety-critical crisis responses.

**Fix:**
```tsx
<div role="log" aria-live="polite" aria-label={locale === 'ar' ? 'المحادثة' : 'Conversation'} ...>
```

---

### [A11Y-2] HIGH — Form inputs have no `<label>` elements — placeholders only
**Files:** `components/auth/sign-in-form.tsx:34,36`, `components/auth/sign-up-form.tsx:36,38`

Placeholders disappear on input. WCAG 1.3.1 failure. Screen reader users cannot identify fields after typing begins.

**Fix:**
```tsx
<label htmlFor="signin-email" className="sr-only">Email</label>
<Input id="signin-email" type="email" placeholder="Email" {...register('email')} />
```

---

### [A11Y-3] HIGH — No skip-to-content link
**Files:** `app/layout.tsx`, `app/(app)/layout.tsx`

Keyboard users must Tab through all sidebar navigation on every page load before reaching the message input. WCAG 2.4.1.

**Fix:** Add as first child of `<body>`:
```tsx
<a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:start-4 ...">
  {locale === 'ar' ? 'تخطى إلى المحتوى' : 'Skip to content'}
</a>
```
Add `id="main-content"` to `<main>` in `app/(app)/layout.tsx:10`.

---

### [A11Y-4] HIGH — `BottomSheet` has no `role="dialog"`, `aria-modal`, or focus trap
**File:** `packages/ui/src/components/bottom-sheet.tsx:16`

Focus escapes into the obscured page behind the backdrop. WCAG 2.1.2, 4.1.2. `AppSideNav` implements a correct manual focus trap — the same pattern is needed here.

**Fix:** Add `role="dialog" aria-modal="true"` to the sheet `<div>`, implement an `useEffect` that focuses the first focusable element on open, traps Tab within the sheet, and closes on Escape.

---

### [A11Y-5] HIGH — `ResponsivePanel` desktop drawer also missing dialog semantics
**File:** `packages/ui/src/components/responsive-panel.tsx:31`

Same failures as A11Y-4 on the desktop code path. `BottomSheet` and `ResponsivePanel` should share a `useFocusTrap` hook.

---

### [A11Y-6] HIGH — Crisis card has no `role="alert"` — screen readers will not announce it
**File:** `components/chat/crisis-card.tsx:18`

The crisis card is the primary safety surface of the app. When it mounts, no AT announcement fires. WCAG 4.1.3. Safety risk.

**Fix:**
```tsx
<div role="alert" className="...">
```

---

### [A11Y-7] HIGH — Send button arrow `→` not mirrored for RTL Arabic
**File:** `components/chat/input-bar.tsx:73`

In RTL layout, directional icons must point left. The raw Unicode `→` is not mirrored.

**Fix:** Use locale-conditional character or a mirrored SVG:
```tsx
{locale === 'ar' ? '←' : '→'}
```
A proper `aria-hidden="true"` SVG icon with `dir="rtl"` CSS `scaleX(-1)` is strongly preferred.

---

### [A11Y-8] MEDIUM — `LanguageToggle` no locale-aware `aria-label`; triggers full reload losing focus
**File:** `components/auth/language-toggle.tsx:17`

`عربي` is meaningless to an English screen reader. `window.location.reload()` destroys focus context with no announcement.

**Fix:**
```tsx
<Button aria-label={locale === 'en' ? 'Switch to Arabic' : 'Switch to English'} lang={locale === 'en' ? 'ar' : 'en'}>
```

---

### [A11Y-9] MEDIUM — Chat `<textarea>` has no accessible name
**File:** `components/chat/input-bar.tsx:55`

Placeholder only, no `aria-label`. WCAG 1.3.1.

**Fix:**
```tsx
aria-label={locale === 'ar' ? 'اكتب رسالتك' : 'Message'}
```

---

### [A11Y-10] MEDIUM — Voice button `aria-label` English-only; no `aria-pressed`
**File:** `components/chat/input-bar.tsx:51`

**Fix:**
```tsx
aria-label={locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input'}
aria-pressed={listening}
```

---

### [A11Y-11] MEDIUM — Panel titles and close button labels hardcoded English
**Files:** `components/chat/history-panel.tsx:11`, `packages/ui/src/components/bottom-sheet.tsx:30`, `packages/ui/src/components/responsive-panel.tsx:34`

Add a `closeLabel?: string` prop to `BottomSheet`/`ResponsivePanel` with a default of `'Close'`. Pass `locale === 'ar' ? 'إغلاق' : 'Close'` from call sites.

---

### [A11Y-12] MEDIUM — `TabBar` active link has no `aria-current="page"`
**File:** `components/tab-bar.tsx:24`

`AppSideNav`'s session list correctly sets `aria-current="page"`. `TabBar` does not.

**Fix:**
```tsx
<Link aria-current={active ? 'page' : undefined} ...>
```

---

### [A11Y-13] MEDIUM — Only one font variable set on `<html>` per locale
**File:** `app/layout.tsx:43`

`jakartaSans.variable` is only applied when locale is English; `ibmPlexArabic.variable` only when Arabic. Any component forcing `font-body` in Arabic mode falls back to system sans-serif.

**Fix:** Always apply both variables:
```tsx
<html className={`${jakartaSans.variable} ${ibmPlexArabic.variable}`} lang={locale} dir={dir}>
```

---

### [A11Y-14] MEDIUM — Onboarding language step: English-only heading; Arabic button missing `dir`/`lang`
**File:** `components/onboarding/steps/language.tsx:26`

The first screen an Arabic-speaking user sees has an English heading and Arabic button text in an LTR container.

**Fix:**
```tsx
<Button key="ar" dir="rtl" lang="ar" ...>العربية</Button>
```
And render the heading bilingually or in the user's likely language.

---

### [A11Y-15] LOW — `offline.html` and panel close buttons always output English
Already covered under PWA-9 and A11Y-11.

---

## Category 5 — TypeScript Quality & Code Smells

### [TS-1] HIGH — `React.ReactNode` used without import in `responsive-panel.tsx` — compile error
**File:** `packages/ui/src/components/responsive-panel.tsx:10`

`React.ReactNode` is referenced but `React` is never imported. Will fail compilation under `strict: true`.

**Fix:**
```ts
import { type ReactNode, useEffect, useState } from 'react'
// Change interface field: children: ReactNode
```

---

### [TS-2] HIGH — Non-null assertions on required env vars in middleware — runtime crash if missing
**File:** `middleware.ts:11–12`

`process.env.NEXT_PUBLIC_SUPABASE_URL!` — if the variable is absent in a preview environment, every request 500s.

**Fix:** Add a startup guard before the `createServerClient` call:
```ts
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
if (!supabaseUrl || !supabaseKey) throw new Error('Supabase env vars must be set')
```

---

### [TS-3] HIGH — Side effect (state setter call) inside a React state updater in `VoiceBiomarker`
**File:** `components/voice-biomarker/voice-biomarker.tsx:34–36`

```ts
setCountdown((prev) => {
  if (prev <= 1) {
    clearInterval(timerRef.current!)
    if (mountedRef.current) stopRecording()  // calls setPhase — side effect in updater
    return 0
  }
})
```
State updaters must be pure. This executes twice in React Strict Mode (React 18+), meaning `stopRecording` fires twice per countdown expiry.

**Fix:** Separate the countdown logic from the side effect:
```ts
timerRef.current = setInterval(() => {
  setCountdown(prev => Math.max(0, prev - 1))
}, 1000)

useEffect(() => {
  if (countdown === 0 && phase === 'recording') stopRecording()
}, [countdown, phase])
```

---

### [TS-4] HIGH — Hardcoded brand color hex values in chart components bypass design token system
**Files:** `components/progress/mood-chart.tsx:62–85`, `components/admin/charts.tsx:121,178–188`

`#4A7C59`, `#2D6B6B`, `#DC2626` hardcoded in 5+ places. If tenant brand changes, charts become inconsistent. The code already has a `// TODO(post-Gitex)` comment acknowledging this.

**Fix:** Where Recharts accepts string props, use CSS custom properties:
```ts
stroke="var(--color-primary)"
fill="var(--color-primary)"
```
For SVG `stopColor` (where `var()` is less reliable), derive from the tenant config object.

---

### [TS-5] MEDIUM — `getAdminDemoData()` called every render without `useMemo`
**File:** `components/admin/admin-dashboard.tsx:20`

Re-runs the full demo data generator on every re-render triggered by `highlightSection` state changes (which occur every 4 seconds).

**Fix:**
```ts
const demo = useMemo(() => getAdminDemoData(), [])
```

---

### [TS-6] MEDIUM — `handleAlertClick` leaks two `setTimeout` handles on unmount
**File:** `components/admin/admin-dashboard.tsx:22–28`

Both `setTimeout` IDs are discarded. The 4-second timer calls `setHighlightSection(null)` after unmount.

**Fix:** Store IDs in a ref and clear in a cleanup effect:
```ts
const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([])
useEffect(() => () => timerRefs.current.forEach(clearTimeout), [])
```

---

### [TS-7] MEDIUM — Magic number `6` for onboarding step count in 4 separate files
**Files:** `step-guard.tsx:12`, `middleware.ts:56`, `about-you.tsx:25`, `what-matters.tsx:19`, `(onboarding)/layout.tsx:6`

**Fix:** Define in `lib/onboarding-constants.ts`:
```ts
export const TOTAL_ONBOARDING_STEPS = 6
```
Import in all files.

---

### [TS-8] MEDIUM — `formatRelativeTime` hardcodes `'en-US'` locale
**File:** `lib/format-relative-time.ts:27–29`

Renders English day/month names even in Arabic mode.

**Fix:** Accept an optional locale parameter:
```ts
export function formatRelativeTime(updatedAt: string, locale = 'en-US'): string {
  const displayLocale = locale === 'ar' ? 'ar-AE' : 'en-US'
  return thenDate.toLocaleDateString(displayLocale, { weekday: 'long' })
}
```

---

### [TS-9] LOW — `BottomSheet` backdrop `div` has no keyboard dismiss handler
**File:** `packages/ui/src/components/bottom-sheet.tsx:17`

Clicking the backdrop closes the sheet; pressing Escape does not.

**Fix:**
```tsx
<div
  onClick={onClose}
  onKeyDown={(e) => e.key === 'Escape' && onClose()}
  role="presentation"
  className="fixed inset-0 z-40 bg-black/30"
/>
```

---

### [TS-10] LOW — Tailwind content scan missing `packages/theme` and `packages/tenant`
**File:** `apps/web/tailwind.config.ts:10–14`

Any Tailwind class strings added to those packages in the future will be silently purged in production.

**Fix:** Add to `content` array:
```ts
'../../packages/theme/src/**/*.{ts,tsx}',
'../../packages/tenant/src/**/*.{ts,tsx}',
```

---

## Category 6 — Performance & Mobile UX

### [PERF-1] HIGH — No iOS safe area insets on tab bar or BottomSheet; `viewport-fit=cover` missing
**Files:** `components/tab-bar.tsx:20`, `packages/ui/src/components/bottom-sheet.tsx:36`, `app/layout.tsx`

In standalone PWA mode on iPhone, the home indicator overlaps the bottom nav. `env(safe-area-inset-*)` always resolves to `0` without `viewport-fit=cover`.

**Fix 1:** Add to `app/layout.tsx`:
```tsx
export const viewport: Viewport = {
  viewportFit: 'cover',
  width: 'device-width',
  initialScale: 1,
}
```
**Fix 2:** Tab bar:
```tsx
<nav className={cn('border-t ... pb-[env(safe-area-inset-bottom)]', className)}>
```
**Fix 3:** BottomSheet content:
```tsx
<div className="p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">{children}</div>
```

---

### [PERF-2] HIGH — `scrollIntoView({ behavior: 'smooth' })` fires on every streaming chunk
**File:** `components/chat/chat-interface.tsx:211–213`

`messages` is a new array reference on every chunk. `smooth` scroll restart on each call causes visible stutter on low-end Android during streaming.

**Fix:**
```tsx
useEffect(() => {
  bottomRef.current?.scrollIntoView({ behavior: isStreaming ? 'instant' : 'smooth' })
}, [messages, isLoading])
```

---

### [PERF-3] HIGH — Recharts loaded eagerly on progress page (no `dynamic()`)
**Files:** `components/progress/mood-chart.tsx`, `app/(app)/progress/page.tsx:74`

`admin/charts.tsx` correctly wraps all chart components in `next/dynamic`. `MoodChart` does not, including ~200KB of d3/Recharts in the initial bundle.

**Fix:**
```tsx
const MoodChart = dynamic(
  () => import('@/components/progress/mood-chart').then(m => m.MoodChart),
  { ssr: false, loading: () => <Skeleton className="h-40 w-full" /> }
)
```

---

### [PERF-4] HIGH — 60KB Framer Motion bundled for a single opacity fade; no `prefers-reduced-motion` anywhere
**Files:** `components/chat/chat-fade-in.tsx`, `package.json:17`

`ChatFadeIn` is the only usage. The animation is a `opacity: 0 → 1` fade trivially achievable with CSS. There is zero `prefers-reduced-motion` handling in the entire codebase (confirmed by grep). WCAG 2.3.3 AA.

**Fix 1:** Replace with CSS animation and remove `framer-motion` from `package.json`:
```tsx
export function ChatFadeIn({ children }: { children: React.ReactNode }) {
  return <div className="flex h-full flex-col animate-fade-in">{children}</div>
}
```

**Fix 2:** Add to `globals.css`:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

### [PERF-5] HIGH — `max-w-md` (448px) still locks tablet portrait layout
**File:** `app/(app)/layout.tsx:9`

On a 768px tablet in portrait mode (below the `md` breakpoint), the content column is 448px wide and centered with empty space on both sides. This looks broken on iPad mini.

**Fix:** Remove the `max-w-md` cap or apply only for specific breakpoints where it is intentional.

---

### [PERF-6] MEDIUM — `progress/page.tsx` scroll container is broken — cannot scroll on mobile
**File:** `app/(app)/progress/page.tsx:46`

`overflow-y-auto` is on an auto-height `div` inside a parent with `overflow-hidden`. The element grows unbounded while `overflow-hidden` clips the content.

**Fix:** Add `h-full` to the progress page root div:
```tsx
<div className="flex flex-col gap-4 overflow-y-auto h-full p-4 pb-8">
```

---

### [PERF-7] MEDIUM — `BottomSheet` has no `max-h` or scroll container; long lists overflow off-screen
**File:** `packages/ui/src/components/bottom-sheet.tsx:36`

With 8+ history sessions the sheet pushes off the top of a 667px phone screen.

**Fix:**
```tsx
<div className="max-h-[70dvh] overflow-y-auto p-6">{children}</div>
```

---

### [PERF-8] MEDIUM — `ResponsivePanel` flashes `BottomSheet` on desktop for one paint frame (FOUC)
**File:** `packages/ui/src/components/responsive-panel.tsx:14`

`isDesktop` initialises as `false`. Desktop users see the bottom-sheet layout before the effect fires.

**Fix:** Use `null` initial state and return `null` until resolved:
```tsx
const [isDesktop, setIsDesktop] = useState<boolean | null>(null)
if (!open || isDesktop === null) return null
```

---

### [PERF-9] MEDIUM — Typing indicator missing `role="status"` — screen readers cannot detect Sage is typing
**File:** `components/chat/typing-indicator.tsx:3`

**Fix:**
```tsx
<div role="status" aria-label={locale === 'ar' ? 'Sage يكتب...' : 'Sage is typing...'} ...>
```

---

### [PERF-10] LOW — `dynamic(Promise.resolve(...))` in admin charts does not actually code-split
**File:** `components/admin/charts.tsx:306–324`

`Promise.resolve(LocalComponent)` resolves synchronously — Webpack/Turbopack do not emit a separate chunk. The `ssr: false` effect is real, but lazy network loading is not achieved.

**Fix:** Move each chart implementation to its own file and use actual `import()`:
```ts
export const MoodTrendChart = dynamic(() => import('./mood-trend-chart-impl'))
```

---

### [PERF-11] LOW — `VoiceBiomarker` analysis `setTimeout` not cleared on unmount
**File:** `components/voice-biomarker/voice-biomarker.tsx:49`

The 2500ms timer handle is not stored, so it cannot be cancelled. If the user navigates away during "Analysing…", the timer fires into a dead component.

**Fix:**
```ts
const analysisTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
analysisTimerRef.current = setTimeout(() => { if (mountedRef.current) setPhase('result') }, 2500)
// in cleanup: if (analysisTimerRef.current) clearTimeout(analysisTimerRef.current)
```

---

## Prioritised Fix Sequence

### Pre-Gitex (Hard Blockers — must fix before any user exposure)

| Priority | ID | Finding |
|----------|----|---------|
| P0 | PWA-1 | SW never registered — entire offline/PWA is non-functional |
| P0 | PWA-3 | Maskable icon is a placeholder — Android adaptive icon broken |
| P0 | STATE-5 | Sign-out leaks PII (onboarding data) to next user on shared device |
| P0 | STATE-2 | No Zod validation on `/api/chat` — prompt injection vector |
| P0 | STATE-1 | Admin page bypasses auth via `revalidate=60` — clinical data exposed |
| P1 | TS-1 | `responsive-panel.tsx` compile error (missing React import) |
| P1 | TS-2 | Env var non-null assertions in middleware — 500 on missing env var |
| P1 | A11Y-6 | Crisis card no `role="alert"` — safety-critical, screen reader invisible |
| P1 | PWA-2 | SW update race condition — users can reload with stale SW |
| P1 | PERF-1 | No iOS safe area insets — tab bar hidden behind home indicator on iPhone |

### Sprint 6 Quality (before broader launch)

| ID | Finding |
|----|---------|
| ARCH-1 | Progress page — convert to Server Component |
| ARCH-2 | Deduplicate `CRISIS_SIGNAL` constant |
| ARCH-3 | StepGuard children flash during redirect |
| ARCH-5 | Add `loading.tsx` / `error.tsx` / `not-found.tsx` |
| STATE-4 | Delete dead `chat-store.ts` |
| STATE-3 | Zod validation on `/api/feedback` |
| STATE-6 | Rate limiting on `/api/chat` |
| A11Y-1 | ARIA live region on chat message container |
| A11Y-2 | Form input `<label>` elements |
| A11Y-3 | Skip-to-content link |
| A11Y-4/5 | Focus traps in BottomSheet and ResponsivePanel |
| PERF-2 | Fix streaming scroll jank |
| PERF-4 | Remove Framer Motion; add `prefers-reduced-motion` |
| PERF-6 | Fix progress page scroll (broken on mobile) |
| PERF-7 | Fix BottomSheet overflow (history list clips off-screen) |
| TS-3 | Side effect in VoiceBiomarker state updater |
| TS-7 | Consolidate magic `6` constant for onboarding steps |
| TS-8 | `formatRelativeTime` hardcoded `'en-US'` locale |
| ARCH-4 | Replace `<button>+router.push` in HistoryPanel with `<Link>` |
| A11Y-7 | Mirror send arrow `→` for RTL |
| A11Y-13 | Apply both font variables to `<html>` always |

### Post-Gitex (Debt)

| ID | Finding |
|----|---------|
| PWA-4 | Tighten manifest scope away from `/` |
| PWA-5 | Add SW `activate` handler for cache eviction |
| PERF-3 | Lazy-load Recharts on progress page |
| PERF-5 | Fix `max-w-md` tablet layout |
| PERF-8 | Fix `ResponsivePanel` FOUC |
| TS-4 | Replace hardcoded chart colors with CSS custom properties |
| TS-5 | `useMemo` on `getAdminDemoData()` |
| TS-6 | Clear `setTimeout` handles in admin dashboard |
| STATE-9 | Date cutoffs on progress queries |
| ARCH-6 | Split `'use client'` out of auth page files |
| A11Y-8–14 | Remaining MEDIUM accessibility fixes |
| PERF-10 | Fix `dynamic(Promise.resolve(...))` in admin charts |
| TS-10 | Add `packages/theme` and `packages/tenant` to Tailwind content scan |

---

## What Is Working Well

- `<html lang={locale} dir={dir}>` set server-side from cookie — correct bilingual pattern
- Auth layout uses `border-e`, `ms-auto`, `end-4` — logical CSS properties for RTL
- Crisis card phone numbers are `<a href="tel:...">` with bilingual `aria-label` — correct
- Crisis card uses `dir="auto"` on AI-generated content — correct for mixed-direction
- Arabic phone numbers wrapped in `<span dir="ltr">` — correct per RFC 3966
- `AppSideNav` sign-out dialog has manual Tab trap and Escape handler
- `FeedbackButtons` correctly uses `aria-pressed`
- `SessionList` uses `aria-current="page"` on active session links
- All interactive icon buttons have ≥44×44px touch targets
- `admin/charts.tsx` uses `ssr: false` dynamic imports (intent correct, implementation has the code-split gap noted in PERF-10)
- Monorepo package boundaries are respected throughout
- Supabase `getUser()` (not `getSession()`) used correctly in server contexts where auth was implemented
