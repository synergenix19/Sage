# Markdown Hierarchy (Abby-parity answer formatting) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render assistant answers with real typographic hierarchy — bold subheads, proper bullet/numbered lists, and safe links — instead of flat plain text, matching the Abby benchmark.

**Architecture:** This is two coordinated subsystems, deliberately split. **Sub-project A (frontend, this plan, shippable now):** add a sanitized, RTL-aware Markdown renderer to the assistant message surface. It immediately upgrades the numbered/point lists the backend *already* emits (via the L4 light-structure directive) into proper lists, and it auto-upgrades to bold subheads + links the moment the backend emits them — no further frontend change. **Sub-project B (backend, scoped here, NOT yet detailed — clinical-governance gated):** flip the backend from markdown-*stripping* to markdown-*emitting*. The frontend is the prerequisite and is low-risk on its own; the backend is the value unlock but needs clinical sign-off and guard recalibration.

**Tech Stack:** Next.js + React + TypeScript (`apps/web`); `react-markdown` (builds a React element tree, no `dangerouslySetInnerHTML` — XSS-safe by default) + `remark-gfm` (lists, autolinks, strikethrough) + `remark-breaks` (single newline → `<br>`, to preserve the backend's line-structured points). Backend is Python/LangGraph in `sage-poc` (Sub-project B only).

## Global Constraints

- **Base:** Sub-project A executes on `main` at `4d272e1`. `apps/web` has NO markdown dependency today; `message-bubble.tsx` renders assistant content as `{message.content}` in a `whitespace-pre-wrap` div (post the prose/centered-column work).
- **Assistant content only.** User messages render as literal plain text (`whitespace-pre-wrap`), never as Markdown — user input must not be interpreted as formatting. Crisis content never reaches this renderer (`MessageBubble` returns `null` for `role: 'crisis'`; the pinned `CrisisCard` owns it).
- **Security:** no raw HTML rendering (do NOT add `rehype-raw`). Restrict to an explicit safe element allowlist. `react-markdown`'s default URL transform strips `javascript:` etc. — but protocol-filtering does NOT vet the destination domain.
- **Links (gated — no clickable anchors in A):** Sub-project A renders link syntax as a **plain-text label, never a clickable anchor.** Reason: the RAG design has the model *cite sources* from a curated corpus, but retrieved content is untrusted text — a hallucinated or injection-derived `https://` URL would render as an equally clickable, equally trustworthy-looking link, and protocol-filtering cannot catch a clean link to a bad domain. Verified: the backend does **not** strip `[text](url)` (output_gate strips emphasis/emoji/em-dash only, `output_gate.py:90-100`), so an enabled anchor would be live on day one, not dormant. Clickable links (with a **vetted-domain allowlist**, non-allowlisted → plain text) are a Sub-project B decision with the clinical owner.
- **RTL preserved:** the authoritative `dir={message.direction ?? 'auto'}` stays on the bubble container; list indentation uses logical properties (`ps-*`, not `pl-*`) so RTL indents on the correct side.
- **KNOWN INTERACTION (not fixed here — raises the priority of the banked authoritative-direction work):** `dir="auto"` resolves direction from the first strong character. An Arabic answer that *opens with a numbered list* now leads with the glyph `1`, which `dir="auto"` mis-resolves to LTR — and this plan makes digit-leading Arabic lists common. History messages carry no authoritative `message.direction` (the page projects only `id/role/content`), so such an answer can flip LTR. This is pre-existing (it was banked two PRs ago as the "carry backend detected-language direction into the message object" follow-up), but Markdown lists **increase its exposure**: "Arabic lists render now" + "Arabic list direction inferred from a leading digit" is a bad pairing. Do NOT fix it in Sub-project A; the fix is the backend-authoritative-direction work, and this plan is the reason to prioritise it.
- **Font/contrast unchanged:** assistant text stays `text-[15px] leading-7` on the prose surface; this is a structure change, not a restyle. No new color tokens (links use existing `--color-primary-dark`, which is AA on white per the contrast gate).
- **The actual bold-subhead value is gated on Sub-project B.** Sub-project A delivers list rendering + readiness; do not claim "bold subheads shipped" until B lands. B is **clinical-sign-off gated** (changes the L0 persona FORMAT clause, which is clinician-signed).

---

# Sub-project A — Frontend Markdown renderer (shippable now)

### Task A1: `MarkdownContent` component + dependencies

A focused, reusable renderer that maps Markdown to the prose design with a safe element allowlist. Self-contained and unit-testable before it touches `message-bubble`.

**Files:**
- Modify: `apps/web/package.json` (add deps)
- Create: `apps/web/components/chat/markdown-content.tsx`
- Test: `apps/web/components/chat/__tests__/markdown-content.test.tsx`

**Interfaces:**
- Produces: `export function MarkdownContent({ content }: { content: string }): JSX.Element` — consumed by Task A2.

- [ ] **Step 1: Add the dependencies**

Run: `cd apps/web && npm install react-markdown@^9 remark-gfm@^4 remark-breaks@^4`
Expected: the three packages appear under `dependencies` in `apps/web/package.json`; `npm ls react-markdown` resolves.

- [ ] **Step 2: Write the failing tests**

Create `apps/web/components/chat/__tests__/markdown-content.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownContent } from '../markdown-content'

describe('MarkdownContent', () => {
  it('renders **bold** as a <strong> subhead', () => {
    const { container } = render(<MarkdownContent content="**Breathing techniques**" />)
    const strong = container.querySelector('strong')
    expect(strong?.textContent).toBe('Breathing techniques')
  })

  it('renders a numbered list as an <ol> with items', () => {
    const { container } = render(<MarkdownContent content={'1. first point\n2. second point'} />)
    const items = container.querySelectorAll('ol > li')
    expect(items.length).toBe(2)
    expect(items[0].textContent).toContain('first point')
  })

  it('numbered list uses logical inline-start padding so RTL indents on the correct side', () => {
    const { container } = render(<MarkdownContent content={'1. a\n2. b'} />)
    // ps-5 (padding-inline-start), NOT pl-5 — flips correctly under dir="rtl"
    expect(container.querySelector('ol')?.className).toContain('ps-5')
  })

  it('renders a [label](url) link as plain-text label with NO clickable anchor (deferred to Sub-project B)', () => {
    const { container } = render(<MarkdownContent content="[NIMH](https://nimh.nih.gov)" />)
    expect(container.querySelector('a')).toBeNull() // no anchor to a model-generated URL
    expect(container.textContent).toContain('NIMH') // the label still shows
  })

  it('renders a BARE autolinked URL as plain text, not a clickable anchor', () => {
    // remark-gfm autolinks a raw URL into a link node whose visible text IS the URL;
    // with `a` unwrapped it renders as the literal URL string (safe, non-clickable).
    const { container } = render(<MarkdownContent content="See https://nimh.nih.gov for more." />)
    expect(container.querySelector('a')).toBeNull()
    expect(container.textContent).toContain('https://nimh.nih.gov')
  })

  it('does NOT render raw HTML (XSS-safe): a script tag is not executed or emitted', () => {
    const { container } = render(<MarkdownContent content={'<script>alert(1)</script> hello'} />)
    expect(container.querySelector('script')).toBeNull()
    expect(container.textContent).toContain('hello')
  })

  it('never emits an anchor, even for a javascript: URL', () => {
    const { container } = render(<MarkdownContent content="[x](javascript:alert(1))" />)
    expect(container.querySelector('a')).toBeNull()
  })

  it('renders plain prose as a paragraph, unchanged', () => {
    render(<MarkdownContent content="You have mentioned feeling stressed lately." />)
    expect(screen.getByText('You have mentioned feeling stressed lately.')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd apps/web && npx vitest run components/chat/__tests__/markdown-content.test.tsx`
Expected: FAIL — `markdown-content` module does not exist.

- [ ] **Step 4: Implement `MarkdownContent`**

Create `apps/web/components/chat/markdown-content.tsx`:

```tsx
'use client'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'

// Safe element allowlist — no raw HTML (rehype-raw is intentionally absent), so the
// renderer cannot emit script/style/iframe. Headings are capped at h3/h4 so a stray
// model `#` cannot produce a page-dominating title; bold subheads come from <strong>.
// 'a' is DELIBERATELY EXCLUDED (see Global Constraints "Links"): with unwrapDisallowed,
// [text](url) renders as its plain-text label with NO clickable anchor. The backend does
// not strip link syntax (output_gate strips emphasis/emoji/em-dash only), so allowing 'a'
// would make clickable model-generated URLs live on day one. Clickable links are a
// Sub-project B decision (vetted-domain allowlist + clinical owner).
const ALLOWED = ['p', 'strong', 'em', 'ul', 'ol', 'li', 'br', 'h3', 'h4', 'blockquote', 'code']

export function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkBreaks]}
      allowedElements={ALLOWED}
      unwrapDisallowed
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 ps-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 ps-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        h3: ({ children }) => <h3 className="mb-2 mt-3 font-semibold first:mt-0">{children}</h3>,
        h4: ({ children }) => <h4 className="mb-2 mt-3 font-semibold first:mt-0">{children}</h4>,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-s-2 border-[var(--color-border)] ps-3 text-[var(--color-text-secondary)]">
            {children}
          </blockquote>
        ),
        // No `a` mapping — 'a' is not in ALLOWED, so links render as plain-text labels.
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd apps/web && npx vitest run components/chat/__tests__/markdown-content.test.tsx`
Expected: PASS (8 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/web/package.json apps/web/package-lock.json apps/web/components/chat/markdown-content.tsx apps/web/components/chat/__tests__/markdown-content.test.tsx
git commit -m "feat(chat): add sanitized RTL-aware MarkdownContent renderer"
```

