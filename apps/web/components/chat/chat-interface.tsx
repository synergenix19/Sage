'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { mapSdkRole, type ChatSession, type MessageRole, type Source } from '@cdai/types'
import { FIRST_CHAT_EVENT } from '@/components/pwa/install-prompt'
import { CRISIS_SIGNAL, SERVER_ERROR_SIGNAL } from '@/lib/constants'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { ChatHeader } from './chat-header'
import { MessageBubble } from './message-bubble'
import { CrisisCard } from './crisis-card'
import { TypingIndicator } from './typing-indicator'
import { EmptyState } from './empty-state'
import { InputBar } from './input-bar'

// SDK-shaped messages: roles are 'user' | 'assistant' | 'system' (what the route consumes
// and what the AI SDK normally yields). Internal roles ('ai', 'crisis') are derived for render.
type SdkRole = 'user' | 'assistant' | 'system'
interface SdkMessage {
  id: string
  role: SdkRole
  content: string
  supabaseId?: string  // Supabase UUID from X-Sage-Ai-Message-Id header
  isCrisis?: boolean
  direction?: 'ltr' | 'rtl'  // authoritative from X-Sage-Direction (detected_language)
  sources?: Source[]  // KB sources from X-Sage-Sources (Task 6); absent when the header is absent or malformed
}

interface Props {
  initialSession: ChatSession | null
  initialMessages?: SdkMessage[]
  userName: string
  userId: string // sent in body for future analytics; route authenticates via supabase.auth.getUser(), not this value
}

