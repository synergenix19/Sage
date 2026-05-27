'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { mapSdkRole, type ChatSession, type MessageRole } from '@cdai/types'
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
export function useStreamingChat(sessionId: string | undefined, userId: string | undefined, initialMessages: SdkMessage[] = []) {
  const [messages, setMessages]   = useState<SdkMessage[]>(initialMessages)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError]         = useState<Error | null>(null)
  const abortRef                  = useRef<AbortController | null>(null)

  const stream = useCallback(
    async (history: SdkMessage[]) => {
      setError(null)
      setIsLoading(true)

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

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let accumulated = ''
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          accumulated += decoder.decode(value, { stream: true })
          const isCrisisMsg = accumulated.startsWith(CRISIS_SIGNAL)
          const displayContent = isCrisisMsg
            ? accumulated.slice(CRISIS_SIGNAL.length).trimStart()
            : accumulated
          setMessages((curr) =>
            curr.map((m) =>
              m.id === assistantId ? { ...m, content: displayContent, isCrisis: isCrisisMsg } : m
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
        if ((err as Error).name === 'AbortError') return
        setError(err as Error)
        // Discard the assistant message entirely on any failure — partial content
        // must never be shown. v7 output_gate: un-gated partial content must not display.
        setMessages((curr) => curr.filter((m) => m.id !== assistantId))
      } finally {
        setIsLoading(false)
        abortRef.current = null
      }
    },
    [sessionId, userId]
  )

  const append = useCallback(
    (msg: { role: 'user'; content: string }) => {
      const userMessage: SdkMessage = {
        id: crypto.randomUUID(),
        role: msg.role,
        content: msg.content,
      }
      // Compute next history synchronously so we can stream from it.
      let nextHistory: SdkMessage[] = []
      setMessages((curr) => {
        nextHistory = [...curr, userMessage]
        return nextHistory
      })
      // Defer to next tick so React flushes the optimistic user message first.
      queueMicrotask(() => void stream(nextHistory))
    },
    [stream]
  )

  const reload = useCallback(() => {
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
    void stream(history)
  }, [messages, stream])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  return { messages, append, isLoading, error, reload }
}

export function ChatInterface({ initialSession, initialMessages = [], userName, userId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const hasSignaledInstall = useRef(false)
  const { messages, append, isLoading, error, reload } = useStreamingChat(initialSession?.id, userId, initialMessages)
  const locale = useLocaleStore((s) => s.locale)
  // Pin the crisis card for the entire crisis/post-crisis monitoring sequence.
  // Content is already CRISIS_SIGNAL-stripped on the message during streaming.
  const pinnedCrisis = messages.find((m) => m.isCrisis)?.content ?? null

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
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
      >
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

      {pinnedCrisis !== null && (
        <div className="py-2">
          <CrisisCard content={pinnedCrisis} />
        </div>
      )}

      <InputBar onSend={handleSend} disabled={isLoading} />
    </div>
  )
}