### Task A2: Render assistant messages through `MarkdownContent`

Switch the assistant branch of `MessageBubble` to render Markdown; keep user messages literal plain text. Update the message-bubble tests whose assertions assumed `whitespace-pre-wrap` plain text for the assistant (these now assert structured rendering); the user-side and dir assertions move to the container.

**Files:**
- Modify: `apps/web/components/chat/message-bubble.tsx`
- Test: `apps/web/components/chat/__tests__/message-bubble.test.tsx`

**Interfaces:**
- Consumes: `MarkdownContent` from Task A1.

- [ ] **Step 1: Write/adjust the failing tests**

In `apps/web/components/chat/__tests__/message-bubble.test.tsx`, replace the `MessageBubble — L4 structure & RTL rendering` describe block (which pins `whitespace-pre-wrap` on the assistant text element) with assertions that match Markdown rendering. Add:

```tsx
describe('MessageBubble — Markdown assistant rendering', () => {
  it('renders an assistant numbered list as an <ol> (not pre-wrapped text)', () => {
    const list = 'Here are a few points:\n1. first point\n2. second point'
    const { container } = render(<MessageBubble message={{ ...base, role: 'ai', content: list }} />)
    expect(container.querySelectorAll('ol > li').length).toBe(2)
  })

  it('renders **bold** from an assistant message as <strong> (auto-upgrades once backend emits it)', () => {
    const { container } = render(<MessageBubble message={{ ...base, role: 'ai', content: '**Subhead**: text' }} />)
    expect(container.querySelector('strong')?.textContent).toBe('Subhead')
  })

  it('keeps the authoritative dir on the bubble container for an Arabic answer', () => {
    const { container } = render(
      <MessageBubble message={{ ...base, role: 'ai', content: 'مرحبا بك', direction: 'rtl' }} />
    )
    // dir lives on the container that wraps the rendered Markdown
    expect(container.querySelector('[dir="rtl"]')).not.toBeNull()
  })

  it('does NOT interpret Markdown in a USER message (literal text)', () => {
    render(<MessageBubble message={{ ...base, role: 'user', content: '**not bold**' }} />)
    // the user bubble shows the literal asterisks, not a <strong>
    expect(screen.getByText('**not bold**')).toBeInTheDocument()
  })
})
```

