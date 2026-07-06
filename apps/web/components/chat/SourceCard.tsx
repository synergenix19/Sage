import Link from 'next/link'
import type { Source } from '@cdai/types'
import { VideoEmbed } from './VideoEmbed'

interface Props {
  sources: Source[]
  // Mirrors message.direction on the parent ChatMessage (X-Sage-Direction) — falls
  // back to 'auto' the same way message-bubble.tsx does when absent.
  direction?: 'ltr' | 'rtl'
}

// Renders the KB sources for an AI reply, below the message content. Type-switches
// per entry: 'article' -> a plain link, 'video' -> an embedded player.
export function SourceCard({ sources, direction }: Props) {
  if (!sources || sources.length === 0) return null

  return (
    <aside
      aria-label="Sources"
      dir={direction ?? 'auto'}
      className="mt-2 flex w-full max-w-[680px] flex-col gap-2"
    >
      {sources.map((source, i) => (
        <div
          key={`${source.url}-${i}`}
          className="rounded-xl border border-[var(--color-border)] p-3"
        >
          {source.type === 'article' ? (
            <Link
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-[var(--color-primary-dark)] underline"
            >
              {source.title}
            </Link>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium text-[var(--color-text-primary)]">{source.title}</p>
              <VideoEmbed url={source.url} title={source.title} />
            </div>
          )}
        </div>
      ))}
    </aside>
  )
}
