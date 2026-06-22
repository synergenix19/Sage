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

// L4 light-structure rendering: the content was rendered as raw text with no dir and
// collapsed whitespace, so numbered lists flattened to run-on text (silently in EN,
// visibly broken/RTL-jumbled in AR). These pin the dir="auto" + whitespace-pre-wrap fix.
describe('MessageBubble — L4 structure & RTL rendering', () => {
  it('sets dir="auto" so an Arabic answer resolves right-to-left', () => {
    render(<MessageBubble message={{ ...base, role: 'ai', content: 'مرحبا بك' }} />)
    expect(screen.getByText('مرحبا بك')).toHaveAttribute('dir', 'auto')
  })

  it('preserves newlines so a numbered list renders as separate lines, not run-on', () => {
    const list = 'Here are a few points:\n1. first point\n2. second point'
    render(<MessageBubble message={{ ...base, role: 'ai', content: list }} />)
    const el = screen.getByText(/Here are a few points/)
    expect(el.className).toContain('whitespace-pre-wrap')
    expect(el.textContent).toBe(list) // newlines intact in the DOM, not collapsed
  })

  // Edge A (reviewer, now FIXED): an Arabic answer whose lead opens on a non-Arabic token
  // ("CBT") resolves LTR under dir="auto" (first-strong-character heuristic). The backend
  // sends the authoritative direction (X-Sage-Direction, from detected_language); the
  // renderer uses it, so the answer is RTL regardless of the lead character.
  it('uses server-provided direction=rtl even when an Arabic answer opens on a non-Arabic token', () => {
    const content = '"CBT" هو علاج فعّال ومدعوم بالأبحاث للقلق'
    render(<MessageBubble message={{ ...base, role: 'ai', content, direction: 'rtl' }} />)
    const el = screen.getByText(/CBT/)
    expect(el).toHaveAttribute('dir', 'rtl')
    expect(el.textContent).toBe(content)
  })

  it('uses server-provided direction=ltr for an English answer', () => {
    render(<MessageBubble message={{ ...base, role: 'ai', content: 'Hello there', direction: 'ltr' }} />)
    expect(screen.getByText('Hello there')).toHaveAttribute('dir', 'ltr')
  })

  // Edge B (reviewer): whitespace-pre-wrap now faithfully renders the model's whitespace,
  // including mistakes. Pin that messy input is preserved (degrades, does not crash or drop).
  it('renders messy multi-line whitespace faithfully without dropping content', () => {
    const messy = 'Lead sentence.\n\n\n1. first   \n2. second  \n'
    render(<MessageBubble message={{ ...base, role: 'ai', content: messy }} />)
    const el = screen.getByText(/Lead sentence/)
    expect(el.className).toContain('whitespace-pre-wrap')
    expect(el.textContent).toBe(messy)
  })
})
