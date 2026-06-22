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

  // Edge A (reviewer): dir="auto" keys off the first strong char. An Arabic answer whose
  // lead opens on a non-Arabic char is the case that can land on the wrong side. jsdom does
  // not run the bidi algorithm, so this pins attribute + content integrity; the visual
  // direction on this mixed-lead case is confirmed in the app-UI check (the real T4).
  it('keeps dir="auto" and full content when an Arabic answer opens on a non-Arabic character', () => {
    const content = '"CBT" هو علاج فعّال ومدعوم بالأبحاث للقلق'
    render(<MessageBubble message={{ ...base, role: 'ai', content }} />)
    const el = screen.getByText(/CBT/)
    expect(el).toHaveAttribute('dir', 'auto')
    expect(el.textContent).toBe(content)
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
