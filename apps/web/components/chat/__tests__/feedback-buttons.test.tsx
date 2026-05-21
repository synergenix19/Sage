// components/chat/__tests__/feedback-buttons.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { FeedbackButtons } from '../feedback-buttons'

describe('FeedbackButtons', () => {
  it('renders thumbs up and thumbs down buttons', () => {
    render(<FeedbackButtons messageId="msg-1" onFeedback={vi.fn()} />)
    expect(screen.getByRole('button', { name: /thumbs up/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /thumbs down/i })).toBeInTheDocument()
  })

  it('calls onFeedback with 1 when thumbs up clicked', () => {
    const onFeedback = vi.fn()
    render(<FeedbackButtons messageId="msg-1" onFeedback={onFeedback} />)
    fireEvent.click(screen.getByRole('button', { name: /thumbs up/i }))
    expect(onFeedback).toHaveBeenCalledWith('msg-1', 1)
  })

  it('calls onFeedback with -1 when thumbs down clicked', () => {
    const onFeedback = vi.fn()
    render(<FeedbackButtons messageId="msg-1" onFeedback={onFeedback} />)
    fireEvent.click(screen.getByRole('button', { name: /thumbs down/i }))
    expect(onFeedback).toHaveBeenCalledWith('msg-1', -1)
  })

  it('shows selected state after clicking thumbs up', () => {
    render(<FeedbackButtons messageId="msg-1" onFeedback={vi.fn()} />)
    const upBtn = screen.getByRole('button', { name: /thumbs up/i })
    fireEvent.click(upBtn)
    expect(upBtn).toHaveAttribute('aria-pressed', 'true')
  })

  it('disables both buttons after a selection', () => {
    render(<FeedbackButtons messageId="msg-1" onFeedback={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /thumbs up/i }))
    expect(screen.getByRole('button', { name: /thumbs up/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /thumbs down/i })).toBeDisabled()
  })
})
