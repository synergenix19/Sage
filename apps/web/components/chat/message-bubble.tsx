import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'
import { FeedbackButtons } from './feedback-buttons'

interface Props {
  message: ChatMessage
  supabaseId?: string
  onFeedback?: (messageId: string, value: 1 | -1) => void
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

  return (
    <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        dir={message.direction ?? 'auto'}
        className={cn(
          // whitespace-pre-wrap: render the L4 line structure (numbered lists) instead of
          // collapsing newlines to run-on text. Direction is authoritative from the backend
          // (message.direction, derived from detected_language); dir="auto" is only the
          // fallback when it is absent. Authoritative direction fixes the case where an
          // Arabic answer opens on a Latin token, which dir="auto" alone resolves LTR.
          // Both whitespace-pre-wrap and dir must stay on every branch (pinned by tests).
          'whitespace-pre-wrap leading-relaxed',
          isUser
            // User turns stay as green bubbles (the one bubbled speaker).
            ? 'max-w-[78%] rounded-2xl rounded-ee-sm bg-[var(--color-primary-dark)] px-4 py-2.5 text-sm text-white'
            // Assistant turns render as borderless typographic prose, regardless of length
            // (Abby-style). No bubble for any AI message — short or long.
            : 'max-w-[680px] text-[15px] leading-7 text-[var(--color-text-primary)]'
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
