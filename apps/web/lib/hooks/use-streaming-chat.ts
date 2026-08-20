'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { Source } from '@cdai/types'
import { SERVER_ERROR_SIGNAL } from '@/lib/constants'
import { hasCrisisSignal, stripCrisisSignal } from '@/lib/crisis'
import { extractSageMetadata } from '@/lib/sage-headers'

// SDK-shaped messages: roles are 'user' | 'assistant' | 'system' (what the route consumes
// and what the AI SDK normally yields). Internal roles ('ai', 'crisis') are derived for render.
export type SdkRole = 'user' | 'assistant' | 'system'
export interface SdkMessage {
  id: string
  role: SdkRole
  content: string
  supabaseId?: string  // Supabase UUID from X-Sage-Ai-Message-Id header
  isCrisis?: boolean
  direction?: 'ltr' | 'rtl'  // authoritative from X-Sage-Direction (detected_language)
  sources?: Source[]  // KB sources from X-Sage-Sources (Task 6); absent when the header is absent or malformed
}

// Crisis detection at the RENDER BOUNDARY (invariant, issue #191). A message is crisis if its
// flag says so OR its content still carries the in-band `[[CRISIS_DETECTED]]` sentinel. This is
// belt-and-suspenders: even if `isCrisis` was mis-derived upstream (e.g. a history/reload path),
// the sentinel can NEVER render as plain text and crisis content NEVER renders as a normal
// bubble. Root cause is in-band signaling; the class-level fix is Phase 0b's out-of-band
// render_mode — this invariant remains as defense-in-depth after 0b lands.
export const isCrisisMessage = (m: SdkMessage): boolean =>
  m.isCrisis === true || hasCrisisSignal(m.content)

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

        // Single shared parse of every X-Sage-* metadata header (lib/sage-headers.ts) —
        // the persist path (app/api/chat/route.ts) parses the SAME headers through the
        // SAME function, so stored and rendered metadata can never diverge (Task 6a).
        const sageMetadata = extractSageMetadata(res.headers)
        if (sageMetadata.crisisState) setCrisisState(sageMetadata.crisisState)
        // Authoritative text direction from the backend; functional, present on every turn.
        const aiDirection = sageMetadata.direction
        // KB sources (already merged with skill-delivered media, if present) — a malformed
        // header falls back to "no sources" rather than surfacing an error to the user.
        const aiSources: Source[] | undefined = sageMetadata.sources ?? undefined

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
          const isCrisisMsg = hasCrisisSignal(accumulated)
          const displayContent = stripCrisisSignal(accumulated)
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
    const lastUserIdx = messages.findLastIndex((m) => m.role === 'user')
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

  // Pin the crisis card while in monitoring; dismiss when backend signals resolved.
  // Crisis content is normally sentinel-stripped during streaming, but strip again here so a
  // message that reached us with the sentinel still (history/reload path, #191) yields a clean
  // card. `findLast`: on repeated crisis disclosures, pin the LATEST card (matches the most recent
  // disclosure) — a crisis-UX behavior change on the sign-off packet (Task 4).
  const pinnedCrisisMsg = crisisState !== 'resolved' ? messages.findLast(isCrisisMessage) : undefined
  const pinnedCrisis = pinnedCrisisMsg ? stripCrisisSignal(pinnedCrisisMsg.content) : null

  return { messages, append, isLoading, error, reload, crisisState, pinnedCrisis }
}
