import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { renderHook, act, waitFor, render, screen, fireEvent } from '@testing-library/react'
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
// Enhanced (Task 7) beyond a bare stub: exposes a send button and a focus/keydown-able
// field so integration tests can drive `append()` and `onInteract` through the component
// tree — mirrors what the file's other tests do for useStreamingChat, but at the
// ChatInterface level where there previously was no send affordance to hook into.
vi.mock('../input-bar', () => ({
  InputBar: ({
    onSend,
    onInteract,
  }: {
    onSend: (text: string) => void
    disabled?: boolean
    onInteract?: () => void
  }) => (
    <div>
      <button data-testid="mock-send" onClick={() => onSend('hello')}>
        send
      </button>
      <input data-testid="mock-field" onFocus={onInteract} onKeyDown={onInteract} />
    </div>
  ),
}))
vi.mock('../crisis-card', () => ({ CrisisCard: () => null }))
vi.mock('../typing-indicator', () => ({ TypingIndicator: () => null }))
// Enhanced (Task 7): surfaces `reveal` via a data attribute so tests can assert on the
// prop ChatInterface computed, while still rendering full `message.content` synchronously
// like the original stub (no timers) — existing assertions that only check text are unaffected.
vi.mock('../message-bubble', () => ({
  MessageBubble: ({ message, reveal }: { message: { id: string; content: string }; reveal?: boolean }) => (
    <div data-testid={`msg-${message.id}`} data-reveal={reveal ? 'true' : 'false'}>
      {message.content}
    </div>
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

describe('useStreamingChat — first-byte timeout', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sets error and clears placeholder when server sends no bytes within the first-byte timeout', async () => {
    // Minimal ReadableStream that never yields — simulates hung server.
    const neverStream = new ReadableStream<Uint8Array>({ start() {} })
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: neverStream,
      headers: new Headers(),
    } as unknown as Response)

    const { result } = renderHook(() =>
      useStreamingChat('sess-timeout-1', 'user-1', [])
    )

    act(() => {
      result.current.append({ role: 'user', content: 'hello' })
    })

    // Before timeout: still loading, empty placeholder present.
    expect(result.current.isLoading).toBe(true)

    // Advance past the first-byte timeout (58s — aligned just above the backend's 55s ceiling).
    await act(async () => {
      vi.advanceTimersByTime(58_001)
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.error?.message).toMatch(/taking too long/i)
    // Empty placeholder must be removed — not left in the message list.
    expect(result.current.messages.every((m) => m.role !== 'assistant' || m.content !== '')).toBe(true)
  })

  it('does NOT trigger timeout when server responds before 25s', async () => {
    const singleChunkStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('Hello there'))
        controller.close()
      },
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: singleChunkStream,
      headers: new Headers(),
    } as unknown as Response)

    const { result } = renderHook(() =>
      useStreamingChat('sess-timeout-2', 'user-1', [])
    )

    await act(async () => {
      result.current.append({ role: 'user', content: 'hi' })
      vi.advanceTimersByTime(1_000)
    })

    // Drain all pending microtasks and timers so the stream completes.
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    // waitFor uses real-time polling; restore real timers first so it can settle.
    vi.useRealTimers()
    await waitFor(() => {
      expect(result.current.error).toBeNull()
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('reload() is a no-op while a stream is already in flight (no stacked server runs)', async () => {
    // Never-yielding body: the request stays in flight so reload() must not start another.
    const neverStream = new ReadableStream<Uint8Array>({ start() {} })
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      body: neverStream,
      headers: new Headers(),
    } as unknown as Response)

    const { result } = renderHook(() =>
      useStreamingChat('sess-guard-1', 'user-1', [])
    )

    await act(async () => {
      result.current.append({ role: 'user', content: 'hello' })
    })

    // Exactly one in-flight request.
    expect(result.current.isLoading).toBe(true)
    expect(fetchSpy).toHaveBeenCalledTimes(1)

    // Re-tapping retry while the first run is still in flight must NOT issue a second fetch.
    await act(async () => {
      result.current.reload()
    })
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  // Task 8 / spec §2.3 / review Change 3: a retry must never run two concurrent server-side
  // turns for one utterance — a second concurrent turn would also write a second
  // session_audit row for what the user experiences as a single message. This variant stubs
  // fetch itself as never-resolving (rather than a resolved response with a hung body, as
  // above) so the guard is pinned at the point reload() is invoked before fetch's promise
  // has settled at all — the other resend-supersede shape covered by the "no-op" test.
  it('retry supersedes an in-flight request — never two concurrent turns per utterance', async () => {
    const fetchMock = vi.fn(() => new Promise(() => {})) // stays in flight, never resolves
    vi.spyOn(globalThis, 'fetch').mockImplementation(fetchMock as unknown as typeof fetch)

    const { result } = renderHook(() => useStreamingChat('sess-supersede-1', 'user-1', []))

    act(() => {
      result.current.append({ role: 'user', content: 'hi' })
    })
    await act(async () => {
      await Promise.resolve()
    })

    const callsAfterFirst = fetchMock.mock.calls.length
    expect(callsAfterFirst).toBe(1)

    act(() => {
      result.current.reload() // re-tap while still in flight
    })

    expect(fetchMock.mock.calls.length).toBe(callsAfterFirst) // reload() no-ops while inFlight
  })
})

