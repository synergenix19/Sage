'use client'

import Link from 'next/link'
import type { Source } from '@cdai/types'
import { VideoEmbed } from './video-embed'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { sourceLabel, sourceDomain } from './source-card-labels'

interface Props {
  sources: Source[]
  // Mirrors message.direction on the parent ChatMessage (X-Sage-Direction) — falls
  // back to 'auto' the same way message-bubble.tsx does when absent.
  direction?: 'ltr' | 'rtl'
}

// Small "opens in a new tab" arrow.
function ExternalIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3.5 w-3.5 shrink-0"
    >
      <path d="M7 17 17 7M17 7H8M17 7v9" />
    </svg>
  )
}

// Renders the KB sources for an AI reply, below the message content. A deterministic,
// type-keyed lead-in heading (Further reading / Watch / Learn more) sits above the cards.
// Each card shows the title + its source domain + an external-link cue (articles) or a
// click-to-play video facade — the "meaningful source + link" pattern, from data we already
// have (title, url). The heading and cards stay subdued so the reply's triage question
// remains the primary next action.
export function SourceCard({ sources, direction }: Props) {
  const locale = useLocaleStore((s) => s.locale)
  if (!sources || sources.length === 0) return null

  const label = sourceLabel(sources, locale)
  const headingId = 'source-card-heading'

  return (
    <aside
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
        {sources.map((source, i) => {
          const domain = sourceDomain(source.url)
          return (
            <li
              key={`${source.url}-${i}`}
              className="rounded-xl border border-[var(--color-border)] transition-colors hover:border-[var(--color-primary)]"
            >
              {source.type === 'article' ? (
                <Link
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-start justify-between gap-3 p-3"
                >
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate text-sm font-medium text-[var(--color-primary-dark)] group-hover:underline">
                      {source.title}
                    </span>
                    {domain && (
                      <span className="truncate text-xs text-[var(--color-text-tertiary)]">{domain}</span>
                    )}
                  </span>
                  <span className="mt-0.5 text-[var(--color-text-tertiary)]">
                    <ExternalIcon />
                  </span>
                </Link>
              ) : (
                <div className="flex flex-col gap-2 p-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="min-w-0 truncate text-sm font-medium text-[var(--color-text-primary)]">
                      {source.title}
                    </p>
                    {domain && (
                      <span className="shrink-0 text-xs text-[var(--color-text-tertiary)]">{domain}</span>
                    )}
                  </div>
                  <VideoEmbed url={source.url} title={source.title} />
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