Keep the existing crisis/system/feedback-button tests as-is. Remove only the old assertions that read `whitespace-pre-wrap` / `textContent === list` off the assistant text node (superseded by the above).

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd apps/web && npx vitest run components/chat/__tests__/message-bubble.test.tsx`
Expected: the new Markdown tests FAIL (assistant still renders raw text; no `<ol>`/`<strong>`).

- [ ] **Step 3: Wire `MarkdownContent` into the assistant branch**

In `apps/web/components/chat/message-bubble.tsx`, add the import and split the body so the assistant renders Markdown while the user stays literal. Replace the render block:

```tsx
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        dir={message.direction ?? 'auto'}
        className={cn(
          'text-[15px] leading-relaxed',
          isUser
            // User turns: literal text in the green bubble. whitespace-pre-wrap stays here.
            ? 'max-w-[78%] whitespace-pre-wrap rounded-2xl rounded-ee-sm bg-[var(--color-primary-dark)] px-4 py-2.5 text-white'
            // Assistant turns: borderless prose, rendered as Markdown (structure handled by the renderer).
            : 'max-w-[680px] leading-7 text-[var(--color-text-primary)]'
        )}
      >
        {isUser ? message.content : <MarkdownContent content={message.content} />}
      </div>
      {!isUser && supabaseId && onFeedback && (
        <FeedbackButtons messageId={supabaseId} onFeedback={onFeedback} />
      )}
    </div>
  )
