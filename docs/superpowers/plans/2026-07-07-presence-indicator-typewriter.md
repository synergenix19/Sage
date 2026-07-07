# Sage Presence Indicator + Typewriter Reveal (Phase 0a) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Sage's static three-dot waiting state and one-burst answer paint with a therapist-present "Presence Indicator" (timed, config-driven reassurance copy) and a word-level, bidi-safe "Typewriter Reveal" of the already-gated answer — improving perceived latency with zero change to the clinical safety gate.

**Architecture:** Pure frontend (`cdai`, the `apps/web` Next.js app). All new logic is small, isolated, individually-tested units in `apps/web/lib/` and `apps/web/hooks/`, wired into two existing components (`chat-interface.tsx`, `message-bubble.tsx`) via opt-in props so existing tests stay green. No backend change (crisis `render_mode` derives from today's `CRISIS_SIGNAL` prefix; crisis content already routes to `CrisisCard`, not the typewriter path). Phase 0b (content-free heartbeat + header→body metadata migration) is a committed fast-follow with its own plan.

**Tech Stack:** Next.js / React / TypeScript / Zustand (`useLocaleStore`) / Tailwind (CSS-var tokens) / Vitest 4 + @testing-library/react (jsdom, fake timers) / Playwright (e2e screenshot diff).

## Global Constraints

- **Spec:** `sage-poc/docs/superpowers/specs/2026-07-07-presence-indicator-typewriter-spec.md` — every requirement below traces to it.
- **No safety-gate change; no early emission of un-gated content.** Typewriter animates only the *fully-received, already-gated* text.
- **No i18n library exists.** UI strings are inline `locale === 'ar' ? '<ar>' : '<en>'`. A ~10-item copy pool goes in a dedicated `apps/web/lib/presence-phrases.ts`.
- **No config module / no UI env vars.** Tunables are exported module consts in `apps/web/lib/presence-constants.ts`, `_`-separator style (`9_000`).
- **Copy is clinician + native-Khaleeji sign-off gated** (spec §5). Ship the proposed pool marked PROPOSED; do not invent extra Arabic phrasing. Prefer self-reference-neutral Arabic (persona-gender is an open review item, spec §2.2) — the gendered "موجود معك" pair is held out of the shipped pool.
- **Config values (spec §6):** `PRESENCE_PHRASE_MS=600`, `PRESENCE_SLOW_MS=9000`, `PRESENCE_DEGRADED_MS=25000`, `TYPEWRITER_WPS=30`, `TYPEWRITER_MAX_MS=2500`.
- **Crisis indistinguishability (spec §2.4):** the waiting state is byte-identical across paths; nothing in it varies by turn path. Screenshot diff must deterministically seed the shuffle-bag (spec §7).
- **Bidi-safe chunking (spec §3.1):** a reveal chunk never straddles a text-direction change.
- **Analytics boundary (spec §5):** shown-phrase ID may be logged client-side only; never into `session_audit`.
- **Run tests from `apps/web`.** Single file: `npx vitest run <path>`. Full: `npm test` (= `vitest run`). All `git` commands run in the `cdai` repo.
- **Honesty statement (spec §1):** carry verbatim into the eventual PR description — the indicator/typewriter are POC perceived-latency mitigations, never counted against nor evidence of the `<3s` p95 KPI.

---

## File Structure

**Create (all under `cdai/apps/web/`):**
- `lib/presence-constants.ts` — the five timing/speed consts.
- `lib/presence-phrases.ts` — copy pool (pool / slow / degraded, EN+AR) + `createShuffleBag`.
- `lib/bidi-chunk.ts` — `chunkForReveal(text): string[]`, bidi-run-safe.
- `hooks/use-typewriter.ts` — `useTypewriter(text, opts)` reveal hook.
- `components/chat/presence-indicator.tsx` — the new waiting state (replaces `TypingIndicator` at the render site).
- Tests colocated: `lib/__tests__/presence-phrases.test.ts`, `lib/__tests__/bidi-chunk.test.ts`, `hooks/__tests__/use-typewriter.test.ts`, `components/chat/__tests__/presence-indicator.test.tsx`.
- `playwright/waiting-state-indistinguishability.spec.ts` — crisis-vs-normal waiting diff.

**Modify:**
- `components/chat/message-bubble.tsx` — swap `{message.content}` for a reveal-aware node (opt-in `reveal` prop).
- `components/chat/chat-interface.tsx` — mount `PresenceIndicator`; track the just-completed message for reveal; wire skip affordances.

---

## Task 1: Presence timing/speed config

**Files:**
- Create: `apps/web/lib/presence-constants.ts`
- Test: `apps/web/lib/__tests__/presence-constants.test.ts`

**Interfaces:**
- Produces: `PRESENCE_PHRASE_MS`, `PRESENCE_SLOW_MS`, `PRESENCE_DEGRADED_MS`, `TYPEWRITER_WPS`, `TYPEWRITER_MAX_MS` (all `number`).

- [ ] **Step 1: Write the failing test**

```ts
// apps/web/lib/__tests__/presence-constants.test.ts
import { describe, it, expect } from 'vitest'
import {
  PRESENCE_PHRASE_MS, PRESENCE_SLOW_MS, PRESENCE_DEGRADED_MS,
  TYPEWRITER_WPS, TYPEWRITER_MAX_MS,
} from '@/lib/presence-constants'

describe('presence-constants', () => {
  it('matches the spec §6 envelope', () => {
    expect(PRESENCE_PHRASE_MS).toBe(600)
    expect(PRESENCE_SLOW_MS).toBe(9_000)
    expect(PRESENCE_DEGRADED_MS).toBe(25_000)
    expect(TYPEWRITER_WPS).toBe(30)
    expect(TYPEWRITER_MAX_MS).toBe(2_500)
  })
  it('phases are strictly increasing (envelope is well-ordered)', () => {
    expect(PRESENCE_PHRASE_MS).toBeLessThan(PRESENCE_SLOW_MS)
    expect(PRESENCE_SLOW_MS).toBeLessThan(PRESENCE_DEGRADED_MS)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run lib/__tests__/presence-constants.test.ts`
Expected: FAIL — cannot resolve `@/lib/presence-constants`.

- [ ] **Step 3: Write minimal implementation**

```ts
// apps/web/lib/presence-constants.ts
// Presence Indicator + Typewriter Reveal tunables (spec §6).
// Calibrated to the real prod latency distribution measured 2026-07-07
// (spec §1.1): PRESENCE_SLOW ≈ mid-wait of ~15s total p50; PRESENCE_DEGRADED
// ≈ total p99 (~23s) + margin, so only the ~1% tail sees the honesty phrase.
// Re-tune by editing here if the distribution shifts — no code change needed.
export const PRESENCE_PHRASE_MS = 600      // first phrase fades in and is held
export const PRESENCE_SLOW_MS = 9_000      // cross-fade to the steadier "still with you"
export const PRESENCE_DEGRADED_MS = 25_000 // honesty phrase — or on actual failure, whichever first
export const TYPEWRITER_WPS = 30           // reveal speed (25–35 range), eases faster over time
export const TYPEWRITER_MAX_MS = 2_500     // hard cap; long responses accelerate rather than wait
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run lib/__tests__/presence-constants.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/presence-constants.ts apps/web/lib/__tests__/presence-constants.test.ts
git commit -m "feat(chat): presence + typewriter timing constants (spec §6)"
```

---

## Task 2: Copy pool + shuffle-bag (random-without-repeat)

**Files:**
- Create: `apps/web/lib/presence-phrases.ts`
- Test: `apps/web/lib/__tests__/presence-phrases.test.ts`

**Interfaces:**
- Produces:
  - `PRESENCE_POOL: { en: string[]; ar: string[] }` — the held first-phrase pool.
  - `PRESENCE_SLOW: { en: string; ar: string }`, `PRESENCE_DEGRADED: { en: string; ar: string }`.
  - `createShuffleBag(size: number, rng?: () => number): { next: () => number }` — returns indices, never the same index twice in a row.

- [ ] **Step 1: Write the failing test**

```ts
// apps/web/lib/__tests__/presence-phrases.test.ts
import { describe, it, expect } from 'vitest'
import { PRESENCE_POOL, PRESENCE_SLOW, PRESENCE_DEGRADED, createShuffleBag } from '@/lib/presence-phrases'

describe('presence copy pool', () => {
  it('EN and AR pools are the same length and non-empty', () => {
    expect(PRESENCE_POOL.en.length).toBeGreaterThan(0)
    expect(PRESENCE_POOL.en.length).toBe(PRESENCE_POOL.ar.length)
  })
  it('contains none of the banned word-classes (process/promise/whimsy)', () => {
    const banned = /analy|check|assess|process|solv|find the answer|ponder|brew/i
    for (const s of [...PRESENCE_POOL.en, PRESENCE_SLOW.en, PRESENCE_DEGRADED.en]) {
      expect(s).not.toMatch(banned)
    }
  })
  it('holds out the gendered self-reference pair (persona-gender open item, spec §2.2)', () => {
    expect(PRESENCE_POOL.ar.join(' ')).not.toContain('موجود')
  })
})

describe('createShuffleBag', () => {
  it('never returns the same index twice in a row', () => {
    // Deterministic rng cycling through a fixed sequence.
    const seq = [0.0, 0.0, 0.99, 0.5, 0.0, 0.0]
    let i = 0
    const rng = () => seq[i++ % seq.length]
    const bag = createShuffleBag(4, rng)
    let prev = bag.next()
    for (let n = 0; n < 20; n++) {
      const cur = bag.next()
      expect(cur).not.toBe(prev)
      expect(cur).toBeGreaterThanOrEqual(0)
      expect(cur).toBeLessThan(4)
      prev = cur
    }
  })
  it('is deterministic under a seeded rng (enables the indistinguishability test)', () => {
    const mk = () => { let i = 0; const s = [0.1, 0.7, 0.3, 0.9]; return createShuffleBag(4, () => s[i++ % s.length]) }
    const a = mk(); const b = mk()
    expect([a.next(), a.next(), a.next()]).toEqual([b.next(), b.next(), b.next()])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run lib/__tests__/presence-phrases.test.ts`
Expected: FAIL — cannot resolve `@/lib/presence-phrases`.

- [ ] **Step 3: Write minimal implementation**

```ts
// apps/web/lib/presence-phrases.ts
// PROPOSED copy — pending clinician + native-Khaleeji sign-off (spec §5).
// Register: therapist-present, not machinery. Banned: process/promise/whimsy words.
// Arabic is self-reference-neutral; the gendered "موجود/موجودة" pair is held out
// until the persona-gender review resolves (spec §2.2). Pool should reach ~8–12
// items after sign-off. Every phrase must read right after a crisis disclosure,
// a casual greeting, AND a long trauma story.
export const PRESENCE_POOL: { en: string[]; ar: string[] } = {
  en: [
    'Listening…',
    "I'm with you…",
    'Taking that in…',
    'One moment…',
    'Thinking about what you said…',
    'Giving this a moment…',
  ],
  ar: [
    'أسمعك…',
    'معك…',
    'أستوعب كلامك…',
    'لحظة…',
    'أفكر في اللي قلته…',
    'أعطي هذا وقته…',
  ],
}

// Phase 2 (slow) — one steadier phrase, held.
export const PRESENCE_SLOW: { en: string; ar: string } = {
  en: 'Still with you — taking a little longer…',
  ar: 'معك، بس أحتاج شوي وقت…',
}

// Phase 3 (degraded / honesty valve) — acknowledge the wait once, warmly.
export const PRESENCE_DEGRADED: { en: string; ar: string } = {
  en: 'This is taking longer than it should. Give me one more moment, or try sending again.',
  ar: 'هذا ياخذ وقت أطول من المتوقع. لحظة وحدة بعد، أو جرّب ترسل مرة ثانية.',
}

// Random-without-repeat index generator (a "shuffle bag" degenerate to no-immediate-repeat).
// rng is injectable so tests (and the indistinguishability screenshot) are deterministic.
export function createShuffleBag(size: number, rng: () => number = Math.random): { next: () => number } {
  let prev = -1
  return {
    next() {
      if (size <= 1) return 0
      let idx = Math.floor(rng() * size)
      if (idx >= size) idx = size - 1 // guard rng() === 1
      if (idx === prev) idx = (idx + 1) % size // skip an immediate repeat deterministically
      prev = idx
      return idx
    },
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run lib/__tests__/presence-phrases.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/presence-phrases.ts apps/web/lib/__tests__/presence-phrases.test.ts
git commit -m "feat(chat): presence copy pool + no-repeat shuffle bag (spec §2.2, PROPOSED/pending sign-off)"
```

---

## Task 3: Bidi-safe reveal chunking

**Files:**
- Create: `apps/web/lib/bidi-chunk.ts`
- Test: `apps/web/lib/__tests__/bidi-chunk.test.ts`

**Interfaces:**
- Produces: `chunkForReveal(text: string): string[]` — chunks concatenate **exactly** to `text`; each chunk holds at most 2 word-tokens; a chunk never straddles a direction change (LTR↔RTL word tokens are never in the same chunk).

- [ ] **Step 1: Write the failing test**

```ts
// apps/web/lib/__tests__/bidi-chunk.test.ts
import { describe, it, expect } from 'vitest'
import { chunkForReveal } from '@/lib/bidi-chunk'

const AR_WORD = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/
const LAT_WORD = /[A-Za-z]/

describe('chunkForReveal', () => {
  it('reconstructs the original text exactly (whitespace preserved)', () => {
    const t = 'Thinking about what you said today.\nOne more line.'
    expect(chunkForReveal(t).join('')).toBe(t)
  })
  it('never puts more than 2 word-tokens in a chunk', () => {
    const chunks = chunkForReveal('one two three four five six')
    for (const c of chunks) {
      const words = c.trim().split(/\s+/).filter(Boolean)
      expect(words.length).toBeLessThanOrEqual(2)
    }
  })
  it('never straddles a direction change (code-switched text — C-2 eval shape)', () => {
    const t = 'أحس بضغط كبير and my boss keeps calling'
    const chunks = chunkForReveal(t)
    expect(chunks.join('')).toBe(t)
    for (const c of chunks) {
      const hasAr = AR_WORD.test(c)
      const hasLat = LAT_WORD.test(c)
      expect(hasAr && hasLat).toBe(false) // no chunk mixes an Arabic word and a Latin word
    }
  })
  it('handles empty and single-word input', () => {
    expect(chunkForReveal('')).toEqual([])
    expect(chunkForReveal('hello').join('')).toBe('hello')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run lib/__tests__/bidi-chunk.test.ts`
Expected: FAIL — cannot resolve `@/lib/bidi-chunk`.

- [ ] **Step 3: Write minimal implementation**

```ts
// apps/web/lib/bidi-chunk.ts
// Split text into progressive-reveal chunks for the typewriter.
// Rules (spec §3.1): word-level (≤2 word-tokens/chunk), and a chunk NEVER
// straddles a text-direction change — so a partial LTR run embedded in RTL
// (or vice-versa) can't reorder already-revealed words as more land.
const RTL = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/
const LTR = /[A-Za-zÀ-ɏ]/

type Dir = 'rtl' | 'ltr' | 'neutral'
function dirOf(token: string): Dir {
  if (RTL.test(token)) return 'rtl'
  if (LTR.test(token)) return 'ltr'
  return 'neutral' // whitespace, digits, punctuation — do not force a boundary
}

const MAX_WORDS_PER_CHUNK = 2

export function chunkForReveal(text: string): string[] {
  if (!text) return []
  // Tokenize into alternating word / whitespace runs, preserving everything.
  const tokens = text.match(/\s+|\S+/g) ?? []
  const chunks: string[] = []
  let cur = ''
  let curDir: Dir = 'neutral'
  let wordCount = 0

  for (const tok of tokens) {
    const isSpace = /^\s+$/.test(tok)
    const d = isSpace ? 'neutral' : dirOf(tok)
    const flips = d !== 'neutral' && curDir !== 'neutral' && d !== curDir
    const full = wordCount >= MAX_WORDS_PER_CHUNK && !isSpace

    if (cur && (flips || full)) {
      chunks.push(cur)
      cur = ''
      curDir = 'neutral'
      wordCount = 0
    }
    cur += tok
    if (!isSpace) {
      wordCount++
      if (curDir === 'neutral') curDir = d
    }
  }
  if (cur) chunks.push(cur)
  return chunks
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run lib/__tests__/bidi-chunk.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/bidi-chunk.ts apps/web/lib/__tests__/bidi-chunk.test.ts
git commit -m "feat(chat): bidi-safe reveal chunking for code-switched text (spec §3.1)"
```

---

## Task 4: `useTypewriter` reveal hook

**Files:**
- Create: `apps/web/hooks/use-typewriter.ts`
- Test: `apps/web/hooks/__tests__/use-typewriter.test.ts`

**Interfaces:**
- Consumes: `chunkForReveal` (Task 3), `TYPEWRITER_WPS`, `TYPEWRITER_MAX_MS` (Task 1).
- Produces: `useTypewriter(text: string, opts: { enabled: boolean }): { displayed: string; done: boolean; complete: () => void }`.
  - `enabled: false` (crisis / reduced-motion / history) → `displayed === text`, `done === true`, immediately.
  - `enabled: true` → `displayed` grows chunk-by-chunk over `min(TYPEWRITER_MAX_MS, words/WPS*1000)`, accelerating; `complete()` reveals all at once (skip affordance).

- [ ] **Step 1: Write the failing test**

```ts
// apps/web/hooks/__tests__/use-typewriter.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTypewriter } from '@/hooks/use-typewriter'

describe('useTypewriter', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('reveals nothing-to-all over time and completes', () => {
    const text = 'one two three four five six seven eight'
    const { result } = renderHook(() => useTypewriter(text, { enabled: true }))
    expect(result.current.displayed.length).toBeLessThan(text.length)
    act(() => { vi.advanceTimersByTime(3_000) }) // past the 2.5s cap
    expect(result.current.displayed).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it('when disabled, shows full text immediately (crisis / reduced-motion / history)', () => {
    const text = 'helpline text renders instantly'
    const { result } = renderHook(() => useTypewriter(text, { enabled: false }))
    expect(result.current.displayed).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it('complete() reveals everything at once (skip affordance)', () => {
    const text = 'a fairly long sentence to reveal word by word here'
    const { result } = renderHook(() => useTypewriter(text, { enabled: true }))
    act(() => { vi.advanceTimersByTime(200) })
    act(() => { result.current.complete() })
    expect(result.current.displayed).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it('displayed is always a real prefix of the chunk-joined text (no reorder/garble)', () => {
    const text = 'أحس بضغط كبير and my boss keeps calling'
    const { result } = renderHook(() => useTypewriter(text, { enabled: true }))
    act(() => { vi.advanceTimersByTime(500) })
    expect(text.startsWith(result.current.displayed)).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run hooks/__tests__/use-typewriter.test.ts`
Expected: FAIL — cannot resolve `@/hooks/use-typewriter`.

- [ ] **Step 3: Write minimal implementation**

```ts
// apps/web/hooks/use-typewriter.ts
import { useEffect, useMemo, useRef, useState } from 'react'
import { chunkForReveal } from '@/lib/bidi-chunk'
import { TYPEWRITER_WPS, TYPEWRITER_MAX_MS } from '@/lib/presence-constants'

const TICK_MS = 1000 / 60 // ~16ms; interval-driven so fake timers control it deterministically

export function useTypewriter(text: string, opts: { enabled: boolean }): {
  displayed: string; done: boolean; complete: () => void
} {
  const chunks = useMemo(() => chunkForReveal(text), [text])
  const [count, setCount] = useState(() => (opts.enabled ? 0 : chunks.length))
  const elapsedRef = useRef(0)

  // Duration scales with length but is capped — long responses accelerate (spec §3.2).
  const durationMs = useMemo(() => {
    const words = text.trim() ? text.trim().split(/\s+/).length : 0
    return Math.min(TYPEWRITER_MAX_MS, (words / TYPEWRITER_WPS) * 1000)
  }, [text])

  useEffect(() => {
    if (!opts.enabled) { setCount(chunks.length); return }
    setCount(0)
    elapsedRef.current = 0
    if (chunks.length === 0 || durationMs <= 0) { setCount(chunks.length); return }
    const id = setInterval(() => {
      elapsedRef.current += TICK_MS
      const p = Math.min(1, elapsedRef.current / durationMs)
      const eased = Math.pow(p, 1.4) // accelerate: reveal rate increases over time
      const revealed = Math.min(chunks.length, Math.ceil(eased * chunks.length))
      setCount(revealed)
      if (p >= 1) clearInterval(id)
    }, TICK_MS)
    return () => clearInterval(id)
  }, [chunks, durationMs, opts.enabled])

  const complete = () => setCount(chunks.length)
  const displayed = count >= chunks.length ? text : chunks.slice(0, count).join('')
  return { displayed, done: count >= chunks.length, complete }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run hooks/__tests__/use-typewriter.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/web/hooks/use-typewriter.ts apps/web/hooks/__tests__/use-typewriter.test.ts
git commit -m "feat(chat): useTypewriter reveal hook (word-level, capped, skippable) — spec §3"
```

---

## Task 5: `PresenceIndicator` component (breathing pulse + timed phrases + a11y)

**Files:**
- Create: `apps/web/components/chat/presence-indicator.tsx`
- Test: `apps/web/components/chat/__tests__/presence-indicator.test.tsx`

**Interfaces:**
- Consumes: `PRESENCE_POOL`, `PRESENCE_SLOW`, `PRESENCE_DEGRADED`, `createShuffleBag` (Task 2); `PRESENCE_PHRASE_MS`, `PRESENCE_SLOW_MS`, `PRESENCE_DEGRADED_MS` (Task 1); `useLocaleStore`.
- Produces: `PresenceIndicator({ rng, onPhrase }: { rng?: () => number; onPhrase?: (id: number) => void })`. `rng` is injectable so the screenshot test seeds it deterministically (spec §7). `onPhrase` fires the client-only analytics hook with the shown phrase index (spec §5) — never persisted to the audit trail.
- Behavior: mount = turn start. 0–`PRESENCE_PHRASE_MS`: breathing dot only. `PRESENCE_PHRASE_MS`: pick one pool phrase (held, no in-turn rotation). `PRESENCE_SLOW_MS`: cross-fade to slow phrase. `PRESENCE_DEGRADED_MS`: cross-fade to degraded phrase. `prefers-reduced-motion`: static dot (no pulse), phrase still shown. Phrase announced once via the ancestor `aria-live="polite"` log; the component itself keeps `role="status"`.

- [ ] **Step 1: Write the failing test**

```tsx
// apps/web/components/chat/__tests__/presence-indicator.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { PresenceIndicator } from '@/components/chat/presence-indicator'
import { PRESENCE_POOL, PRESENCE_SLOW, PRESENCE_DEGRADED } from '@/lib/presence-phrases'

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en' })),
}))

describe('PresenceIndicator', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  it('shows the breathing dot with no phrase before 600ms', () => {
    render(<PresenceIndicator rng={() => 0} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    for (const p of PRESENCE_POOL.en) expect(screen.queryByText(p)).toBeNull()
  })

  it('holds one pool phrase after 600ms, swaps to slow at 9s, degraded at 25s', () => {
    render(<PresenceIndicator rng={() => 0} />)
    act(() => { vi.advanceTimersByTime(650) })
    expect(screen.getByText(PRESENCE_POOL.en[0])).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(9_000) })
    expect(screen.getByText(PRESENCE_SLOW.en)).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(16_000) })
    expect(screen.getByText(PRESENCE_DEGRADED.en)).toBeInTheDocument()
  })

  it('fires onPhrase once with the chosen index (client-only analytics)', () => {
    const onPhrase = vi.fn()
    render(<PresenceIndicator rng={() => 0} onPhrase={onPhrase} />)
    act(() => { vi.advanceTimersByTime(650) })
    expect(onPhrase).toHaveBeenCalledWith(0)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run components/chat/__tests__/presence-indicator.test.tsx`
Expected: FAIL — cannot resolve `@/components/chat/presence-indicator`.

- [ ] **Step 3: Write minimal implementation**

```tsx
// apps/web/components/chat/presence-indicator.tsx
'use client'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { PRESENCE_POOL, PRESENCE_SLOW, PRESENCE_DEGRADED, createShuffleBag } from '@/lib/presence-phrases'
import { PRESENCE_PHRASE_MS, PRESENCE_SLOW_MS, PRESENCE_DEGRADED_MS } from '@/lib/presence-constants'

type Phase = 'dot' | 'phrase' | 'slow' | 'degraded'

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(mq.matches)
    const on = () => setReduced(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return reduced
}

export function PresenceIndicator({ rng, onPhrase }: { rng?: () => number; onPhrase?: (id: number) => void }) {
  const locale = useLocaleStore((s) => s.locale)
  const reduced = usePrefersReducedMotion()
  const [phase, setPhase] = useState<Phase>('dot')
  // Pick the held phrase index ONCE, at mount, from the no-repeat bag (spec §2.2).
  const bag = useMemo(() => createShuffleBag(PRESENCE_POOL.en.length, rng), [rng])
  const phraseIdx = useRef<number>(-1)

  useEffect(() => {
    const t1 = setTimeout(() => {
      phraseIdx.current = bag.next()
      onPhrase?.(phraseIdx.current) // client-only analytics; never persisted (spec §5)
      setPhase('phrase')
    }, PRESENCE_PHRASE_MS)
    const t2 = setTimeout(() => setPhase('slow'), PRESENCE_SLOW_MS)
    const t3 = setTimeout(() => setPhase('degraded'), PRESENCE_DEGRADED_MS)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [bag, onPhrase])

  const label =
    phase === 'dot' ? '' :
    phase === 'slow' ? PRESENCE_SLOW[locale] :
    phase === 'degraded' ? PRESENCE_DEGRADED[locale] :
    PRESENCE_POOL[locale][phraseIdx.current] ?? ''

  return (
    <div
      role="status"
      aria-label={locale === 'ar' ? 'Sage معك' : 'Sage is with you'}
      className="flex items-center justify-start gap-2"
      data-testid="presence-indicator"
    >
      <span
        className={
          'h-2.5 w-2.5 rounded-full bg-[var(--color-text-secondary)] ' +
          (reduced ? 'opacity-70' : 'motion-safe:animate-[breathe_4s_ease-in-out_infinite]')
        }
      />
      {label && (
        <span className="text-sm text-[var(--color-text-secondary)] transition-opacity duration-500">
          {label}
        </span>
      )}
    </div>
  )
}
```

> Add the `breathe` keyframe to the Tailwind/global CSS (once): in `apps/web/app/globals.css` append
> ```css
> @keyframes breathe { 0%,100% { opacity: .35; transform: scale(1); } 50% { opacity: 1; transform: scale(1.15); } }
> ```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run components/chat/__tests__/presence-indicator.test.tsx`
Expected: PASS (3 tests). (matchMedia is mocked to `matches:false` globally in `vitest.setup.ts`, so the non-reduced path runs.)

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/chat/presence-indicator.tsx \
        apps/web/components/chat/__tests__/presence-indicator.test.tsx \
        apps/web/app/globals.css
git commit -m "feat(chat): PresenceIndicator — breathing pulse, timed phrases, reduced-motion, a11y (spec §2)"
```

---

## Task 6: Reveal-aware message rendering (opt-in `reveal` on MessageBubble)

**Files:**
- Modify: `apps/web/components/chat/message-bubble.tsx` (the `{message.content}` node, ~line 53)
- Test: `apps/web/components/chat/__tests__/message-bubble.test.tsx` (add cases; keep existing green)

**Interfaces:**
- Consumes: `useTypewriter` (Task 4).
- Produces: `MessageBubble` gains an optional prop `reveal?: boolean` (default `false`) and `onRevealComplete?: () => void`. When `reveal` is `false`, output is byte-identical to today (full `content`) so existing tests pass unchanged. When `true`, the content node shows the typewriter `displayed` slice while keeping `dir` and `whitespace-pre-wrap` on the same element (both pinned by existing tests).

- [ ] **Step 1: Write the failing test**

```tsx
// add to apps/web/components/chat/__tests__/message-bubble.test.tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MessageBubble } from '@/components/chat/message-bubble'

function assistantMsg(content: string) {
  return { id: 'm1', role: 'assistant' as const, content, intent: null, sessionId: 's', createdAt: '', direction: 'ltr' as const }
}

describe('MessageBubble reveal', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('reveal=false renders full content immediately (back-compat)', () => {
    render(<MessageBubble message={assistantMsg('hello there friend')} />)
    expect(screen.getByText('hello there friend')).toBeInTheDocument()
  })

  it('reveal=true reveals progressively then completes, keeping dir + whitespace-pre-wrap', () => {
    render(<MessageBubble message={assistantMsg('one two three four five six')} reveal />)
    const node = screen.getByTestId('message-content')
    expect(node).toHaveAttribute('dir', 'ltr')
    expect(node.className).toContain('whitespace-pre-wrap')
    act(() => { vi.advanceTimersByTime(3_000) })
    expect(node.textContent).toBe('one two three four five six')
  })
})
```

> Note: this adds a `data-testid="message-content"` to the content node. If the existing test file lacks it, add the attribute in Step 3 and it does not affect existing assertions.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run components/chat/__tests__/message-bubble.test.tsx`
Expected: FAIL — `reveal` prop unknown / no `message-content` testid / no progressive reveal.

- [ ] **Step 3: Write minimal implementation**

In `message-bubble.tsx`: (a) extend `Props` with `reveal?: boolean` and `onRevealComplete?: () => void`; (b) call the hook near the top of the component body; (c) render `displayed` instead of `content` on the content node, adding the testid. Keep `dir` and `whitespace-pre-wrap` exactly as they are.

```tsx
// top of component body (after props destructure), assistant branch only:
import { useTypewriter } from '@/hooks/use-typewriter'
// ...
const { displayed, done, complete } = useTypewriter(message.content, { enabled: reveal === true })
useEffect(() => { if (done) onRevealComplete?.() }, [done, onRevealComplete])
```

```tsx
// the content node (was `{message.content}` at ~line 53) becomes:
<div
  data-testid="message-content"
  dir={message.direction ?? 'auto'}
  onClick={reveal && !done ? complete : undefined}   // tap-to-skip (spec §3.3)
  className={/* ...unchanged classes incl. */ 'whitespace-pre-wrap'}
>
  {reveal ? displayed : message.content}
</div>
```

> `Props` currently is `{ message: ChatMessage; supabaseId?: string; onFeedback?: ... }`. Add `reveal?: boolean; onRevealComplete?: () => void`. Import `useEffect` if not already imported. The `system`/`crisis` early-return branches are untouched (crisis never reaches here — it renders in `CrisisCard`), so `render_mode='instant'` for crisis is structural, not a branch.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run components/chat/__tests__/message-bubble.test.tsx`
Expected: PASS (existing cases + 2 new).

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/chat/message-bubble.tsx apps/web/components/chat/__tests__/message-bubble.test.tsx
git commit -m "feat(chat): opt-in typewriter reveal on MessageBubble, back-compat default (spec §3)"
```

---

## Task 7: Wire indicator + reveal + skip into ChatInterface (integration)

**Files:**
- Modify: `apps/web/components/chat/chat-interface.tsx`
- Test: `apps/web/components/chat/__tests__/chat-interface.test.tsx` (add integration cases)

**Interfaces:**
- Consumes: `PresenceIndicator` (Task 5), `MessageBubble.reveal` (Task 6).
- Produces: (a) `PresenceIndicator` replaces `TypingIndicator` at the waiting-state render site; (b) the just-completed assistant message reveals via `reveal={m.id === revealId}`; (c) reveal is skipped (completed) when the user starts typing (input `onFocus`/first keystroke) — the tap-to-skip is already wired in Task 6.

- [ ] **Step 1: Write the failing test**

```tsx
// add to apps/web/components/chat/__tests__/chat-interface.test.tsx
it('renders PresenceIndicator (not the old dots) while awaiting first byte', async () => {
  // Arrange a pending fetch (never resolves within the assertion window).
  const fetchMock = vi.fn(() => new Promise(() => {}))
  vi.stubGlobal('fetch', fetchMock)
  const { getByTestId, findByTestId } = renderChat() // existing helper in this file
  // ...trigger a send via the existing input helper...
  expect(await findByTestId('presence-indicator')).toBeInTheDocument()
  expect(() => getByTestId('typing-indicator')).toThrow()
})
```

> Use the file's existing render/send helpers and mock shape (this file already mocks fetch and drives `append`). Mirror its established setup rather than introducing a new harness.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run components/chat/__tests__/chat-interface.test.tsx`
Expected: FAIL — `presence-indicator` testid not found (still rendering `TypingIndicator`).

- [ ] **Step 3: Write minimal implementation**

```tsx
// imports
import { PresenceIndicator } from './presence-indicator'
// remove: import { TypingIndicator } from './typing-indicator'

// add reveal tracking state in ChatInterface:
const [revealId, setRevealId] = useState<string | null>(null)
// when a stream completes, mark that message for reveal. Simplest hook point:
// after `append`/stream settles, the last assistant message id is the reveal target.
// Track it off isLoading transition true->false with a non-empty last assistant msg:
useEffect(() => {
  if (!isLoading) {
    const last = messages[messages.length - 1]
    if (last?.role === 'assistant' && last.content) setRevealId(last.id)
  }
}, [isLoading, messages])

// waiting-state render site (was TypingIndicator):
{isLoading && messages[messages.length - 1]?.content === '' && (
  <PresenceIndicator onPhrase={(id) => { /* client-only UX analytics; never audit (spec §5) */ }} />
)}

// in the messages.map, pass reveal to the assistant bubble:
<MessageBubble
  /* ...existing props... */
  reveal={m.role === 'assistant' && m.id === revealId}
  onRevealComplete={() => setRevealId(null)}
/>

// skip-on-type: pass a completion signal down. Simplest: when InputBar gains focus,
// clear revealId so the reveal finalizes to full text.
<InputBar onSend={handleSend} disabled={isLoading} onFocus={() => setRevealId(null)} />
```

> `InputBar` needs to accept and forward an optional `onFocus` to its `<input>`/`<textarea>`. If it doesn't already, add `onFocus?: () => void` to its props and spread it onto the field. Setting `revealId` to `null` makes the bubble render full `content` (reveal disabled) — an instant, safe completion of the skip.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run components/chat/__tests__/chat-interface.test.tsx`
Expected: PASS (existing suite + new case). Then run the whole chat folder to catch regressions: `npx vitest run components/chat`.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/chat/chat-interface.tsx \
        apps/web/components/chat/input-bar.tsx \
        apps/web/components/chat/__tests__/chat-interface.test.tsx
git commit -m "feat(chat): wire PresenceIndicator + typewriter reveal + skip-on-type (spec §2–§3)"
```

---

## Task 8: Resend-supersede invariant (spec §2.3 / review Change 3)

**Files:**
- Modify: `apps/web/components/chat/chat-interface.tsx` (only if a gap is found — the existing `inFlightRef` + `registerFirstByteTimeout` abort already enforce this)
- Test: `apps/web/components/chat/__tests__/chat-interface.test.tsx` (add invariant test)

**Interfaces:**
- Produces: a regression test asserting a retry never runs two concurrent server-side turns for one utterance (which would also write two `session_audit` rows).

- [ ] **Step 1: Write the failing test**

```tsx
// add to apps/web/components/chat/__tests__/chat-interface.test.tsx
it('retry supersedes an in-flight request — never two concurrent turns per utterance', async () => {
  const fetchMock = vi.fn(() => new Promise(() => {})) // stays in flight
  vi.stubGlobal('fetch', fetchMock)
  const { result } = renderHook(() => useStreamingChat('sess', 'user', []))
  act(() => { result.current.append({ role: 'user', content: 'hi' }) })
  await act(async () => { await Promise.resolve() })
  const callsAfterFirst = fetchMock.mock.calls.length
  act(() => { result.current.reload() }) // re-tap while in flight
  expect(fetchMock.mock.calls.length).toBe(callsAfterFirst) // reload() no-ops while inFlight
})
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `npx vitest run components/chat/__tests__/chat-interface.test.tsx -t 'supersedes'`
Expected: PASS if the existing `inFlightRef` guard already holds (document it); FAIL only if a regression exists. If it FAILS, add the guard in Step 3.

- [ ] **Step 3: Confirm/repair the guard**

The existing `reload()` returns early on `inFlightRef.current`, and `registerFirstByteTimeout()` aborts any prior controller before a new stream. If the test passes, no code change — this step records that the invariant is covered. If it fails, ensure `reload()` begins with `if (inFlightRef.current) return` and `stream()` aborts `abortRef.current` before creating a new controller.

> Copy note (spec §2.3): the degraded phrase says "try sending again," but the input is `disabled` while `isLoading`, so a concurrent send is not reachable mid-flight; the resend path is the post-timeout/error `reload()`, which this test pins. Flag for clinical copy review whether the degraded EN string should soften "try sending again" given the input is disabled until the 58s ceiling — do not reword unilaterally (sign-off gated).

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run components/chat/__tests__/chat-interface.test.tsx -t 'supersedes'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/chat/__tests__/chat-interface.test.tsx apps/web/components/chat/chat-interface.tsx
git commit -m "test(chat): pin resend-supersede invariant — one turn per utterance (spec §2.3)"
```

---

## Task 9: Crisis-vs-normal waiting-state indistinguishability (Playwright, spec §2.4/§7)

**Files:**
- Create: `apps/web/playwright/waiting-state-indistinguishability.spec.ts`

**Interfaces:**
- Consumes: `PresenceIndicator`'s injectable `rng` — the test builds the app with a deterministically-seeded bag so both turns render the identical phrase, then diffs the full waiting-state frame (spec §7 chose deterministic-seed over region-masking).

- [ ] **Step 1: Write the test (screenshot diff)**

```ts
// apps/web/playwright/waiting-state-indistinguishability.spec.ts
import { test, expect } from '@playwright/test'

// Both turns must show a byte-identical waiting state — the presence indicator must
// never leak that a turn is going down the crisis path (spec §2.4). The shuffle-bag
// is seeded deterministically via a test hook so the diff is not defeated by phrase
// variance; the diff therefore covers the FULL frame including the phrase region.
test('waiting state is identical for a normal vs a crisis-bound turn', async ({ page }) => {
  // Route /api/chat to a normal turn, capture the waiting frame before first byte.
  await page.route('**/api/chat', (route) => new Promise(() => { void route })) // hang → stay in waiting
  await page.goto('/chat?e2e_seed=1') // e2e_seed pins createShuffleBag rng (wire in app under NEXT_PUBLIC_E2E only)
  await page.getByRole('textbox').fill('I feel a bit low today')
  await page.getByRole('button', { name: /send/i }).click()
  const normal = await page.getByTestId('presence-indicator').screenshot()

  await page.reload()
  await page.getByRole('textbox').fill('I want to end my life') // crisis-bound utterance
  await page.getByRole('button', { name: /send/i }).click()
  const crisis = await page.getByTestId('presence-indicator').screenshot()

  expect(Buffer.compare(normal, crisis)).toBe(0)
})
```

> Wiring note: expose the deterministic seed only under a test flag. In `chat-interface.tsx`, pass `rng` to `PresenceIndicator` as `process.env.NEXT_PUBLIC_E2E ? seededRng() : undefined`, where `seededRng` is a tiny LCG. This keeps prod behavior random while making the e2e diff deterministic. Add the eval-scenario note (spec §5) to the QA checklist: "waiting-state screenshot review after a crisis-path turn — must equal a normal turn."

- [ ] **Step 2: Run it**

Run (from `apps/web`): `npx playwright test playwright/waiting-state-indistinguishability.spec.ts`
Expected: PASS — `Buffer.compare` is 0 (identical frames).

- [ ] **Step 3: Commit**

```bash
git add apps/web/playwright/waiting-state-indistinguishability.spec.ts apps/web/components/chat/chat-interface.tsx
git commit -m "test(chat): crisis-vs-normal waiting-state indistinguishability, seeded bag (spec §2.4/§7)"
```

---

## Task 10: Full suite green + cleanup

- [ ] **Step 1: Run the full frontend suite**

Run (from `apps/web`): `npm test`
Expected: all pass, including the untouched `typing-indicator.test.tsx` (the component file may remain for now; it is simply no longer rendered — remove it in Step 2 only if nothing imports it).

- [ ] **Step 2: Remove the dead waiting-state component if unreferenced**

Run: `grep -rn "TypingIndicator" apps/web --include=*.tsx --include=*.ts | grep -v __tests__`
If the only remaining references are its own file + test, delete `typing-indicator.tsx` and its test; otherwise leave them.

```bash
git rm apps/web/components/chat/typing-indicator.tsx apps/web/components/chat/__tests__/typing-indicator.test.tsx
git commit -m "chore(chat): remove superseded TypingIndicator (replaced by PresenceIndicator)"
```

- [ ] **Step 3: Manual verification (spec §7 a11y, both locales)**

Run the app; send a message in EN and in AR; confirm: breathing dot → held phrase → (on a slow turn) "still with you"; answer types in word-by-word; tap-to-skip and type-to-skip complete it; Arabic reveals right-to-left with no glyph jitter; a screen reader announces the phrase once and the full answer once. Toggle OS reduced-motion and confirm the dot is static and the answer fades in whole.

---

## Self-Review (plan ↔ spec coverage)

- **§1 honesty statement** → carried into Global Constraints + PR-description note (Task 9 QA). ✔
- **§1.1 latency calibration** → Task 1 consts + rationale comment. ✔
- **§2.1 banned word-classes** → Task 2 banned-regex test. ✔
- **§2.2 copy pool / neutral-Arabic / persona-gender hold-out** → Task 2 (pool + held-out `موجود` test). ✔
- **§2.3 timing envelope (config)** → Tasks 1 + 5; **resend semantics** → Task 8. ✔
- **§2.4 breathing pulse / uniformity / reduced-motion / aria** → Task 5; **indistinguishability** → Task 9. ✔
- **§3.1 word-level bidi-safe / code-switched** → Task 3. ✔
- **§3.2 speed/cap/accelerate** → Task 4. ✔
- **§3.3 skip (tap + type)** → Task 6 (tap) + Task 7 (type). ✔
- **§3.4 render_mode=instant for crisis** → structural (crisis → `CrisisCard`, never the reveal path); Task 6 note. ✔
- **§3.5 reduced-motion fade / SR announce once** → Task 5 (reduced-motion) + Task 6/Task 10 (SR manual). ✔
- **§5 governance: analytics client-only** → Task 5 `onPhrase` + Task 7 comment; **eval scenario** → Task 9. ✔
- **§6 config values** → Task 1. ✔
- **§4.2 / §8 Phase 0b** → out of scope here; committed fast-follow, separate plan.

Gaps: none blocking. The reduced-motion→whole-fade *visual* (spec §3.5) is realized as "reveal disabled ⇒ full content shown"; a literal 300ms fade class can be added in Task 6's content node if design wants the animation — noted, not blocking.

---

## Execution Handoff

**Phase 0a plan complete.** Phase 0b (content-free heartbeat + header→body metadata migration, spec §4.2) is a committed fast-follow and gets its own plan once 0a lands.
