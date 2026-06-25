import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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
