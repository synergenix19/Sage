import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'crisis') return null // rendered by CrisisCard separately
  if (message.role === 'system') {
    return (
      <div className="mx-auto w-full max-w-xs rounded-xl border border-[var(--color-border)] px-4 py-2 text-center text-xs text-[var(--color-text-secondary)]">
        {message.content}
      </div>
    )
  }

  const isUser = message.role === 'user'
  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-[var(--color-primary-dark)] text-white rounded-ee-sm'
            : 'bg-[var(--color-surface-tinted)] text-[var(--color-text-primary)] rounded-es-sm'
        )}
      >
        {message.content}
      </div>
    </div>
  )
}
