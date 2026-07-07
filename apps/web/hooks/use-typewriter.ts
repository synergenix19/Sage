import { useEffect, useMemo, useRef, useState } from 'react'
import { chunkForReveal } from '@/lib/bidi-chunk'
import { TYPEWRITER_WPS, TYPEWRITER_MAX_MS } from '@/lib/presence-constants'

const TICK_MS = 1000 / 60 // ~16ms; interval-driven so fake timers control it deterministically

export function useTypewriter(text: string, opts: { enabled: boolean }): {
  displayed: string; done: boolean; complete: () => void
} {
  const chunks = useMemo(() => chunkForReveal(text), [text])
  const [count, setCount] = useState(() => (opts.enabled ? 0 : chunks.length))
  const elapsedRef = useRef(0)

  // Duration scales with length but is capped — long responses accelerate (spec §3.2).
  const durationMs = useMemo(() => {
    const words = text.trim() ? text.trim().split(/\s+/).length : 0
    return Math.min(TYPEWRITER_MAX_MS, (words / TYPEWRITER_WPS) * 1000)
  }, [text])

  useEffect(() => {
    if (!opts.enabled) { setCount(chunks.length); return }
    setCount(0)
    elapsedRef.current = 0
    if (chunks.length === 0 || durationMs <= 0) { setCount(chunks.length); return }
    const id = setInterval(() => {
      elapsedRef.current += TICK_MS
      const p = Math.min(1, elapsedRef.current / durationMs)
      const eased = Math.pow(p, 1.4) // accelerate: reveal rate increases over time
      const revealed = Math.min(chunks.length, Math.ceil(eased * chunks.length))
      setCount(revealed)
      if (p >= 1) clearInterval(id)
    }, TICK_MS)
    return () => clearInterval(id)
  }, [chunks, durationMs, opts.enabled])

  const complete = () => setCount(chunks.length)
  const displayed = count >= chunks.length ? text : chunks.slice(0, count).join('')
  return { displayed, done: count >= chunks.length, complete }
}
