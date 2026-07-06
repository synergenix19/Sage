import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'
import { FeedbackButtons } from './feedback-buttons'
import { MarkdownContent } from './markdown-content'
import { SourceCard } from './source-card'

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
      {!isUser && message.sources && message.sources.length > 0 && (
        <SourceCard sources={message.sources} direction={message.direction} />
      )}
      {!isUser && supabaseId && onFeedback && (
        <FeedbackButtons messageId={supabaseId} onFeedback={onFeedback} />
      )}
    </div>
  )
}
