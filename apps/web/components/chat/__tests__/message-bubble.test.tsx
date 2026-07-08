import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { MessageBubble } from '../message-bubble'
import type { ChatMessage } from '@cdai/types'

vi.mock('../feedback-buttons', () => ({
  FeedbackButtons: vi.fn(() => <div data-testid="feedback-buttons" />),
}))

const base: ChatMessage = {
  id: '1',
  sessionId: 's1',
  intent: null,
  createdAt: '',
  content: 'Hello',
  role: 'user',
}

describe('MessageBubble', () => {
  it('renders user message content', () => {
    render(<MessageBubble message={{ ...base, role: 'user' }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders ai message content', () => {
    render(<MessageBubble message={{ ...base, role: 'ai' }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders nothing for crisis role (handled by CrisisCard)', () => {
    const { container } = render(<MessageBubble message={{ ...base, role: 'crisis' }} />)
    expect(container.firstChild).toBeNull()
  })
})

describe('MessageBubble feedback buttons', () => {
  it('shows FeedbackButtons for ai messages that have a supabaseId', () => {
    const message: ChatMessage = {
      id: 'sdk-id', role: 'ai', content: 'Hello', intent: null,
      sessionId: 'sess-1', createdAt: '',
    }
    render(
      <MessageBubble
        message={message}
        supabaseId="supabase-uuid-123"
        onFeedback={vi.fn()}
      />
    )
    expect(screen.getByTestId('feedback-buttons')).toBeInTheDocument()
  })

  it('does not show FeedbackButtons for user messages', () => {
    const message: ChatMessage = {
      id: 'sdk-id', role: 'user', content: 'Hello', intent: null,
      sessionId: 'sess-1', createdAt: '',
    }
    render(
      <MessageBubble
        message={message}
        supabaseId="supabase-uuid-123"
        onFeedback={vi.fn()}
      />
    )
    expect(screen.queryByTestId('feedback-buttons')).not.toBeInTheDocument()
  })

  it('does not show FeedbackButtons when supabaseId is absent', () => {
    const message: ChatMessage = {
      id: 'sdk-id', role: 'ai', content: 'Hello', intent: null,
      sessionId: 'sess-1', createdAt: '',
    }
    render(<MessageBubble message={message} />)
    expect(screen.queryByTestId('feedback-buttons')).not.toBeInTheDocument()
  })
})

// Replaces the old "L4 structure & RTL rendering" block which pinned whitespace-pre-wrap
// and textContent on the assistant text node. Those assertions are superseded because the
// assistant branch now renders via MarkdownContent (structured HTML, not pre-wrapped text).
// The RTL/dir invariant is preserved: dir lives on the bubble container div, not the inner
// text node produced by the Markdown renderer.
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

// Quick win #1: ALL assistant messages render as borderless prose (Abby-style),
// regardless of length. Quick win #2 speaker separation is now prose-vs-green-bubble.
describe('MessageBubble — speaker styling & prose', () => {
  it('renders a multi-line assistant answer without a bubble (typographic prose)', () => {
    const long = 'Here are several resources:\n1. first point\n2. second point'
    const { container } = render(<MessageBubble message={{ ...base, role: 'ai', content: long }} />)
    // The container div (not the inner MarkdownContent text node) must not have bubble classes
    const bubbleDiv = container.querySelector('[dir]') as HTMLElement
    expect(bubbleDiv.className).not.toContain('rounded-2xl')
    expect(bubbleDiv.className).not.toContain('color-surface')
    // The list renders as structured <ol> via MarkdownContent
    expect(container.querySelectorAll('ol > li').length).toBe(2)
  })

  it('renders a long single-line assistant answer (>280 chars) without a bubble', () => {
    const long = 'a'.repeat(300)
    const { container } = render(<MessageBubble message={{ ...base, role: 'ai', content: long }} />)
    const bubbleDiv = container.querySelector('[dir]') as HTMLElement
    expect(bubbleDiv.className).not.toContain('rounded-2xl')
  })

  it('renders a SHORT single-paragraph assistant turn as prose too (no bubble)', () => {
    // The representative everyday reply: one paragraph, <280 chars, no newline.
    // Previously this kept a (recolored) bubble; now it must render as prose like Abby.
    const short = "You've mentioned feeling stressed lately. What's been contributing to it, if you feel like sharing?"
    const { container } = render(<MessageBubble message={{ ...base, role: 'ai', content: short }} />)
    const bubbleDiv = container.querySelector('[dir]') as HTMLElement
    expect(bubbleDiv.className).not.toContain('rounded-2xl')
    expect(bubbleDiv.className).not.toContain('color-surface')
    expect(bubbleDiv.className).not.toContain('color-border')
    // User stays literal; assistant is Markdown. No whitespace-pre-wrap on the assistant container.
    expect(screen.getByText(/feeling stressed lately/)).toBeInTheDocument()
  })

  it('renders a one-line acknowledgement as prose (no bubble)', () => {
    const { container } = render(<MessageBubble message={{ ...base, role: 'ai', content: 'Sure, I can help.' }} />)
    const bubbleDiv = container.querySelector('[dir]') as HTMLElement
    expect(bubbleDiv.className).not.toContain('rounded-2xl')
    expect(bubbleDiv.className).not.toContain('bg-[var(--color-surface-muted)]')
  })

  it('keeps the user bubble green and bubbled', () => {
    render(<MessageBubble message={{ ...base, role: 'user', content: 'Hi' }} />)
    const el = screen.getByText('Hi')
    expect(el.className).toContain('bg-[var(--color-primary-dark)]')
    expect(el.className).toContain('rounded-2xl')
  })

  // RTL on the NEW long-form branch: the existing L4/RTL block only covers short,
  // single-line fixtures. A long Arabic answer must still resolve right-to-left via
  // the container's dir attribute and render structured list items via MarkdownContent.
  it('renders a long Arabic answer right-to-left with list items as <ol> (no bubble)', () => {
    const arLong = 'إليك بعض التقنيات:\n1. التنفس البطيء العميق\n2. تمرين التأريض الحسي'
    const { container } = render(
      <MessageBubble message={{ ...base, role: 'ai', content: arLong, direction: 'rtl' }} />
    )
    // dir lives on the container div, not the inner text node
    expect(container.querySelector('[dir="rtl"]')).not.toBeNull()
    // list renders as <ol> via MarkdownContent
    expect(container.querySelectorAll('ol > li').length).toBe(2)
    // no bubble on the container
    const bubbleDiv = container.querySelector('[dir="rtl"]') as HTMLElement
    expect(bubbleDiv.className).not.toContain('rounded-2xl')
  })
})

// Task 6: Sources card renders below the AI message when message.sources is present
// (X-Sage-Sources, parsed client-side in chat-interface.tsx — see its own tests for the
// malformed-header fallback). 'article' -> a link, 'video' -> an embedded player.
describe('MessageBubble — Sources card', () => {
  it('renders an article link', () => {
    render(
      <MessageBubble
        message={{
          ...base,
          role: 'ai',
          sources: [{ type: 'article', title: 'Understanding Anxiety', url: 'https://kb/a', citation: 'c' }],
        }}
      />
    )
    expect(screen.getByRole('link', { name: /Understanding Anxiety/ })).toHaveAttribute('href', 'https://kb/a')
  })

  it('embeds YouTube via youtube-nocookie', () => {
    render(
      <MessageBubble
        message={{
          ...base,
          role: 'ai',
          sources: [{ type: 'video', title: 'V', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', citation: 'c' }],
        }}
      />
    )
    expect(screen.getByTitle('V').getAttribute('src')).toContain('youtube-nocookie.com/embed/')
  })

  it('renders the Arabic sources card RTL', () => {
    render(
      <MessageBubble
        message={{
          ...base,
          role: 'ai',
          direction: 'rtl',
          sources: [{ type: 'article', title: 'القلق', url: 'https://kb/a', citation: 'c' }],
        }}
      />
    )
    expect(screen.getByLabelText('Sources')).toHaveAttribute('dir', 'rtl')
  })

  it('renders no card when sources are absent', () => {
    render(<MessageBubble message={{ ...base, role: 'ai' }} />)
    expect(screen.queryByLabelText('Sources')).toBeNull()
  })

  it('renders no card for an empty sources array', () => {
    render(<MessageBubble message={{ ...base, role: 'ai', sources: [] }} />)
    expect(screen.queryByLabelText('Sources')).toBeNull()
  })

  it('does not render a card on user messages even if sources were somehow attached', () => {
    render(
      <MessageBubble
        message={{
          ...base,
          role: 'user',
          sources: [{ type: 'article', title: 'Understanding Anxiety', url: 'https://kb/a', citation: 'c' }],
        }}
      />
    )
    expect(screen.queryByLabelText('Sources')).toBeNull()
  })
})

// Task 6: opt-in typewriter reveal (spec §3). reveal is undefined/false by default, so every
// test above must keep passing unchanged — these cases only cover the new opt-in path.
// Note: MessageRole is 'user' | 'ai' | 'system' | 'crisis' (no 'assistant' literal), so the
// fixture below uses 'ai' to match @cdai/types, not the brief's illustrative 'assistant'.
describe('MessageBubble reveal', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  function aiMsg(content: string): ChatMessage {
    return { ...base, role: 'ai', content, direction: 'ltr' }
  }

  it('reveal=false renders full content immediately (back-compat)', () => {
    render(<MessageBubble message={aiMsg('hello there friend')} />)
    expect(screen.getByText('hello there friend')).toBeInTheDocument()
  })

  it('reveal=true reveals progressively then completes, keeping dir + whitespace-pre-wrap while typing', () => {
    render(<MessageBubble message={aiMsg('one two three four five six')} reveal />)
    const node = screen.getByTestId('message-content')
    expect(node).toHaveAttribute('dir', 'ltr')
    expect(node.className).toContain('whitespace-pre-wrap')
    act(() => { vi.advanceTimersByTime(3_000) })
    expect(node.textContent).toBe('one two three four five six')
  })

  it('calls onRevealComplete exactly once when the reveal finishes', () => {
    const onRevealComplete = vi.fn()
    render(<MessageBubble message={aiMsg('a b c')} reveal onRevealComplete={onRevealComplete} />)
    act(() => { vi.advanceTimersByTime(3_000) })
    expect(onRevealComplete).toHaveBeenCalledTimes(1)
  })

  it('does not call onRevealComplete when reveal is false', () => {
    const onRevealComplete = vi.fn()
    render(<MessageBubble message={aiMsg('a b c')} onRevealComplete={onRevealComplete} />)
    act(() => { vi.advanceTimersByTime(3_000) })
    expect(onRevealComplete).not.toHaveBeenCalled()
  })

  it('tap-to-skip: clicking the content node while typing completes the reveal immediately', () => {
    render(<MessageBubble message={aiMsg('one two three four five six seven eight')} reveal />)
    const node = screen.getByTestId('message-content')
    fireEvent.click(node)
    expect(node.textContent).toBe('one two three four five six seven eight')
  })
})

// Finding 2 (whole-branch review): useTypewriter is a JS setInterval — a CSS reduced-motion
// media query cannot stop it, so reduced-motion users still got word-by-word reveal
// (violates spec §3.5 and the shipped PRESENCE_QA_CHECKLIST.md). MessageBubble now reads
// usePrefersReducedMotion() and disables the typewriter (enabled=false) whenever it's set,
// so the full content renders via MarkdownContent immediately instead of animating.
describe('MessageBubble reveal — prefers-reduced-motion (Finding 2)', () => {
  const originalMatchMedia = window.matchMedia

  afterEach(() => {
    // Restore the global vitest.setup.ts matchMedia stub so this override never leaks
    // into other test files (or later tests in this file) that assume matches:false.
    window.matchMedia = originalMatchMedia
  })

  function aiMsg(content: string): ChatMessage {
    return { ...base, role: 'ai', content, direction: 'ltr' }
  }

  it('renders the FULL content immediately with no progressive reveal when prefers-reduced-motion is set', () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }))

    const full = 'one two three four five six seven eight'
    render(<MessageBubble message={aiMsg(full)} reveal />)
    const node = screen.getByTestId('message-content')
    // Full text present on the very first render — never a partial word-1 slice.
    expect(node.textContent).toBe(full)
  })
})

// Item D (2026-07-08): replies containing block-level Markdown (lists/headings/bold) skip the
// typewriter and take the fade path — a calm single paint of the rendered Markdown, no raw→snap
// reflow seam. Plain prose still types. Render mode is three-valued: instant | fade | typewriter.
describe('MessageBubble reveal — block-Markdown fade path (Item D)', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  function aiMsg(content: string): ChatMessage {
    return { ...base, role: 'ai', content, direction: 'ltr' }
  }

  it('a formatted reply (list) skips the typewriter and fades in the full content in one paint', () => {
    const list = '- alpha item\n- beta item\n- gamma item'
    render(<MessageBubble message={aiMsg(list)} reveal />)
    const node = screen.getByTestId('message-content')
    // Full content from the first render — no partial word-1 slice, no raw→snap.
    expect(node.textContent).toContain('alpha item')
    expect(node.textContent).toContain('gamma item')
    // Fade path (motion-safe), NOT the typewriter path (no raw whitespace-pre-wrap phase).
    expect(node.className).toContain('motion-safe:animate-[fadeIn')
    expect(node.className).not.toContain('whitespace-pre-wrap')
    // Advancing time starts no progressive reveal — content is stable.
    act(() => { vi.advanceTimersByTime(3_000) })
    expect(node.textContent).toContain('gamma item')
  })

  it('plain prose still types (no fade class while typing)', () => {
    render(<MessageBubble message={aiMsg('one two three four five six')} reveal />)
    const node = screen.getByTestId('message-content')
    expect(node.className).not.toContain('animate-[fadeIn')
    expect(node.className).toContain('whitespace-pre-wrap') // the typewriter (typing) path
  })

  it.each([
    ['`)`-delimited ordered list', '1) alpha item\n2) beta item\n3) gamma item', 'gamma item'],
    ['blockquote', '> a quoted reflection\nand more', 'quoted reflection'],
  ])('routes %s to the fade path, not the typewriter', (_label, content, needle) => {
    render(<MessageBubble message={aiMsg(content)} reveal />)
    const node = screen.getByTestId('message-content')
    expect(node.className).toContain('motion-safe:animate-[fadeIn')
    expect(node.className).not.toContain('whitespace-pre-wrap')
    act(() => { vi.advanceTimersByTime(3_000) })
    expect(node.textContent).toContain(needle)
  })
})
