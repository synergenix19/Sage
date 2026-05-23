import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act, waitFor, render, screen } from '@testing-library/react'
import { useStreamingChat, ChatInterface } from '../chat-interface'

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: (selector: (s: { locale: string }) => unknown) =>
    selector({ locale: 'en' }),
}))
vi.mock('@/components/pwa/install-prompt', () => ({
  FIRST_CHAT_EVENT: '__test_first_chat__',
}))
vi.mock('../chat-header', () => ({ ChatHeader: () => null }))
vi.mock('../empty-state', () => ({ EmptyState: () => null }))
vi.mock('../input-bar', () => ({ InputBar: () => null }))
vi.mock('../crisis-card', () => ({ CrisisCard: () => null }))
vi.mock('../typing-indicator', () => ({ TypingIndicator: () => null }))
vi.mock('../message-bubble', () => ({
  MessageBubble: ({ message }: { message: { content: string } }) => (
    <div>{message.content}</div>
  ),
}))

// crypto.randomUUID is available in jsdom >= 19 / Node 18+.
// Guard so the suite fails loudly if the environment is missing it.
if (typeof crypto === 'undefined' || typeof crypto.randomUUID !== 'function') {
  throw new Error('crypto.randomUUID is not available in this test environment')
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a fetch mock whose body reader rejects after emitting `chunks`.
 *
 * jsdom's ReadableStream does not propagate controller.error() to reader.read()
 * reliably. We bypass that layer entirely by mocking the reader directly so
 * the nth read() call rejects — simulating a mid-stream network failure in a
 * way that reliably enters the catch block of useStreamingChat.
 */
function makeFaultingFetchMock(chunks: string[], error: Error): Promise<Response> {
  const enc = new TextEncoder()
  let callCount = 0
  const mockRead = vi.fn().mockImplementation(() => {
    if (callCount < chunks.length) {
      return Promise.resolve({ done: false, value: enc.encode(chunks[callCount++]) })
    }
    return Promise.reject(error)
  })
  return Promise.resolve({
    ok: true,
    headers: new Headers(),
    body: { getReader: () => ({ read: mockRead }) },
  } as unknown as Response)
}

afterEach(() => {
  vi.restoreAllMocks()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useStreamingChat — mid-stream failure', () => {
  it('discards partial assistant message when stream errors mid-way', async () => {
    const networkError = new Error('Network failure mid-stream')

    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      makeFaultingFetchMock(['Hello'], networkError)
    )

    const { result } = renderHook(() => useStreamingChat('session-1', undefined, []))

    // Trigger a stream by appending a user message.
    act(() => {
      result.current.append({ role: 'user', content: 'Hi' })
    })

    // Wait for both isLoading:false AND error:non-null together.
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).not.toBeNull()
    }, { timeout: 3000 })

    // --- core assertion: zero assistant messages remain ---
    const assistantMessages = result.current.messages.filter((m) => m.role === 'assistant')
    expect(assistantMessages).toHaveLength(0)
    expect(result.current.error?.message).toMatch(/Network failure mid-stream/)
  })

  it('keeps the user message after stream error', async () => {
    const networkError = new Error('Network failure mid-stream')

    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      makeFaultingFetchMock(['Partial'], networkError)
    )

    const { result } = renderHook(() => useStreamingChat('session-2', undefined, []))

    act(() => {
      result.current.append({ role: 'user', content: 'Hello there' })
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).not.toBeNull()
    }, { timeout: 3000 })

    const userMessages = result.current.messages.filter((m) => m.role === 'user')
    expect(userMessages).toHaveLength(1)
    expect(userMessages[0].content).toBe('Hello there')
  })
})

describe('ChatInterface — ARIA live region', () => {
  it('renders the message container with role="log" and aria-live="polite"', () => {
    // jsdom does not implement scrollIntoView — stub it so the useEffect doesn't throw.
    window.HTMLElement.prototype.scrollIntoView = vi.fn()

    render(
      <ChatInterface
        initialSession={null}
        initialMessages={[]}
        userName="Test"
        userId="user-1"
      />
    )
    const log = screen.getByRole('log')
    expect(log).toBeInTheDocument()
    expect(log).toHaveAttribute('aria-live', 'polite')
  })
})
