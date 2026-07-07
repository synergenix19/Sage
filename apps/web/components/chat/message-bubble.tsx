'use client'
import { useEffect } from 'react'
import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'
import { useTypewriter } from '@/hooks/use-typewriter'
import { usePrefersReducedMotion } from '@/hooks/use-prefers-reduced-motion'
import { FeedbackButtons } from './feedback-buttons'
import { MarkdownContent } from './markdown-content'
import { SourceCard } from './source-card'

interface Props {
  message: ChatMessage
  supabaseId?: string
  onFeedback?: (messageId: string, value: 1 | -1) => void
  /** Opt-in typewriter reveal (spec §3). Default false: byte-identical to the
   *  pre-reveal renderer (full content, no timers). Never applies to the user's
   *  own turn — only the assistant's reply is "typed". */
  reveal?: boolean
  onRevealComplete?: () => void
}

export function MessageBubble({ message, supabaseId, onFeedback, reveal = false, onRevealComplete }: Props) {
  // Hook must be called unconditionally (rules of hooks) regardless of role/branch below.
  // When reveal is false it resolves to the full text on the first render, so the
  // reveal=false path stays byte-identical to today.
  // prefers-reduced-motion (spec §3.5): the typewriter is a JS setInterval, which a CSS
  // media query cannot stop. Disabling it here (enabled=false) makes useTypewriter resolve
  // to the full text immediately (done=true), so the content renders via MarkdownContent
  // instantly instead of animating word-by-word.
  const reducedMotion = usePrefersReducedMotion()
  const { displayed, done, complete } = useTypewriter(message.content, {
    enabled: reveal === true && !reducedMotion,
  })

  useEffect(() => {
    if (reveal && done) onRevealComplete?.()
  }, [reveal, done, onRevealComplete])

  if (message.role === 'crisis') return null
  if (message.role === 'system') {
    return (
      <div className="mx-auto w-full max-w-xs rounded-xl border border-[var(--color-border)] px-4 py-2 text-center text-xs text-[var(--color-text-secondary)]">
        {message.content}
      </div>
    )
  }

  const isUser = message.role === 'user'
  // Reveal only ever applies to the assistant's own reply, never the user's turn.
  const revealing = !isUser && reveal === true
  const isTyping = revealing && !done

  return (
    <div className={cn('flex flex-col', isUser ? 'items-end' : 'items-start')}>
      <div
        data-testid="message-content"
        dir={message.direction ?? 'auto'}
        onClick={isTyping ? complete : undefined}
        className={cn(
          'text-[15px] leading-relaxed',
          isUser
            // User turns: literal text in the green bubble. whitespace-pre-wrap stays here.
            ? 'max-w-[78%] whitespace-pre-wrap rounded-2xl rounded-ee-sm bg-[var(--color-primary-dark)] px-4 py-2.5 text-white'
            // Assistant turns: borderless prose, rendered as Markdown (structure handled by the renderer).
            : 'max-w-[680px] leading-7 text-[var(--color-text-primary)]',
          // Mid-reveal, the assistant node shows the raw typewriter slice (not yet parsed
          // as Markdown), so preserve literal line breaks the same way the user bubble does.
          isTyping && 'whitespace-pre-wrap'
        )}
      >
        {isUser
          ? message.content
          : isTyping
            ? displayed
            : <MarkdownContent content={message.content} />}
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