// Task 6: the client reads X-Sage-Sources off res.headers directly (mirroring how it
// already reads X-Sage-Crisis-State / X-Sage-Direction) and attaches the parsed array to
// the assistant message so message-bubble.tsx can render <SourceCard>. The header is a
// raw, unvalidated JSON string from the backend — a malformed value must never crash the
// render; it must silently fall back to "no sources".
describe('useStreamingChat — X-Sage-Sources header', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function singleChunkStreamWithHeaders(headers: Record<string, string>) {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('hello'))
        controller.close()
      },
    })
    return { ok: true, status: 200, body, headers: new Headers(headers) } as unknown as Response
  }

  it('attaches parsed sources from a well-formed X-Sage-Sources header', async () => {
    const sources = [{ type: 'article', title: 'Understanding Anxiety', url: 'https://kb/a', citation: 'c' }]
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      singleChunkStreamWithHeaders({ 'X-Sage-Sources': JSON.stringify(sources) })
    )

    const { result } = renderHook(() => useStreamingChat('sess-sources-1', 'user-1', []))

    await act(async () => {
      result.current.append({ role: 'user', content: 'tell me about anxiety' })
    })
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    vi.useRealTimers()
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    const assistant = result.current.messages.find((m) => m.role === 'assistant')
    expect(assistant?.sources).toEqual(sources)
  })

  it('does not crash and attaches no sources when X-Sage-Sources is malformed JSON', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      singleChunkStreamWithHeaders({ 'X-Sage-Sources': '{not valid json' })
    )

    const { result } = renderHook(() => useStreamingChat('sess-sources-2', 'user-1', []))

    await act(async () => {
      result.current.append({ role: 'user', content: 'hi' })
    })
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    vi.useRealTimers()
    await waitFor(() => {
      expect(result.current.error).toBeNull()
      expect(result.current.isLoading).toBe(false)
    })
    const assistant = result.current.messages.find((m) => m.role === 'assistant')
    expect(assistant?.content).toBe('hello')
    expect(assistant?.sources).toBeUndefined()
  })

  it('attaches no sources when the header is absent', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(singleChunkStreamWithHeaders({}))

    const { result } = renderHook(() => useStreamingChat('sess-sources-3', 'user-1', []))

    await act(async () => {
      result.current.append({ role: 'user', content: 'hi' })
    })
    await act(async () => {
      await vi.runAllTimersAsync()
    })

    vi.useRealTimers()
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    const assistant = result.current.messages.find((m) => m.role === 'assistant')
    expect(assistant?.sources).toBeUndefined()
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
    expect(log).toHaveAttribute('aria-label', 'Conversation')
  })
})

// Task 7: PresenceIndicator replaces TypingIndicator at the waiting-state render site, and
// the just-completed assistant message reveals via a `revealId` edge (never on mount with
// pre-loaded history — Bug 2).
describe('ChatInterface — presence indicator + typewriter reveal (Task 7)', () => {
  beforeEach(() => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  it('renders PresenceIndicator (not the old dots) while awaiting first byte', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))

    render(
      <ChatInterface initialSession={null} initialMessages={[]} userName="Test" userId="user-1" />
    )

    fireEvent.click(screen.getByTestId('mock-send'))

    expect(await screen.findByTestId('presence-indicator')).toBeInTheDocument()
    expect(() => screen.getByTestId('typing-indicator')).toThrow()
  })

  it('does NOT typewriter-reveal historical messages on page load (Bug 2 — edge-only reveal)', () => {
    const history = [
      { id: 'u1', role: 'user' as const, content: 'hi' },
      { id: 'a1', role: 'assistant' as const, content: 'a full historical reply that must not animate' },
    ]

    render(
      <ChatInterface
        initialSession={null}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        initialMessages={history as any}
        userName="X"
        userId="u"
      />
    )

    // Full text present synchronously (no fake-timer advance) => not revealed progressively.
    expect(screen.getByText('a full historical reply that must not animate')).toBeInTheDocument()
    // The mocked MessageBubble surfaces the `reveal` prop ChatInterface computed — it must
    // be false because isLoading was never true->false on this render (no edge occurred).
    expect(screen.getByTestId('msg-a1')).toHaveAttribute('data-reveal', 'false')
  })

  // Task 8 (closes the Task 7 review Minor): end-to-end skip-on-type. Drives a full turn to
  // completion so the last assistant message is genuinely revealing (data-reveal="true"),
  // then fires a keydown on the InputBar's field (mock exposes it as onKeyDown={onInteract})
  // and asserts the reveal is finalized (data-reveal flips to "false") — proving the wiring
  // from InputBar's onInteract through to ChatInterface's finishReveal actually fires in a
  // real render tree, not just as an isolated unit assertion.
  it('firing keydown on the input field finalizes an in-progress reveal (skip-on-type)', async () => {
    const singleChunkStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('a reply'))
        controller.close()
      },
    })
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: singleChunkStream,
      headers: new Headers(),
    } as unknown as Response)

    const { container } = render(
      <ChatInterface initialSession={null} initialMessages={[]} userName="Test" userId="user-1" />
    )

    fireEvent.click(screen.getByTestId('mock-send'))

    // Turn completes (isLoading true->false edge) => the assistant message starts revealing.
    // Two message divs render (user + assistant); the assistant one is the last — the user
    // message's `reveal` is always false, so it must not be the node under assertion.
    const lastMsgEl = () => {
      const all = container.querySelectorAll('[data-testid^="msg-"]')
      return all[all.length - 1]
    }
    await waitFor(() => {
      expect(lastMsgEl()).toBeDefined()
      expect(lastMsgEl()).toHaveAttribute('data-reveal', 'true')
    })

    fireEvent.keyDown(screen.getByTestId('mock-field'), { key: 'a' })

    await waitFor(() => {
      expect(lastMsgEl()).toHaveAttribute('data-reveal', 'false')
    })
  })
})
