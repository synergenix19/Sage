'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { mapSdkRole, type ChatSession, type MessageRole } from '@cdai/types'
import { FIRST_CHAT_EVENT } from '@/components/pwa/install-prompt'
import { ChatHeader } from './chat-header'
import { MessageBubble } from './message-bubble'
import { CrisisCard } from './crisis-card'
import { TypingIndicator } from './typing-indicator'
import { EmptyState } from './empty-state'
import { InputBar } from './input-bar'

const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'

// SDK-shaped messages: roles are 'user' | 'assistant' | 'system' (what the route consumes
// and what the AI SDK normally yields). Internal roles ('ai', 'crisis') are derived for render.
type SdkRole = 'user' | 'assistant' | 'system'
interface SdkMessage {
  id: string
  role: SdkRole
  content: string
}

interface Props {
  initialSession: ChatSession | null
  initialMessages?: SdkMessage[]
  userName: string
  userId: string // passed by chat/page.tsx; available for future API auth or analytics
}

// Custom streaming chat hook. The /api/chat route returns a raw text stream via
// `toTextStreamResponse()` (AI SDK v6). In v6 the React `useChat` hook moved to
// `@ai-sdk/react` (not installed) and expects a UI-message stream from
// `toUIMessageStreamResponse()`. To avoid changing the route contract or adding
// a dep, we consume the raw text stream directly.
// Exported for testability only — not part of the public component API.
export function useStreamingChat(sessionId: string | undefined, initialMessages: SdkMessage[] = []) {
  const [messages, setMessages] = useState<SdkMessage[]>(initialMessages)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const abortRef = useRef<AbortController | null>(null)

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
            messages: history.map((m) => ({ role: m.role, content: m.content })),
          }),
          signal: controller.signal,
        })

        if (!res.ok || !res.body) {
          throw new Error(`Chat request failed: ${res.status}`)
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let accumulated = ''
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          accumulated += decoder.decode(value, { stream: true })
          const displayContent = accumulated
          setMessages((curr) =>
            curr.map((m) => (m.id === assistantId ? { ...m, content: displayContent } : m))
          )
        }
        accumulated += decoder.decode() // flush trailing multi-byte sequence

        if (accumulated.includes('[[SERVER_ERROR]]')) {
          // Drop the placeholder and surface the error — lets the retry UI appear
          setMessages((curr) => curr.filter((m) => m.id !== assistantId))
          setError(new Error('Sage is having trouble responding. Please try again.'))
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
    [sessionId]
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

export function ChatInterface({ initialSession, initialMessages = [], userName }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const hasSignaledInstall = useRef(false)
  const { messages, append, isLoading, error, reload } = useStreamingChat(initialSession?.id, initialMessages)

  // Pin the crisis card only while the last assistant message is still a crisis.
  // Once the user receives a normal reply the crisis is considered addressed
  // for this turn and the pin is cleared.
  const pinnedCrisis = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant') {
        if (messages[i].content.startsWith(CRISIS_SIGNAL)) {
          return messages[i].content.replace(CRISIS_SIGNAL, '').trimStart()
        }
        return null
      }
    }
    return null
  })()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
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

  return (
    <div className="flex h-full flex-col">
      <ChatHeader session={initialSession} />

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && !isLoading ? (
          <EmptyState userName={userName} onChipClick={handleSend} />
        ) : (
          messages.map((m) => {
            const isCrisis =
              m.role === 'assistant' && m.content.startsWith(CRISIS_SIGNAL)
            const content = isCrisis
              ? m.content.replace(CRISIS_SIGNAL, '').trimStart()
              : m.content
            if (isCrisis) return <CrisisCard key={m.id} content={content} />
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
              />
            )
          })
        )}
        {isLoading &&
          messages[messages.length - 1]?.content === '' && <TypingIndicator />}
        {error && (
          <div className="text-center text-xs text-[var(--color-crisis)]">
            Something went wrong —{' '}
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
