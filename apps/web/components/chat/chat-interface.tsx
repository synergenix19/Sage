'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { mapSdkRole, type ChatSession, type MessageRole } from '@cdai/types'
import { FIRST_CHAT_EVENT } from '@/components/pwa/install-prompt'
import { useStreamingChat, isCrisisMessage, type SdkMessage } from '@/lib/hooks/use-streaming-chat'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { seedPresenceBag } from '@/lib/presence-phrases'
import { ChatHeader } from './chat-header'
import { MessageBubble } from './message-bubble'
import { CrisisCard } from './crisis-card'
import { PresenceIndicator } from './presence-indicator'
import { EmptyState } from './empty-state'
import { InputBar } from './input-bar'

// Tiny linear-congruential rng — deterministic, dependency-free. Its ONLY use is seeding the
// E2E presence-phrase bag below (Task 9 / spec §2.4 waiting-state indistinguishability test)
// so a normal turn and a crisis-bound turn draw the identical phrase and can be byte-diffed.
// Not cryptographic; not used anywhere in the production render path.
// Exported for testability only — not part of the public component API.
export function makeLcg(seed: number): () => number {
  let state = seed >>> 0
  return () => {
    state = (state * 1103515245 + 12345) & 0x7fffffff
    return state / 0x7fffffff
  }
}

interface Props {
  initialSession: ChatSession | null
  initialMessages?: SdkMessage[]
  userName: string
  userId: string // sent in body for future analytics; route authenticates via supabase.auth.getUser(), not this value
}

export function ChatInterface({ initialSession, initialMessages = [], userName, userId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const hasSignaledInstall = useRef(false)
  const { messages, append, isLoading, error, reload, pinnedCrisis } = useStreamingChat(initialSession?.id, userId, initialMessages)
  const locale = useLocaleStore((s) => s.locale)

  // Typewriter reveal (spec §3): the id of the assistant message currently mid-reveal.
  // Set ONLY on a genuine isLoading true->false EDGE (never on initial mount with loaded
  // history — that path starts with isLoading already false and must not animate the last
  // historical message on every page load, Bug 2).
  const [revealId, setRevealId] = useState<string | null>(null)
  // Detect the isLoading true->false EDGE DURING RENDER (React's documented "adjust state when
  // a prop changes" pattern) rather than in an effect. Setting reveal during render applies it
  // in the SAME commit as the full-content message, so the full answer never paints before the
  // reveal flips on (no "flash & re-type"), and it avoids the setState-in-effect lint. Bug 2
  // (no reveal on history mount) holds: prevLoading initializes to isLoading, so mounting with
  // loaded history (isLoading already false) never produces a true->false edge.
  const [prevLoading, setPrevLoading] = useState(isLoading)
  if (prevLoading !== isLoading) {
    setPrevLoading(isLoading)
    if (prevLoading && !isLoading) {
      const last = messages[messages.length - 1]
      if (last?.role === 'assistant' && last.content) setRevealId(last.id)
    }
  }

  // Stable callbacks — both are re-render triggers for the reveal effects downstream
  // (useTypewriter completion effect, PresenceIndicator's phrase timer) so they must not
  // be recreated on every render.
  const finishReveal = useCallback(() => setRevealId(null), [])
  const handlePresencePhrase = useCallback((_id: number) => {
    // client-only UX analytics; never persisted/audited (spec §5)
  }, [])

  // E2E-ONLY (Task 9 / spec §2.4/§7): reseed the module-singleton presence-phrase bag with a
  // deterministic rng so a normal turn and a crisis-bound turn draw the SAME phrase, letting
  // playwright/waiting-state-indistinguishability.spec.ts byte-diff the full captured frame
  // instead of masking the phrase region. Gated on NEXT_PUBLIC_E2E (unset in prod) — this
  // branch is DEAD CODE in production; prod phrase selection stays genuinely Math.random.
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_E2E === 'true') {
      seedPresenceBag(makeLcg(1))
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: isLoading ? 'instant' : 'smooth' })
  }, [messages, isLoading])

  // Signal install prompt after first completed assistant response
  useEffect(() => {
    if (hasSignaledInstall.current || isLoading || error) return
    if (messages.some((m) => m.role === 'assistant' && m.content.length > 0)) {
      hasSignaledInstall.current = true
      localStorage.setItem(FIRST_CHAT_EVENT, '1')
      window.dispatchEvent(new Event(FIRST_CHAT_EVENT))
    }
  }, [isLoading, error, messages])

  function handleSend(text: string) {
    append({ role: 'user', content: text })
  }

  async function handleFeedback(messageId: string, value: 1 | -1) {
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messageId, value }),
      })
    } catch {
      // feedback is best-effort — do not surface errors to the user
    }
  }

  return (
    <div className="flex h-full flex-col">
      <ChatHeader session={initialSession} />

      <div
        role="log"
        aria-live="polite"
        aria-label={locale === 'ar' ? 'المحادثة' : 'Conversation'}
        className="flex-1 overflow-y-auto px-4 py-4"
      >
        {/* Centered reading column: keeps assistant prose and the user bubble within one
            balanced column instead of pinning them to opposite viewport edges on wide screens. */}
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
        {messages.length === 0 && !isLoading ? (
          <EmptyState userName={userName} onChipClick={handleSend} />
        ) : (
          messages.map((m) => {
            const isCrisis = isCrisisMessage(m)
            if (isCrisis) return null
            const content = m.content
            const role: MessageRole = mapSdkRole(m.role)
            return (
              <MessageBubble
                key={m.id}
                message={{
                  id: m.id,
                  role,
                  content,
                  intent: null,
                  sessionId: initialSession?.id ?? '',
                  createdAt: '',
                  direction: m.direction,
                  sources: m.sources,
                }}
                supabaseId={m.supabaseId}
                onFeedback={handleFeedback}
                reveal={m.role === 'assistant' && m.id === revealId}
                onRevealComplete={finishReveal}
              />
            )
          })
        )}
        {isLoading &&
          messages[messages.length - 1]?.content === '' && (
            <PresenceIndicator onPhrase={handlePresencePhrase} />
          )}
        {error && (
          <div className="text-center text-xs text-[var(--color-text-secondary)]">
            {(error as Error & { httpStatus?: number }).httpStatus === 503
              ? 'Service is starting up — '
              : 'Something went wrong — '}
            <button onClick={() => reload()} className="underline">
              tap to retry
            </button>
          </div>
        )}
        <div ref={bottomRef} />
        </div>
      </div>

      {pinnedCrisis !== null && (
        <div className="py-2">
          <CrisisCard content={pinnedCrisis} />
        </div>
      )}

      <InputBar onSend={handleSend} disabled={isLoading} onInteract={finishReveal} />
    </div>
  )
}
