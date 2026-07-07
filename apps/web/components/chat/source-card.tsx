'use client'

import Link from 'next/link'
import type { Source } from '@cdai/types'
import { VideoEmbed } from './video-embed'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { sourceLabel } from './source-card-labels'

interface Props {
  sources: Source[]
  // Mirrors message.direction on the parent ChatMessage (X-Sage-Direction) — falls
  // back to 'auto' the same way message-bubble.tsx does when absent.
  direction?: 'ltr' | 'rtl'
}

// Renders the KB sources for an AI reply, below the message content. A deterministic,
// type-keyed lead-in heading (Further reading / Watch / Learn more) is shown above the
// cards when reviewed copy exists for the locale. The heading is intentionally SUBDUED
// (small, uppercase, tertiary colour) so the reply's triage question stays the primary
// next action and the cards read as the secondary, self-serve reading affordance.
export function SourceCard({ sources, direction }: Props) {
  const locale = useLocaleStore((s) => s.locale)
  if (!sources || sources.length === 0) return null

  const label = sourceLabel(sources, locale)
  const headingId = 'source-card-heading'

  return (
    <aside
      // When a visible heading is shown, name the landmark by it; otherwise keep a
      // generic label so screen readers still announce the region.
      aria-label={label ? undefined : 'Sources'}
      aria-labelledby={label ? headingId : undefined}
      dir={direction ?? 'auto'}
      className="mt-2 flex w-full max-w-[680px] flex-col gap-2"
    >
      {label && (
        <h3
          id={headingId}
          className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]"
        >
          {label}
        </h3>
      )}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {sources.map((source, i) => (
          <li
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
          </li>
        ))}
      </ul>
    </aside>
  )
}
