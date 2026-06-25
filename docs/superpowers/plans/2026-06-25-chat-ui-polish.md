# Chat UI Polish (Abby-parity quick wins #1, #2, #5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Sage chat UI read as a considered product rather than a default chat widget by (1) rendering long assistant answers as typographic prose instead of trapping them in a bubble, (2) giving the two speakers distinct colours (neutral assistant bubble vs. green user bubble), and (5) softening the heavy solid-green sidebar buttons.

**Architecture:** Three localized, frontend-only changes in the `cdai` monorepo. A new neutral surface design token is added to the theme/tenant layer; `message-bubble.tsx` consumes it and gains a long-form branch; the sidebar buttons (`app-side-nav.tsx` desktop + `history-panel.tsx` mobile drawer) switch from solid-fill to tinted/outline styles with more whitespace. No backend, no API, no new dependencies.

**Tech Stack:** Next.js (App Router) + React + TypeScript (strict) in `apps/web`; Tailwind CSS driven by CSS variables; design tokens in `packages/theme` + `packages/tenant`; tests in Vitest + @testing-library/react.

## Global Constraints

- **No hardcoded hex in components.** Components reference CSS-variable tokens only, e.g. `bg-[var(--color-surface-muted)]`. Hex values live solely in `packages/tenant/src/configs/sage.ts`. (Existing repo convention — every colour in `message-bubble.tsx` and `app-side-nav.tsx` already uses `var(--color-*)`.)
- **Preserve accessibility:** every interactive control keeps `min-h-[44px]` and its `focus-visible:ring-*` classes.
- **Preserve RTL + L4 structure:** the assistant content element must keep `whitespace-pre-wrap` and the `dir={message.direction ?? 'auto'}` attribute in every branch. These are pinned by existing tests in `message-bubble.test.tsx` (the `L4 structure & RTL rendering` describe block) and must stay green.
- **No em dashes in user-facing copy strings.** (Project rule.) These tasks change classes/tokens, not copy, so no copy is added.
- **Run tests from `apps/web`:** `npx vitest run <path>` (monorepo uses a vitest workspace; run per-package).

---

### Task 1: Add a neutral assistant-surface design token

Introduces `surfaceMuted` (a warm-neutral grey) so the assistant bubble can be visually distinct from both the green user bubble and the white canvas. Separated from Task 2 because a reviewer could approve the token addition while still debating the bubble markup.

**Files:**
- Modify: `packages/tenant/src/types.ts` (add `surfaceMuted` to the colours interface)
- Modify: `packages/tenant/src/configs/sage.ts` (add the hex value)
- Modify: `packages/theme/src/css-vars.ts` (map it to `--color-surface-muted`)
- Modify: `packages/theme/src/tailwind-preset.ts` (expose `surface-muted` to Tailwind)
- Test: `packages/tenant/src/__tests__/tenant.test.ts` (add to required-keys list)
- Test: `packages/theme/src/__tests__/theme.test.ts` (assert the CSS var)
- Create: `packages/theme/src/__tests__/contrast.test.ts` (WCAG 2.1 AA contrast gate — non-optional in this project)

**Interfaces:**
- Produces: CSS variable `--color-surface-muted` (value `#F3F2F0`) and Tailwind token `surface-muted`. Consumed by Task 2.