```

Add at the top with the other imports:

```tsx
import { MarkdownContent } from './markdown-content'
```

- [ ] **Step 4: Run the full message-bubble suite**

Run: `cd apps/web && npx vitest run components/chat/__tests__/message-bubble.test.tsx`
Expected: PASS — new Markdown tests plus the retained crisis/system/user/feedback tests.

- [ ] **Step 5: Run the broader chat suite for regressions**

Run: `cd apps/web && npx vitest run components/chat`
Expected: PASS. (If `chat-interface.test.tsx` asserted assistant text via `whitespace-pre-wrap`, update those reads the same way — assert the rendered text/structure, not the pre-wrap class.)

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/chat/message-bubble.tsx apps/web/components/chat/__tests__/message-bubble.test.tsx
git commit -m "feat(chat): render assistant answers as Markdown (user stays literal)"
```

## Verification (Sub-project A)

- [ ] Unit: `cd apps/web && npx vitest run components/chat` — all green.
- [ ] Production build: `cd apps/web && npx next build` (exit 0), then `npx next start -p 3000`.
- [ ] **LOAD-BEARING RTL check (not optional):** the A2 test rewrite removes the old `whitespace-pre-wrap` RTL/L4 unit assertions; the new unit test only proves a `dir` attribute exists and that `<ol>` uses `ps-5` — it does NOT prove the list visually indents on the correct side. So this manual pass is the real guarantee of the RTL/L4 invariant and must be treated as a gate, not a nicety: seed an **Arabic** assistant message containing a numbered list, render it (with `message.direction='rtl'` set, and separately without it to observe the leading-digit interaction above), and confirm the list markers and indentation sit on the **right**. Repeat at wide + mobile.
- [ ] Visual, EN, wide + mobile (reuse the `chat-layout.spec.ts` seeding): seed an assistant message with a numbered list and confirm it renders as a real `<ol>`. Seed one with `**bold**` and confirm it renders bold — proving the surface is ready for Sub-project B.
- [ ] **Streaming sanity:** send a live message (or seed-then-stream) and confirm partial Markdown mid-stream does not crash or flash badly — an unclosed `**` renders as literal text until closed, then resolves. (react-markdown re-parses each token batch; this is expected.)
- [ ] **Plain-text safety pass:** skim several real prod transcripts rendered through the renderer — confirm ordinary therapeutic prose (no intended markdown) does not mis-render (a stray leading `-` or `#` is the thing to watch; low frequency, but eyeball it before deploy).
- [ ] **Bare-URL readability:** confirm a bare `https://…` in an answer renders as the literal URL string (non-clickable, per the autolink test) and *reads acceptably* — it is safe either way, but if raw URLs look bad inline, that is extra motivation to land the Sub-project B vetted-domain link work rather than a reason to enable anchors in A.

