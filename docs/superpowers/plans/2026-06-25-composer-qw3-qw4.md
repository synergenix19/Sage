# Composer Polish — QW4 (placeholder + mic icon + honest voice affordance) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the chat composer more inviting and honest — a warmer Khaleeji placeholder and a real SVG mic icon (replacing the raw emoji), without overselling the deferred voice feature.

**Architecture:** Frontend-only, in the composer component (`input-bar.tsx`). The placeholder copy changes; the `🎙` emoji becomes an inline SVG mic (mirroring the existing send-button SVG pattern); and the voice button degrades gracefully when the browser has no `SpeechRecognition`. A contrast assertion for the mic stroke is added to the existing theme gate.

**Tech Stack:** Next.js (App Router) + React + TypeScript (strict) in `apps/web`; Tailwind via CSS-variable tokens; locale via `useLocaleStore` inline `locale === 'ar' ? … : …` ternaries; tests in Vitest + @testing-library/react.

## Global Constraints

- **Base:** executes on `main` at `616c5bf` (deployed centered-column + 15px-font build). `input-bar.tsx` currently has a `max-w-3xl` centered controls wrapper and a `🎙` emoji voice button whose click handler is `if (!SR) return` (a silent no-op when unsupported).
- **QW3 (AI disclaimer) is OUT of scope by product decision** — the AI-fallibility notice already appears once during onboarding; a persistent always-on line would clutter the chat. Do not add it.
- **The placeholder is a deliberate Khaleeji *register AND gender* choice, not a translation.** Conversational UI uses Khaleeji dialect (formal content uses MSA); the L0 persona is a warm Khaleeji wellness companion, so the first conversational beat should be Khaleeji. **Gender is the substantive catch:** 2nd-person Khaleeji address is grammatically gendered — masculine `بالك` (balak) vs feminine `بالچ`/`بالش` (balich) — and defaulting to masculine mis-greets every female user on the very first beat (the intelligence eval flags this as C-5 `gender_address` sensitivity). The implemented default below (`وش في البال؟`) is **gender-neutral** — it uses `البال` ("the mind") with no 2nd-person suffix, so it sidesteps the inflection. The native-speaker pass **must deliberately confirm both the register and the gender treatment before merge** (neutral as shipped, vs a masculine/feminine pair keyed off the user's profile gender). This is a merge gate.
- **No em dashes in user-facing copy.** (Project rule.)
- **Voice/ASR is a Full Build feature (TD8 deferred); the POC is text-first.** The mic must not present a confident affordance that dead-ends. Where `SpeechRecognition` is unavailable it must visibly degrade (disabled + "coming soon"), not silently no-op.
- **Preserve existing a11y contracts:** the voice button keeps a stable `aria-label` (`Voice input` / `الإدخال الصوتي`) and `aria-pressed`; the textarea keeps its `aria-label` (`Message` / `اكتب رسالتك`); both buttons keep `h-11 w-11` (44px) and the textarea its focus ring. `input-bar.test.tsx` selects by these aria-labels — keep them byte-identical. The "coming soon" state is conveyed via `title` + `disabled`, NOT by changing the aria-label.
- **Tailwind tokens only** — no hardcoded hex.
- **Verify on the production build** (`next build` → `next start`) in **both EN and AR** plus mobile (390px). This repo has no Vercel PR preview; prod deploy is a manual `vercel --prod --scope team_QIkBcxIyX24wygy4smltVtRK`.

---

### Task 1: Khaleeji placeholder + SVG mic icon + contrast gate

Swaps the bare `Message…` placeholder for a warm Khaleeji invitation and the raw `🎙` emoji (renders inconsistently across OS/browsers) for a clean inline SVG mic. Adds a computed-contrast assertion for the mic stroke (a UI component) to the existing theme gate.

**Files:**
- Modify: `apps/web/components/chat/input-bar.tsx`
- Test: `apps/web/components/chat/__tests__/input-bar.test.tsx`
- Test: `packages/theme/src/__tests__/contrast.test.ts`

**Interfaces:**
- Consumes: existing `locale` from `useLocaleStore`, `listening` state.
- Produces: no new exported symbols.

- [ ] **Step 1: Write the failing component tests**

Append to `apps/web/components/chat/__tests__/input-bar.test.tsx`:

```tsx
describe('InputBar — QW4 placeholder & mic icon', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'en' }))
  })

  it('shows the warmer English placeholder', () => {
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByPlaceholderText("What's on your mind?")).toBeInTheDocument()
  })

  it('shows the gender-neutral Khaleeji placeholder when locale is ar', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useLocaleStore).mockImplementation((selector: any) => selector({ locale: 'ar' }))
    render(<InputBar onSend={vi.fn()} />)
    expect(screen.getByPlaceholderText('وش في البال؟')).toBeInTheDocument()
  })

  it('renders the voice button as an SVG icon, not the raw emoji', () => {
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    expect(btn.querySelector('svg')).not.toBeNull()
    expect(btn.textContent ?? '').not.toContain('🎙')
  })
})
```

- [ ] **Step 2: Run the component tests to verify they fail**

Run: `cd apps/web && npx vitest run components/chat/__tests__/input-bar.test.tsx`
Expected: the three new tests FAIL — placeholder is `Message…`, button renders the `🎙` text node, not an `<svg>`.

- [ ] **Step 3: Replace the emoji with an SVG mic and update the placeholder**

In `apps/web/components/chat/input-bar.tsx`, replace the emoji child of the voice button:

```tsx
        🎙
```

with an inline SVG (note: NO `scale-x-[-1]` — the mic is symmetric and must not be mirrored in RTL like the send arrow is):

```tsx
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
        >
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
```

Then change the textarea placeholder. Replace:

```tsx
        placeholder={locale === 'ar' ? 'رسالة...' : 'Message…'}
```

with (gender-neutral Khaleeji — `البال`, no 2nd-person suffix; see Global Constraints):

```tsx
        placeholder={locale === 'ar' ? 'وش في البال؟' : "What's on your mind?"}
```

- [ ] **Step 4: Run the component tests to verify they pass**

Run: `cd apps/web && npx vitest run components/chat/__tests__/input-bar.test.tsx`
Expected: PASS — the three new tests plus all pre-existing ones (which query by `aria-label`, unchanged).

- [ ] **Step 5: Write the failing contrast assertion**

The SVG mic uses `stroke="currentColor"`, inheriting `text-secondary` on the composer bar's `surface` background — a UI component, so WCAG 1.4.11 requires ≥3:1. Add to `packages/theme/src/__tests__/contrast.test.ts`, inside the existing `describe('WCAG 2.1 AA contrast — chat UI colour pairings', …)` block:

```ts
  it('composer mic icon (UI component): textSecondary on surface >= 3:1', () => {
    expect(ratio(c.textSecondary, c.surface)).toBeGreaterThanOrEqual(3.0)
  })
```

- [ ] **Step 6: Run the contrast gate to verify it passes**

Run: `cd packages/theme && npx vitest run src/__tests__/contrast.test.ts`
Expected: PASS — `textSecondary #6B7280` on `surface #F9F8F6` computes 4.55:1, above the 3:1 bar (the assertion fails CI if a future token edit drops it below 3:1).

- [ ] **Step 7: Commit**

```bash
git add apps/web/components/chat/input-bar.tsx apps/web/components/chat/__tests__/input-bar.test.tsx packages/theme/src/__tests__/contrast.test.ts
git commit -m "feat(chat): Khaleeji placeholder + SVG mic icon + mic contrast gate (QW4)"
```

---

### Task 2: Honest voice affordance — graceful degradation when unsupported

The polished mic must not look live where it cannot work. Detect `SpeechRecognition` support on mount; when absent, render the button disabled with a "coming soon" title so it does not present a confident affordance that dead-ends. The `aria-label` stays stable (existing tests depend on it); "coming soon" is conveyed via `title` + `disabled`.

**Files:**
- Modify: `apps/web/components/chat/input-bar.tsx`
- Test: `apps/web/components/chat/__tests__/input-bar.test.tsx`

**Interfaces:**
- Consumes: `window.SpeechRecognition ?? window.webkitSpeechRecognition`.
- Produces: no new exported symbols. Adds internal `supported` state.

- [ ] **Step 1: Write the failing tests**

Append to `apps/web/components/chat/__tests__/input-bar.test.tsx`:

```tsx
describe('InputBar — QW4 honest voice affordance', () => {
  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).SpeechRecognition
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).webkitSpeechRecognition
  })

  it('disables the voice button with a "coming soon" title when unsupported', async () => {
    // jsdom has no SpeechRecognition by default
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    await vi.waitFor(() => expect(btn).toBeDisabled())
    expect(btn).toHaveAttribute('title', expect.stringMatching(/coming soon/i))
  })

  it('enables the voice button when SpeechRecognition is available', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(window as any).SpeechRecognition = vi.fn()
    render(<InputBar onSend={vi.fn()} />)
    const btn = screen.getByRole('button', { name: 'Voice input' })
    await vi.waitFor(() => expect(btn).toBeEnabled())
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd apps/web && npx vitest run components/chat/__tests__/input-bar.test.tsx`
Expected: the two new tests FAIL — the button is currently always enabled and has no "coming soon" title.

- [ ] **Step 3: Add support detection state**

In `apps/web/components/chat/input-bar.tsx`, the component already imports `useState`, `useRef`, `useEffect`. Add a `supported` state and detect it on mount. Find:

```tsx
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const locale = useLocaleStore((s) => s.locale)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    return () => { recognitionRef.current?.abort() }
  }, [])
```

and replace with:

```tsx
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  // Voice is a Full Build feature; in browsers without the Web Speech API it must not
  // present a clickable affordance that dead-ends. Default true to avoid an SSR flash;
  // confirmed on mount. (window is undefined during SSR, hence the effect.)
  const [supported, setSupported] = useState(true)
  const locale = useLocaleStore((s) => s.locale)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
    setSupported(Boolean(SR))
    return () => { recognitionRef.current?.abort() }
  }, [])
```

- [ ] **Step 4: Reflect support in the voice button**

In the same file, update the voice button to disable + retitle when unsupported (keep `aria-label` stable). Replace:

```tsx
      <button
        onClick={startVoice}
        aria-label={locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input'}
        aria-pressed={listening}
        className={cn(
          'flex h-11 w-11 items-center justify-center rounded-full transition-colors',
          listening
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
        )}
      >
```

with:

```tsx
      <button
        onClick={startVoice}
        disabled={!supported}
        aria-label={locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input'}
        title={
          supported
            ? (locale === 'ar' ? 'الإدخال الصوتي' : 'Voice input')
            : (locale === 'ar' ? 'الإدخال الصوتي قريباً' : 'Voice input coming soon')
        }
        aria-pressed={listening}
        className={cn(
          'flex h-11 w-11 items-center justify-center rounded-full transition-colors',
          !supported && 'cursor-not-allowed opacity-40',
          listening
            ? 'bg-[var(--color-primary)] text-white'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
        )}
      >
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd apps/web && npx vitest run components/chat/__tests__/input-bar.test.tsx`
Expected: PASS — both new tests plus all earlier ones. (Existing aria-label/aria-pressed tests still pass because the aria-label is unchanged and `disabled` does not affect `aria-pressed`.)

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/chat/input-bar.tsx apps/web/components/chat/__tests__/input-bar.test.tsx
git commit -m "feat(chat): degrade voice button to 'coming soon' when unsupported (QW4)"
```

---

## Verification (after both tasks)

- [ ] Unit: `cd apps/web && npx vitest run components/chat` and `cd packages/theme && npx vitest run` — all green.
- [ ] Production build parity: `cd apps/web && npx next build` (exit 0), then `npx next start -p 3000`.
- [ ] Visual check in **both languages** at wide and mobile (390px) widths — reuse the seeding pattern in `apps/web/playwright/chat-layout.spec.ts`:
  - EN: placeholder reads "What's on your mind?"; the voice control is a crisp mic icon (not an emoji).
  - AR: toggle عربي, confirm the gender-neutral Khaleeji placeholder `وش في البال؟` renders RTL; confirm the mic icon is NOT mirrored (it must not get the `scale-x-[-1]` the send arrow uses).
  - In a browser without the Web Speech API (or stub `window.SpeechRecognition = undefined`), confirm the mic is visibly disabled with the "coming soon" tooltip rather than a silent no-op.
- [ ] **MERGE GATE:** the Khaleeji placeholder has been confirmed by a native Khaleeji speaker for BOTH register and gender — the shipped default `وش في البال؟` is gender-neutral (sidesteps the inflection); the native pass confirms it (or replaces it with a profile-gender-keyed masculine/feminine pair). No em dashes in any new copy.
- [ ] Pre-flight done: grepped the suite for a voice-button click-path test — none exists (only presence + `aria-pressed` assertions), so Task 2's jsdom-disabled button breaks nothing.

## Out of scope (deliberately)

- **QW3 AI disclaimer** — dropped by product decision (already shown once at onboarding; a persistent line clutters the chat).
- **Abby's "Tools" pill** — Sage has no composer tools feature (YAGNI).
- **Moving the language toggle into the composer** — separate layout decision, not part of this quick win.
- **Hiding the mic entirely vs. "coming soon"** — this plan keeps the button visible-but-disabled when unsupported. If product prefers to not signal voice at all in the POC, gating the button's render on a capability flag (cf. `capabilities.voiceBiomarker`) is a one-line alternative; flagged, not chosen here.