// Custom streaming chat hook. The /api/chat route returns a raw text stream via
// `toTextStreamResponse()` (AI SDK v6). In v6 the React `useChat` hook moved to
// `@ai-sdk/react` (not installed) and expects a UI-message stream from
// `toUIMessageStreamResponse()`. To avoid changing the route contract or adding
// a dep, we consume the raw text stream directly.
// Exported for testability only — not part of the public component API.
// Aligned just above the backend graph ceiling (AINVOKE_TIMEOUT_SECONDS=55) and below the
// Vercel route maxDuration (60s). A turn legitimately takes 15-50s and the backend buffers
// the whole graph before the first byte, so a 25s cutoff fired WHILE the backend was still
// working — surfacing a premature "tap to retry" that invited a retry and stacked a second
// server-side run. At 58s the backend's own result or [[SERVER_ERROR]] arrives first.
const FIRST_BYTE_TIMEOUT_MS = 58_000
export function useStreamingChat(sessionId: string | undefined, userId: string | undefined, initialMessages: SdkMessage[] = []) {
  const [messages, setMessages]     = useState<SdkMessage[]>(initialMessages)
  const [isLoading, setIsLoading]   = useState(false)
  const [error, setError]           = useState<Error | null>(null)
  const [crisisState, setCrisisState] = useState<string | null>(null)
  const abortRef                    = useRef<AbortController | null>(null)
  // Tracks whether the first-byte timeout fired. Used by stream() to distinguish
  // a timeout-triggered AbortError from a user-navigation AbortError.
  const timedOutRef                 = useRef(false)
  // Stores the active first-byte timeout ID so stream() can clear it on first byte.
  const firstByteTimerRef           = useRef<ReturnType<typeof setTimeout> | null>(null)
  // True while a stream is genuinely in flight. Guards reload() so a re-tap cannot stack a
  // second server-side graph run on the same thread (a client abort does NOT cancel the
  // backend ainvoke), which produced fast checkpoint-conflict errors on rapid retries.
  const inFlightRef                 = useRef(false)

  const stream = useCallback(
    async (history: SdkMessage[]) => {
      // If the first-byte timeout already fired (before stream() started via queueMicrotask),
      // the timeout callback already set the error state — bail out immediately.
      if (timedOutRef.current) return

      setError(null)
      setIsLoading(true)
      inFlightRef.current = true

      const controller = new AbortController()
      abortRef.current = controller

      const assistantId = crypto.randomUUID()
      setMessages([...history, { id: assistantId, role: 'assistant', content: '' }])

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId,
            userId: userId ?? null,
            messages: history.map((m) => ({ role: m.role, content: m.content })),
          }),
          signal: controller.signal,
        })

        if (!res.ok || !res.body) {
          const err = new Error(`Chat request failed: ${res.status}`)
          ;(err as Error & { httpStatus: number }).httpStatus = res.status
          throw err
        }

        const aiSupabaseId = res.headers.get('X-Sage-Ai-Message-Id') ?? undefined
        const newCrisisState = res.headers.get('X-Sage-Crisis-State')
        if (newCrisisState) setCrisisState(newCrisisState)
        // Authoritative text direction from the backend; functional, present on every turn.
        const aiDirectionRaw = res.headers.get('X-Sage-Direction')
        const aiDirection: 'ltr' | 'rtl' | undefined =
          aiDirectionRaw === 'rtl' || aiDirectionRaw === 'ltr' ? aiDirectionRaw : undefined

        // KB source cards (X-Sage-Sources) — a raw, unvalidated JSON string forwarded
        // verbatim from the backend by the route. A malformed header must never crash
        // the render, so a parse failure silently falls back to "no sources" rather
        // than surfacing an error to the user.
        const sourcesHeaderRaw = res.headers.get('X-Sage-Sources')
        let aiSources: Source[] | undefined
        if (sourcesHeaderRaw) {
          try {
            aiSources = JSON.parse(sourcesHeaderRaw)
          } catch {
            aiSources = undefined
          }
        }

        // Skill-delivered media (X-Sage-Skill-Media) — a SEPARATE header from X-Sage-Sources
        // (skill media is not a retrieved KB passage). Appended to the message's sources as a
        // video entry so it renders through the same SourceCard/VideoEmbed. Malformed → skipped,
        // never crashes the render (same discipline as X-Sage-Sources).
        const skillMediaRaw = res.headers.get('X-Sage-Skill-Media')
        if (skillMediaRaw) {
          try {
            const m = JSON.parse(skillMediaRaw)
            const entry: Source = { type: m.type, title: m.title ?? '', url: m.url, citation: m.provider ?? '' }
            aiSources = [...(aiSources ?? []), entry]
          } catch { /* malformed → ignore */ }
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let accumulated = ''
        let firstByteReceived = false
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          if (!firstByteReceived) {
            // Cancel the first-byte timeout — server is responsive.
            firstByteReceived = true
            if (firstByteTimerRef.current !== null) {
              clearTimeout(firstByteTimerRef.current)
              firstByteTimerRef.current = null
            }
          }
          accumulated += decoder.decode(value, { stream: true })
          const isCrisisMsg = accumulated.startsWith(CRISIS_SIGNAL)
          const displayContent = isCrisisMsg
            ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
            : accumulated
          setMessages((curr) =>
            curr.map((m) =>
              m.id === assistantId
                ? { ...m, content: displayContent, isCrisis: isCrisisMsg, direction: aiDirection, sources: aiSources }
                : m
            )
          )
        }
        accumulated += decoder.decode() // flush trailing multi-byte sequence

        if (accumulated.includes(SERVER_ERROR_SIGNAL)) {
          // Drop the placeholder and surface the error — lets the retry UI appear
          setMessages((curr) => curr.filter((m) => m.id !== assistantId))
          setError(new Error('Sage is having trouble responding. Please try again.'))
        } else {
          // Stream complete — attach the Supabase message UUID for the feedback flow.
          if (aiSupabaseId) {
            setMessages((curr) =>
              curr.map((m) => (m.id === assistantId ? { ...m, supabaseId: aiSupabaseId } : m))
            )
          }
        }
      } catch (err) {
        // AbortError from user navigation (component unmount): discard silently.
        // AbortError from first-byte timeout: already handled by the timeout callback.
        if ((err as Error).name === 'AbortError') return
        setError(err as Error)
        // Discard the assistant message entirely on any failure — partial content
        // must never be shown. v7 output_gate: un-gated partial content must not display.
        setMessages((curr) => curr.filter((m) => m.id !== assistantId))
      } finally {
        // The stream has settled (completed, errored, or was aborted by the timeout); the
        // request is no longer in flight, so reload() may start a fresh one.
        inFlightRef.current = false
        // Always clear the first-byte timer — prevents it firing 58s after a
        // pre-response network error and overwriting the real error message.
        if (firstByteTimerRef.current !== null) {
          clearTimeout(firstByteTimerRef.current)
          firstByteTimerRef.current = null
        }
        // Only reset loading/abort state if the timeout didn't already do so.
        if (!timedOutRef.current) {
          setIsLoading(false)
          abortRef.current = null
        }
      }
    },
    [sessionId, userId]
  )

  /**
   * Registers the first-byte timeout (FIRST_BYTE_TIMEOUT_MS) synchronously (before any await)
   * so vi.advanceTimersByTime() in tests can fire it before stream()'s async body runs.
   * The timeout callback sets error state directly, then aborts the in-flight request.
   * stream() cancels the timer on first byte via firstByteTimerRef.
   */
  function registerFirstByteTimeout() {
    // Abort any in-flight stream before registering a new timeout, so a second
    // append() call does not produce two concurrent streams writing to state.
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    if (firstByteTimerRef.current !== null) clearTimeout(firstByteTimerRef.current)
    timedOutRef.current = false
    firstByteTimerRef.current = setTimeout(() => {
      timedOutRef.current = true
      firstByteTimerRef.current = null
      setError(new Error('Sage is taking too long to respond. Please try again.'))
      // Remove any empty assistant placeholder left in the message list.
      setMessages((curr) => curr.filter((m) => m.role !== 'assistant' || m.content !== ''))
      setIsLoading(false)
      abortRef.current?.abort()
      abortRef.current = null
    }, FIRST_BYTE_TIMEOUT_MS)
  }

  const append = useCallback(
    (msg: { role: 'user'; content: string }) => {
      const userMessage: SdkMessage = {
        id: crypto.randomUUID(),
        role: msg.role,
        content: msg.content,
      }
      // Set loading eagerly so callers see isLoading:true synchronously within act().
      setIsLoading(true)
      setError(null)
      // Register the first-byte timeout synchronously before any async work,
      // so vi.advanceTimersByTime() in tests can fire it even before stream() runs.
      registerFirstByteTimeout()
      // Compute next history synchronously so we can stream from it.
      let nextHistory: SdkMessage[] = []
      setMessages((curr) => {
        nextHistory = [...curr, userMessage]
        return nextHistory
      })
      // Defer stream() to next tick so React flushes the optimistic user message first.
      queueMicrotask(() => void stream(nextHistory))
    },
    [stream]
  )

  const reload = useCallback(() => {
    // Don't stack a second server-side run on top of one still in flight. A client abort
    // doesn't cancel the backend ainvoke, so re-tapping during an active turn just piles
    // concurrent runs onto the same thread — the retry-storm amplifier.
    if (inFlightRef.current) return
    // Replay from the last user message onward.
    const lastUserIdx = (() => {
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === 'user') return i
      }
      return -1
    })()
    if (lastUserIdx === -1) return
    const history = messages.slice(0, lastUserIdx + 1)
    setMessages(history)
    registerFirstByteTimeout()
    void stream(history)
  }, [messages, stream])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      if (firstByteTimerRef.current !== null) clearTimeout(firstByteTimerRef.current)
    }
  }, [])

  return { messages, append, isLoading, error, reload, crisisState }
}

export function ChatInterface({ initialSession, initialMessages = [], userName, userId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const hasSignaledInstall = useRef(false)
  const { messages, append, isLoading, error, reload, crisisState } = useStreamingChat(initialSession?.id, userId, initialMessages)
  const locale = useLocaleStore((s) => s.locale)
  // Pin the crisis card while in monitoring; dismiss when backend signals resolved.
  // Content is already CRISIS_SIGNAL-stripped on the message during streaming.
  const pinnedCrisis =
    crisisState !== 'resolved'
      ? (messages.find((m) => m.isCrisis)?.content ?? null)
      : null

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
            const isCrisis = m.isCrisis === true
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
              />
            )
          })
        )}
        {isLoading &&
          messages[messages.length - 1]?.content === '' && <TypingIndicator />}
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

      <InputBar onSend={handleSend} disabled={isLoading} />
    </div>
  )
}
