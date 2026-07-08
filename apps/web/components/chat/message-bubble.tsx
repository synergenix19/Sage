'use client'
import { useEffect } from 'react'
import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'
import { useTypewriter } from '@/hooks/use-typewriter'
import { usePrefersReducedMotion } from '@/hooks/use-prefers-reduced-motion'
import { FeedbackButtons } from './feedback-buttons'
import { MarkdownContent } from './markdown-content'
import { SourceCard } from './source-card'

// Block-level Markdown = bullet/ordered lists, headings, blockquotes, or bold — the
// constructs whose raw→formatted transition produces a visible reflow if typed then snapped.
// Such replies skip the typewriter and render once via the fade path (spec §3.4/§3.5,
// three-valued render mode: instant | fade | typewriter). ~6% of prod AI replies match
// (2026-07 sample). Ordered lists accept BOTH `.` and `)` delimiters (CommonMark), and
// blockquotes (`> `) are included since MarkdownContent renders them as a bordered block.
// A false positive only over-routes to the (safe) fade path; a false negative reintroduces
// the seam — so this errs toward matching.
const BLOCK_MARKDOWN = /(?:^|\n)[ \t]*(?:[-*+][ \t]|#{1,6}[ \t]|\d+[.)][ \t]|>[ \t])|\*\*[^*]+\*\*/
function hasBlockMarkdown(text: string): boolean {
  return BLOCK_MARKDOWN.test(text)
}

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
  // Render mode is three-valued (spec §3.4/§3.5): crisis → instant (CrisisCard, elsewhere);
  // reduced-motion OR block-Markdown reply → fade (calm single paint, no raw→snap seam);
  // plain prose → typewriter. The typewriter is a JS setInterval a CSS media query can't
  // stop, so both the reduced-motion (spec §3.5) and the formatted-reply cases disable it
  // (enabled=false → useTypewriter resolves to full text immediately) and take the fade path.
  const reducedMotion = usePrefersReducedMotion()
  const formatted = hasBlockMarkdown(message.content)
  const { displayed, done, complete } = useTypewriter(message.content, {
    enabled: reveal === true && !reducedMotion && !formatted,
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
  // Formatted or reduced-motion replies skip the typewriter and fade in as one paint.
  // For plain prose, `!done` keeps isTyping true only while typing; once done, fadeIn is
  // false (skipTypewriter false), so a just-typed message does NOT then fade — no double animation.
  const skipTypewriter = revealing && (reducedMotion || formatted)
  const isTyping = revealing && !skipTypewriter && !done
  const fadeIn = skipTypewriter

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
          isTyping && 'whitespace-pre-wrap',
          // Fade path (formatted reply or reduced-motion): calm single paint, motion-safe so
          // reduced-motion users get an instant appearance rather than an animation.
          fadeIn && 'motion-safe:animate-[fadeIn_300ms_ease-out]'
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