---

# Sub-project B — Backend Markdown emission (SCOPED — needs its own brainstorm + clinical sign-off)

**Do not start B without a brainstorm and clinical sign-off.** The backend currently *strips* markdown as the "PRIMARY style guarantee," so B is not additive — it inverts a clinician-signed policy and must make ~8 deterministic guards markdown-aware. This section scopes the work; it is intentionally not yet broken into TDD steps because the new FORMAT policy is a clinical-content decision (what structure is therapeutically appropriate), not an engineering one.

**Clinical/governance gate (do first):** agree the new formatting policy with the clinical owner — *which* structures are allowed (bold subheads? lists only? links to vetted sources only?), in which intents (knowledge/info_request vs reflective turns), and update the **L0 persona FORMAT clause** (`sage-poc/src/sage_poc/prompts/templates/L0_persona.json:17`, currently "No emojis, no markdown", clinician-signed by Rohan Sarda). New version → new clinical sign-off.

**Engineering touch points (from the backend map — each must be made markdown-aware or explicitly exempted):**

1. **Remove/relax the strip — the hard blocker:** `nodes/output_gate.py:103-130` `_strip_output_format` + regexes `:90-100` deterministically delete `**`/`*`/`***`. This is what currently erases any bold the model emits. Gate it behind the new policy (e.g. allow emphasis, keep em-dash handling).
2. **Banned-opener enforcement — HIGHEST-RISK, must be B's FIRST TDD test.** `output_gate.py:169-205` + `:512-552`: `_BANNED_OPENER_RE` is `^`-anchored and only `lstrip()`s whitespace — a leading `**`/`#`/`- ` would silently disable banned-opener enforcement. This is a *deterministic safety regression hiding inside a formatting change*, not a cosmetic bug. B's first test must prove a banned opener prefixed by markdown (e.g. `**I'm sorry to hear...`) is still caught; the fix strips leading markdown tokens before the anchor test.
3. **Question-discipline** `output_gate.py:135-166` + `:563-574`: splits on `[.!?؟]`; list lines/headings lack terminal punctuation and can mis-merge or drop items. Make list-aware.
4. **Arabic-ratio / English-bleed guard** `output_gate.py:197-205, 417-431, 607-614`: markdown punctuation inflates char counts (could flip the >0.4 Arabic ratio); `_LATIN_WORD_RE` treats link text/URLs as English bleed. Exclude markdown syntax + URLs from the ratio.
5. **History re-injection sanitizer** `prompts/composer.py:30-36 _sanitize_assistant_turn` (+ `:524-527`): strips markdown from prior replies before they re-enter context — decide whether history keeps or drops markdown.
6. **Cultural-output rules** `rules/engine.py:300-332` + `rules/normalize.py:36-49`: substring blocklist/allowlist over the response; `normalize_text` does not strip markdown, so `**word**` evades a `word` blocklist. Normalize markdown before matching.
7. **Translation** `language.py:80-189` (called `output_gate.py:608-611`): markdown survival through Arabic translation is unguaranteed; the strict-retranslate guard trips on Latin runs (URLs). Verify/curate.
8. **Telemetry** `output_gate.py:74-82 _FORMAT_VIOLATIONS`: would flag every markdown turn as a "violation" — update so intended markdown is not logged as a defect.

