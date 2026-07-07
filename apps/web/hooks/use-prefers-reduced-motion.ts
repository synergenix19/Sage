import { useEffect, useState } from 'react'

// Shared across any component that needs to honor OS-level reduced-motion (spec §3.5):
// PresenceIndicator's breathing dot and MessageBubble's typewriter reveal both read this.
// Extracted from presence-indicator.tsx so both consumers share one source of truth
// instead of the typewriter path silently ignoring the setting via a JS setInterval that
// CSS media queries cannot stop.
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(mq.matches)
    const on = () => setReduced(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return reduced
}
