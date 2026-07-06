// Provider-agnostic video embed. The `url` field carries the canonical source URL
// (never a bare provider-specific id) — detect a known provider from it and embed
// accordingly, falling back to a plain HTML5 <video> for anything else (self-hosted
// clips, other providers). Swapping in a second provider is a single added branch.

function youtubeId(url: string): string | null {
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{11})/)
  return m ? m[1] : null
}

interface Props {
  url: string
  title: string
}

export function VideoEmbed({ url, title }: Props) {
  const yt = youtubeId(url)

  if (yt) {
    return (
      <iframe
        title={title}
        src={`https://www.youtube-nocookie.com/embed/${yt}`}
        className="aspect-video w-full rounded-lg border-0"
        allow="encrypted-media"
        referrerPolicy="strict-origin-when-cross-origin"
        loading="lazy"
      />
    )
  }

  // Self-hosted / other providers: no known embed transform, play the URL directly.
  return <video controls src={url} aria-label={title} className="w-full rounded-lg" />
}
