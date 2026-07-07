'use client'

import Link from 'next/link'
import { useState } from 'react'
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

// Generic fallback when a domain has no bundled favicon (or it fails to load).
function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8"
      className="h-4 w-4 text-[var(--color-text-tertiary)]">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18Z" />
    </svg>
  )
}

// Source favicon, served from OUR OWN origin (public/favicons/<domain>.ico) — deliberately
// NOT a third-party favicon service: those fetch client-side per render and would beacon
// "this user is viewing mental-health resource cards" to a third party on every KB answer.
// Bundled at build time; unknown/new domains fall back to a generic icon, never a broken image.
function SourceFavicon({ domain }: { domain: string }) {
  const [failed, setFailed] = useState(false)
  if (!domain || failed) return <GlobeIcon />
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`/favicons/${domain}.ico`}
      alt=""
      aria-hidden="true"
      width={16}
      height={16}
      loading="lazy"
      onError={() => setFailed(true)}
      className="h-4 w-4 rounded-sm object-contain"
    />
  )
}

// "Opens in a new tab" arrow.
function ExternalIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 shrink-0">
      <path d="M7 17 17 7M17 7H8M17 7v9" />
    </svg>
  )
}

// Renders the KB sources for an AI reply, below the message content. A deterministic,
// type-keyed lead-in heading (Further reading / Watch / Learn more) sits above the cards.
// Each card shows a source favicon + title + domain + external-link cue (articles) or a
// click-to-play video facade. The heading and cards stay subdued so the reply's triage
// question remains the primary next action.
export function SourceCard({ sources, direction }: Props) {
  const locale = useLocaleStore((s) => s.locale)
  if (!sources || sources.length === 0) return null

  const label = sourceLabel(sources, locale)
  const headingId = 'source-card-heading'

  // hover + keyboard-focus get the SAME affordance (focus-within fires when the inner
  // link/button is focused) — hover-only feedback would exclude keyboard users.
  const cardCls =
    'rounded-xl border border-[var(--color-border)] transition-colors ' +
    'hover:border-[var(--color-primary)] hover:bg-[var(--color-bg-secondary)] ' +
    'focus-within:border-[var(--color-primary)] focus-within:bg-[var(--color-bg-secondary)]'
  const focusRing =
    'rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]'

  return (
    <aside
      aria-label={label ? undefined : 'Sources'}
      aria-labelledby={label ? headingId : undefined}
      dir={direction ?? 'auto'}
      className="mt-6 flex w-full max-w-[680px] flex-col gap-2"
    >
      {label && (
        <h3
          id={headingId}
          className="mb-1 text-xs font-medium uppercase tracking-wider text-[var(--color-text-tertiary)]"
        >
          {label}
        </h3>
      )}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {sources.map((source, i) => {
          const domain = sourceDomain(source.url)
          return (
            <li key={`${source.url}-${i}`} className={cardCls}>
              {source.type === 'article' ? (
                <Link
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`group flex items-start gap-3 p-4 ${focusRing}`}
                >
                  <span className="mt-0.5 shrink-0">
                    <SourceFavicon domain={domain} />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate text-sm font-medium text-[var(--color-primary-dark)] group-hover:underline">
                      {source.title}
                    </span>
                    {domain && (
                      <span className="truncate text-xs text-[var(--color-text-tertiary)]">{domain}</span>
                    )}
                  </span>
                  <span className="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]">
                    <ExternalIcon />
                  </span>
                </Link>
              ) : (
                <div className="flex flex-col gap-2 p-4">
                  <div className="flex items-center gap-2">
                    <span className="shrink-0">
                      <SourceFavicon domain={domain} />
                    </span>
                    <p className="min-w-0 flex-1 truncate text-sm font-medium text-[var(--color-text-primary)]">
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