**Measured contrast (computed against the sage hex values; the test below pins these so a future hex edit can't silently break AA):**
- `primaryDark #3D6A4B` text on `surfaceTinted #EAF0EA` (softened buttons + active tab) = **5.40:1** — PASS (and higher than the current white-on-`primary` button at 4.86:1).
- `textPrimary #111827` on `surfaceMuted #F3F2F0` (neutral bubble) = **15.86:1** — PASS.
- `textPrimary #111827` on white canvas (long-form prose) = **17.74:1** — PASS.
- Note: the bubble's hairline `border #E5E7EB` vs white canvas is 1.24:1. This is decorative, not a WCAG 1.4.11 case (the border is not the only thing identifying the component or a state — the `surfaceMuted` fill and the text carry that), so it is not asserted. Bubble *visibility* against the canvas is checked manually in the final Verification step instead.

- [ ] **Step 1: Write the failing token test (tenant)**

In `packages/tenant/src/__tests__/tenant.test.ts`, the required-keys array currently is:

```ts
const required = ['primary', 'primaryDark', 'secondary', 'surface',
  'surfaceTinted', 'textPrimary', 'textSecondary', 'border', 'crisis']
```

Add `'surfaceMuted'`:

```ts
const required = ['primary', 'primaryDark', 'secondary', 'surface',
  'surfaceTinted', 'surfaceMuted', 'textPrimary', 'textSecondary', 'border', 'crisis']
```

- [ ] **Step 2: Write the failing token test (theme)**

In `packages/theme/src/__tests__/theme.test.ts`, add an assertion alongside the existing `--color-primary` check:

```ts
expect(vars['--color-surface-muted']).toBe('#F3F2F0')
```

- [ ] **Step 3: Run both tests to verify they fail**

Run: `cd packages/tenant && npx vitest run && cd ../theme && npx vitest run`
Expected: tenant FAILS (`surfaceMuted` missing on sage config) and theme FAILS (`--color-surface-muted` is undefined).

- [ ] **Step 4: Add the field to the colours type**

In `packages/tenant/src/types.ts`, add `surfaceMuted` next to `surfaceTinted`:

```ts
    surface: string
    surfaceTinted: string
    surfaceMuted: string
```

- [ ] **Step 5: Add the hex value to the sage config**

In `packages/tenant/src/configs/sage.ts`, add the line directly after `surfaceTinted`:

```ts
      surface:       '#F9F8F6',
      surfaceTinted: '#EAF0EA',
      surfaceMuted:  '#F3F2F0',
```

- [ ] **Step 6: Map the token to a CSS variable**

In `packages/theme/src/css-vars.ts`, add the line after `--color-surface-tinted`:

```ts
    '--color-surface-tinted': brand.colors.surfaceTinted,
    '--color-surface-muted':  brand.colors.surfaceMuted,
```

- [ ] **Step 7: Expose the token to Tailwind**

In `packages/theme/src/tailwind-preset.ts`, add the line after `'surface-tinted'`:

```ts
        'surface-tinted':'var(--color-surface-tinted)',
        'surface-muted': 'var(--color-surface-muted)',
```

- [ ] **Step 8: Run both tests to verify they pass**

Run: `cd packages/tenant && npx vitest run && cd ../theme && npx vitest run`
Expected: PASS for both packages.

- [ ] **Step 9: Write the WCAG AA contrast gate**

Create `packages/theme/src/__tests__/contrast.test.ts`. It computes the WCAG 2.1 relative-luminance contrast ratio straight from the sage brand hex values, so the assertions fail if anyone later darkens a surface or lightens a text colour below AA.

```ts
import { describe, it, expect } from 'vitest'
import { sage } from '@cdai/tenant/configs/sage'

// WCAG 2.1 relative luminance + contrast ratio (https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio)
function channel(c: number): number {
  const s = c / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}
function luminance(hex: string): number {
  const h = hex.replace('#', '')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}
function ratio(fg: string, bg: string): number {
  const a = luminance(fg)
  const b = luminance(bg)
  const [hi, lo] = a > b ? [a, b] : [b, a]
  return (hi + 0.05) / (lo + 0.05)
}

const AA_NORMAL = 4.5
const WHITE = '#FFFFFF'

describe('WCAG 2.1 AA contrast — chat UI colour pairings', () => {
  const c = sage.brand.colors

  it('softened button / active tab: primaryDark text on surfaceTinted >= 4.5:1', () => {
    expect(ratio(c.primaryDark, c.surfaceTinted)).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('neutral assistant bubble: textPrimary on surfaceMuted >= 4.5:1', () => {
    expect(ratio(c.textPrimary, c.surfaceMuted)).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('long-form prose: textPrimary on white canvas >= 4.5:1', () => {
    expect(ratio(c.textPrimary, WHITE)).toBeGreaterThanOrEqual(AA_NORMAL)
  })

  it('button hover: white text on primary >= 4.5:1', () => {
    expect(ratio(WHITE, c.primary)).toBeGreaterThanOrEqual(AA_NORMAL)
  })
})
```

- [ ] **Step 10: Run the contrast gate to verify it passes**

Run: `cd packages/theme && npx vitest run src/__tests__/contrast.test.ts`
Expected: PASS — all four assertions (5.40, 15.86, 17.74, 4.86 respectively). If `surfaceMuted` from Step 5 is missing the test throws on `c.surfaceMuted` being undefined, so this also re-confirms Task 1's wiring.

- [ ] **Step 11: Commit**

```bash
git add packages/tenant packages/theme
git commit -m "feat(theme): add surface-muted token + WCAG AA contrast gate"
```

---

### Task 2: Neutral short-AI bubble + long-form typographic rendering (quick wins #1 + #2)

Both changes live in the same JSX block in `message-bubble.tsx`, so they ship together. The assistant render gains two branches: long/multi-line answers render as borderless typographic prose (a wider column, no fill); short turns render in the new neutral bubble. The user bubble is unchanged. `whitespace-pre-wrap` and `dir` stay on every branch so the existing RTL/L4 tests keep passing.

**Files:**
- Modify: `apps/web/components/chat/message-bubble.tsx`
- Test: `apps/web/components/chat/__tests__/message-bubble.test.tsx`

**Interfaces:**
- Consumes: `--color-surface-muted` from Task 1.
- Produces: no new exported symbols (same `MessageBubble` signature).

- [ ] **Step 1: Write the failing tests**

Append a new describe block to `apps/web/components/chat/__tests__/message-bubble.test.tsx`:

```tsx
// Quick wins #1 (long-form prose, no bubble) and #2 (neutral short-AI bubble).
describe('MessageBubble — speaker styling & long-form prose', () => {
  it('renders a multi-line assistant answer without a bubble (typographic prose)', () => {
    const long = 'Here are several resources:\n1. first point\n2. second point'
    render(<MessageBubble message={{ ...base, role: 'ai', content: long }} />)
    const el = screen.getByText(/Here are several resources/)
    // no bubble: no rounded fill, no surface background
    expect(el.className).not.toContain('rounded-2xl')
    expect(el.className).not.toContain('color-surface')
    // structure + direction still preserved
    expect(el.className).toContain('whitespace-pre-wrap')
    expect(el.textContent).toBe(long)
  })

  it('renders a long single-line assistant answer (>280 chars) without a bubble', () => {
    const long = 'a'.repeat(300)
    render(<MessageBubble message={{ ...base, role: 'ai', content: long }} />)
    const el = screen.getByText(long)
    expect(el.className).not.toContain('rounded-2xl')
  })

  it('renders a short assistant turn in the neutral bubble, not the green tint', () => {
    render(<MessageBubble message={{ ...base, role: 'ai', content: 'Sure, I can help.' }} />)
    const el = screen.getByText('Sure, I can help.')
    expect(el.className).toContain('bg-[var(--color-surface-muted)]')
    expect(el.className).not.toContain('surface-tinted')
    expect(el.className).toContain('rounded-2xl')
  })

  it('keeps the user bubble green and bubbled', () => {
    render(<MessageBubble message={{ ...base, role: 'user', content: 'Hi' }} />)
    const el = screen.getByText('Hi')
    expect(el.className).toContain('bg-[var(--color-primary-dark)]')
    expect(el.className).toContain('rounded-2xl')
  })

  // RTL on the NEW long-form branch: the existing L4/RTL block only covers short,
  // single-line fixtures. A long Arabic answer must still resolve right-to-left and
  // keep its numbered-list line structure when rendered as borderless prose.
  it('renders a long Arabic answer right-to-left with list lines preserved (no bubble)', () => {
    const arLong = 'إليك بعض التقنيات:\n1. التنفس البطيء العميق\n2. تمرين التأريض الحسي'
    render(
      <MessageBubble message={{ ...base, role: 'ai', content: arLong, direction: 'rtl' }} />
    )
    const el = screen.getByText(/إليك بعض التقنيات/)
    expect(el).toHaveAttribute('dir', 'rtl')
    expect(el.className).toContain('whitespace-pre-wrap')
    expect(el.className).not.toContain('rounded-2xl') // long-form: no bubble
    expect(el.textContent).toBe(arLong)               // newlines intact
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/web && npx vitest run components/chat/__tests__/message-bubble.test.tsx`
Expected: the five new tests FAIL (current code always uses `rounded-2xl` and `bg-[var(--color-surface-tinted)]` for AI; there is no long-form branch). The Arabic long-form test fails on the `rounded-2xl` assertion for the same reason.

- [ ] **Step 3: Rewrite the component**

Replace the entire body of `apps/web/components/chat/message-bubble.tsx` with:

```tsx
import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'
import { FeedbackButtons } from './feedback-buttons'

interface Props {
  message: ChatMessage
  supabaseId?: string
  onFeedback?: (messageId: string, value: 1 | -1) => void
}

// Long or multi-line assistant answers (resource lists, step-by-step guidance) read
// better as typographic prose than inside a chat bubble. Short conversational turns
// (offers, acknowledgements) stay bubbled. Multi-line is the strongest signal because
// the backend emits numbered lists with newlines (preserved by whitespace-pre-wrap).
function isLongForm(content: string): boolean {
  return content.length > 280 || content.includes('\n')
}

export function MessageBubble({ message, supabaseId, onFeedback }: Props) {
  if (message.role === 'crisis') return null
  if (message.role === 'system') {
    return (
      <div className="mx-auto w-full max-w-xs rounded-xl border border-[var(--color-border)] px-4 py-2 text-center text-xs text-[var(--color-text-secondary)]">
        {message.content}
      </div>
    )
  }

  const isUser = message.role === 'user'
  const longForm = !isUser && isLongForm(message.content)

  return (
    <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        dir={message.direction ?? 'auto'}
        className={cn(
          // whitespace-pre-wrap renders the L4 line structure (numbered lists) instead of
          // collapsing newlines to run-on text. Direction is authoritative from the backend
          // (message.direction, derived from detected_language); dir="auto" is the fallback.
          // These two must stay on every branch (pinned by the RTL/L4 tests).
          'whitespace-pre-wrap text-sm leading-relaxed',
          isUser
            ? 'max-w-[78%] rounded-2xl rounded-ee-sm bg-[var(--color-primary-dark)] px-4 py-2.5 text-white'
            : longForm
              // #1 Long-form assistant answer: no bubble. Typographic prose in a wider column.
              ? 'max-w-[680px] text-[15px] leading-7 text-[var(--color-text-primary)]'
              // #2 Short assistant turn: neutral bubble with hairline border (was green tint).
              : 'max-w-[78%] rounded-2xl rounded-es-sm border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-2.5 text-[var(--color-text-primary)]'
        )}
      >
        {message.content}
      </div>
      {!isUser && supabaseId && onFeedback && (
        <FeedbackButtons messageId={supabaseId} onFeedback={onFeedback} />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run the full message-bubble suite to verify all pass**

Run: `cd apps/web && npx vitest run components/chat/__tests__/message-bubble.test.tsx`
Expected: PASS — the four new tests plus all pre-existing tests (including the `L4 structure & RTL rendering` block, which still finds `whitespace-pre-wrap` and the `dir` attribute on its short/no-newline fixtures).

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/chat/message-bubble.tsx apps/web/components/chat/__tests__/message-bubble.test.tsx
git commit -m "feat(chat): typographic long-form answers + neutral assistant bubble"
```

---

### Task 3: Soften the solid-green sidebar buttons (quick win #5)

The desktop "New conversation" button and the active nav tab are heavy solid-green blocks; the mobile drawer's "New conversation" button is the same. Switch them to a soft tinted style (tinted fill, green text, fills green on hover) and add a little vertical whitespace. Two surfaces are updated so desktop and mobile stay consistent.

**Files:**
- Modify: `apps/web/components/app-side-nav.tsx` (new-conversation button + active nav-tab style + spacing)
- Modify: `apps/web/components/chat/history-panel.tsx` (mobile drawer new-conversation button)
- Test: `apps/web/components/__tests__/app-side-nav.test.tsx`

**Interfaces:**
- Consumes: existing `--color-surface-tinted`, `--color-primary`, `--color-primary-dark` tokens. No new tokens.
- Produces: no new exported symbols.

- [ ] **Step 1: Write the failing test**

Append to `apps/web/components/__tests__/app-side-nav.test.tsx`:

```tsx
// Quick win #5: the New conversation button is softened from solid-green to tinted.
it('renders the New conversation button with a tinted (not solid-primary) fill', () => {
  const btn = screen.getByRole('button', { name: 'New conversation' })
  expect(btn.className).toContain('bg-[var(--color-surface-tinted)]')
  expect(btn.className).not.toContain('bg-[var(--color-primary)]')
})
```

Note: this assumes the suite renders `AppSideNav` in English with an accessible "New conversation" button (the component sets `aria-label="New conversation"` when `locale !== 'ar'`). If the existing suite uses a different render helper or locale, reuse that suite's existing setup/`beforeEach` rather than adding a new render — match the file's established pattern.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd apps/web && npx vitest run components/__tests__/app-side-nav.test.tsx`
Expected: FAIL — the button currently has `bg-[var(--color-primary)]`, not `bg-[var(--color-surface-tinted)]`.

- [ ] **Step 3: Soften the desktop New conversation button**

In `apps/web/components/app-side-nav.tsx`, change the button wrapper spacing and the button classes. Replace:

```tsx
      {/* New conversation button */}
      <div className="px-3 pb-2">
        <button
          onClick={handleNewChat}
          aria-label={locale === 'ar' ? 'محادثة جديدة' : 'New conversation'}
          className={cn(
            'flex w-full min-h-[44px] items-center justify-center gap-2 rounded-xl',
            'bg-[var(--color-primary)] text-white text-sm font-medium',
            'hover:bg-[var(--color-primary-dark)] transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]'
          )}
        >
          {locale === 'ar' ? '+ محادثة جديدة' : '+ New conversation'}
        </button>
      </div>
```

with:

```tsx
      {/* New conversation button — softened from solid-green to tinted (#5) */}
      <div className="px-3 pb-3 pt-1">
        <button
          onClick={handleNewChat}
          aria-label={locale === 'ar' ? 'محادثة جديدة' : 'New conversation'}
          className={cn(
            'flex w-full min-h-[44px] items-center justify-center gap-2 rounded-xl',
            'bg-[var(--color-surface-tinted)] text-[var(--color-primary-dark)] text-sm font-medium',
            'hover:bg-[var(--color-primary)] hover:text-white transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]'
          )}
        >
          {locale === 'ar' ? '+ محادثة جديدة' : '+ New conversation'}
        </button>
      </div>
```

- [ ] **Step 4: Soften the active nav tab**

In the same file, in the `ALL_TABS.map` block, replace the active/inactive class expression:

```tsx
                active
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
```

with:

```tsx
                active
                  ? 'bg-[var(--color-surface-tinted)] text-[var(--color-primary-dark)] font-semibold'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
```

- [ ] **Step 5: Run the app-side-nav suite to verify it passes**

Run: `cd apps/web && npx vitest run components/__tests__/app-side-nav.test.tsx`
Expected: PASS — the new test plus all pre-existing tests (active-tab tests, if any, assert behaviour/aria, not the exact bg class; if a pre-existing test asserted `bg-[var(--color-primary)]` on the active tab, update it to the new tinted class in this step).

- [ ] **Step 6: Mirror the softened style on the mobile drawer button**

In `apps/web/components/chat/history-panel.tsx`, replace the new-conversation button className (line ~42):

```tsx
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-primary)] px-4 text-sm font-medium text-white hover:bg-[var(--color-primary-dark)]"
```

with:

```tsx
        className="mb-4 flex w-full min-h-[44px] items-center justify-center gap-2 rounded-full bg-[var(--color-surface-tinted)] px-4 text-sm font-medium text-[var(--color-primary-dark)] hover:bg-[var(--color-primary)] hover:text-white transition-colors"
