'use client'

// Provider-agnostic video: a lightweight FACADE (thumbnail + play button) that loads the
// player only on click — faster and cleaner than an always-mounted iframe, and a deliberate
// play action. Detects a known provider from the canonical `url`; falls back to a plain
// HTML5 <video> for anything else (self-hosted clips). A second provider is one added branch.

import { useState } from 'react'

function youtubeId(url: string): string | null {
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/)
  return m ? m[1] : null
}

interface Props {
  url: string
  title: string
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6 translate-x-[1px] fill-white">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

export function VideoEmbed({ url, title }: Props) {
  const yt = youtubeId(url)
  const [playing, setPlaying] = useState(false)

  if (yt) {
    if (playing) {
      return (
        <iframe
          title={title}
          src={`https://www.youtube-nocookie.com/embed/${yt}?autoplay=1`}
          className="aspect-video w-full rounded-lg border-0"
          allow="autoplay; encrypted-media"
          referrerPolicy="strict-origin-when-cross-origin"
          loading="lazy"
        />
      )
    }
    return (
      <button
        type="button"
        onClick={() => setPlaying(true)}
        aria-label={`Play video: ${title}`}
        className="group relative block aspect-video w-full overflow-hidden rounded-lg bg-black/80"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`https://i.ytimg.com/vi/${yt}/hqdefault.jpg`}
          alt=""
          aria-hidden="true"
          loading="lazy"
          className="h-full w-full object-cover"
        />
        <span className="absolute inset-0 flex items-center justify-center bg-black/25 transition-colors group-hover:bg-black/35">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 shadow-lg transition-transform group-hover:scale-110">
            <PlayIcon />
          </span>
        </span>
      </button>
    )
  }

  return <video controls src={url} aria-label={title} className="w-full rounded-lg" />
}