**B also owns: clickable external links (vetted-domain allowlist at render).** Sub-project A renders link syntax as plain-text labels (the safe floor). Making links clickable is **additive on top of that floor, not a flip from off to on**, and it is a clinical-governance decision because the destination is model-influenced (the RAG corpus is curated/clinician-validated, but retrieved passages are untrusted text and the model composes the final URL — a clean `https://` link to a wrong/injected domain renders identically to a legitimate citation; protocol-filtering does not catch this, only destination-vetting does). Design:
- **Allowlist evaluated at render** in `MarkdownContent`: re-enable the `a` element, but in the `a` component, compute the URL's **host** and render a real anchor (with `target="_blank" rel="noopener noreferrer"`) only if the host is on an approved list (curated source domains + sanctioned helpline/clinical sites); otherwise fall back to the plain-text label A already produces. The safe floor stays the default for everything off-list.
- **LOAD-BEARING #1 — host parsing, not substring match.** Parse the host via `new URL(href).hostname` — **NOT `.host`**, which includes the port (`nih.gov:8080`) that allowlist entries won't carry, so a `.host` compare would silently miss legitimate hosts. Match an approved entry `e` by **`hostname === e` OR `hostname.endsWith('.' + e)`** (subdomain with a dot boundary) — never `href.includes(e)` and never `hostname.includes(e)`. So `nih.gov` approves `nih.gov` and `nimh.nih.gov`, but rejects `nimh.nih.gov.evil.com` (substring-bypass: different host) and `evilnih.gov` (no dot boundary). Pin **all three** failure modes in one test: the substring-bypass host, the no-boundary host, and a host-with-port (`https://nih.gov:8080/x` → `hostname` is `nih.gov`, approved). A substring or `.host` allowlist is the classic bypass.
- **LOAD-BEARING #2 — helpline/crisis-resource ownership.** Crisis-resource presentation is owned by the clinician-authored crisis path that bypasses `output_gate` and is surfaced by the pinned `CrisisCard` — a different surface from the normal assistant renderer. The clinical owner must decide whether normal-turn helpline links are even desirable, or whether helpline routing stays exclusively `CrisisCard`'s job. **Do not let the general link feature silently become a second, ungoverned crisis-resource surface.** If normal-turn helpline links are allowed, their destinations must be the correct UAE/regional ones and on the allowlist.

**Explicitly EXEMPT (do not touch):** the crisis path is a separate node (`graph.py:39-146 _crisis_response_node`) reading clinician-authored JSON (`rules/data/crisis_content/*.json`) and **bypasses `output_gate` entirely** — crisis text stays exactly as authored (it already uses hyphen-bullets by design). Canned `scope_refusal`/`jailbreak` strings are also excluded by existing `gate_path` guards. The streaming tokenizer (`server.py:62-67`) already preserves whitespace/newlines and needs no change.

**B is its own plan.** After the clinical FORMAT decision, write a dedicated `2026-..-markdown-backend-emission.md` whose **first TDD test is the banned-opener bypass (#2)** and whose **acceptance bar is a green safety/quality eval regression**, not a checklist of the touch points above.

**Completeness is proven by the eval, not by this list.** The touch-point map was built from the architecture (output_gate owns post-checks, cultural rules normalize, history re-injection sanitizes) and it maps correctly — but the file/line references and the count of "~8 guards" cannot be treated as exhaustive from here (this repo holds the specs; the live `sage-poc` guards may have drifted). The real risk in "make ~8 guards markdown-aware" is **the ninth guard nobody listed.** So B's definition of done is: the existing safety/quality eval suite (banned-opener recall, Arabic-ratio/bleed, cultural-output rules, and **crisis isolation — prove crisis text is byte-identical before/after, since the crisis node bypasses output_gate**) runs green on markdown-emitting output. Treat any guard the eval surfaces but the list omitted as expected, not a surprise.

---

## Sequencing recommendation

Ship **A first, alone.** It is low-risk (assistant-only, sanitized, no backend change), it immediately improves the lists the backend already emits, and it makes the surface markdown-ready so B lands as a pure backend change with zero further frontend work. Then run the **B clinical gate** (the FORMAT-policy decision) before any backend code. Do not bundle A and B — A is shippable today; B carries clinical governance and guard-recalibration risk that should not block the visible frontend win.
