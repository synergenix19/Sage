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
