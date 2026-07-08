'use client'
import { useEffect, useRef, useState } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { PRESENCE_POOL, PRESENCE_SLOW, PRESENCE_DEGRADED, nextPresencePhraseIndex } from '@/lib/presence-phrases'
import { PRESENCE_PHRASE_MS, PRESENCE_SLOW_MS, PRESENCE_DEGRADED_MS } from '@/lib/presence-constants'
import { usePrefersReducedMotion } from '@/hooks/use-prefers-reduced-motion'

type Phase = 'dot' | 'phrase' | 'slow' | 'degraded'

export function PresenceIndicator({ onPhrase }: { onPhrase?: (id: number) => void }) {
  const locale = useLocaleStore((s) => s.locale)
  const reduced = usePrefersReducedMotion()
  const [phase, setPhase] = useState<Phase>('dot')
  const [phraseIdx, setPhraseIdx] = useState<number>(-1)
  const onPhraseRef = useRef(onPhrase)
  onPhraseRef.current = onPhrase

  useEffect(() => {
    const t1 = setTimeout(() => {
      // Draw from the module singleton so the phrase never repeats the PREVIOUS turn's
      // phrase, even though this component unmounted between turns (spec §2.2, Bug 1).
      const idx = nextPresencePhraseIndex()
      setPhraseIdx(idx)
      onPhraseRef.current?.(idx) // client-only analytics; never persisted (spec §5)
      setPhase('phrase')
    }, PRESENCE_PHRASE_MS)
    const t2 = setTimeout(() => setPhase('slow'), PRESENCE_SLOW_MS)
    const t3 = setTimeout(() => setPhase('degraded'), PRESENCE_DEGRADED_MS)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [])

  const label =
    phase === 'dot' ? '' :
    phase === 'slow' ? PRESENCE_SLOW[locale] :
    phase === 'degraded' ? PRESENCE_DEGRADED[locale] :
    PRESENCE_POOL[locale][phraseIdx] ?? ''

  return (
    <div
      role="status"
      aria-label={locale === 'ar' ? 'Sage معك' : 'Sage is with you'}
      className="flex items-center justify-start gap-2"
      data-testid="presence-indicator"
    >
      <span
        className={
          'h-2.5 w-2.5 rounded-full bg-[var(--color-text-secondary)] ' +
          (reduced ? 'opacity-70' : 'motion-safe:animate-[breathe_4s_ease-in-out_infinite]')
        }
      />
      {label && (
        <span className="text-sm text-[var(--color-text-secondary)] transition-opacity duration-500">
          {label}
        </span>
      )}
    </div>
  )
}