```

- [ ] **Step 7: Run the history-panel suite to verify it still passes**

Run: `cd apps/web && npx vitest run components/chat/__tests__/history-panel.test.tsx`
Expected: PASS — its test clicks the button by role/text, which is unchanged.

- [ ] **Step 8: Commit**

```bash
git add apps/web/components/app-side-nav.tsx apps/web/components/chat/history-panel.tsx apps/web/components/__tests__/app-side-nav.test.tsx
git commit -m "feat(nav): soften solid-green sidebar buttons to tinted style"
```

---

## Verification (after all tasks)

- [ ] Run the chat + nav + theme/tenant test scopes together:
  `cd apps/web && npx vitest run components/chat components/__tests__/app-side-nav.test.tsx`
  then `cd packages/theme && npx vitest run && cd ../tenant && npx vitest run`
- [ ] **WCAG AA contrast is now machine-asserted** by `packages/theme/src/__tests__/contrast.test.ts` (Task 1, Steps 9-10) — confirm it is green. This closes the contrast gap: all three new text pairings are pinned ≥4.5:1 and fail CI if a future hex edit drops below AA.
- [ ] Visual check against the two reference screenshots: start the web app, open a conversation with a long numbered-list assistant answer (e.g. the deep-breathing reply) and confirm it renders as prose with no green bubble; confirm a short assistant offer still sits in a neutral (grey, not green) bubble that is **perceptibly distinct from the white canvas** (the `surfaceMuted` fill is subtle by design — if it reads as invisible, deepen `surfaceMuted` one step or rely on the border, both within Task 1); confirm the user bubble is still green; confirm the sidebar "New conversation" button and active "Chat" tab are tinted, not solid green.
- [ ] **Crisis / helpline / resource content check.** Confirm the pinned crisis card is untouched (it arrives as `role: 'crisis'`, which `MessageBubble` returns `null` for — `CrisisCard` owns it, so the long-form branch can never apply). Then send a turn that returns helpline numbers or a scope refusal as a normal `role: 'ai'` message (these are long/multi-line and will now render as borderless prose) and confirm the helpline information still reads clearly and is not visually demoted. If product wants helpline/resource content *emphasised* (per the Crisis UX rule), the correct fix is a dedicated styled treatment keyed off the message intent — not widening the bubble heuristic, which would re-bubble ordinary long answers too. Flag for a follow-up if emphasis is required; it is out of scope here.
- [ ] Confirm RTL is intact: switch to عربي and confirm an Arabic long answer still resolves right-to-left and the list lines are preserved (now also pinned by the Arabic long-form unit test in Task 2).

## Out of scope (deliberately, to keep these quick wins)

- **Markdown rendering (bold subheads / clickable links like Abby).** The backend currently emits plain text with numbered lists; true bold subheads would require a markdown pipeline (new `react-markdown` dependency + backend emitting markdown). Tracked separately — the long-form branch here is the prerequisite layout change.
- The "long-form" rule is a heuristic (`>280 chars or any newline`). If short multi-line offers should stay bubbled, the threshold can be tuned in `isLongForm` in a follow-up; flagged for the visual-check step.
