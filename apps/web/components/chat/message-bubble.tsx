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
        dir="auto"
        className={cn(
          // whitespace-pre-wrap: render the L4 line structure (numbered lists) instead of
          // collapsing newlines to run-on text. dir="auto": resolve direction from the first
          // strong character so Arabic answers render RTL (mixed-lead cases verified in the UI).
          'max-w-[78%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-[var(--color-primary-dark)] text-white rounded-ee-sm'
            : 'bg-[var(--color-surface-tinted)] text-[var(--color-text-primary)] rounded-es-sm'
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
