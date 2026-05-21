/**
 * Tests for useStreamingChat — mid-stream failure behaviour.
 *
 * Requirement (v7 output_gate): when fetch returns a stream that errors after
 * emitting partial content, the assistant message must be fully discarded.
 * Zero assistant messages must remain in state; an error must be set.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useStreamingChat } from '../chat-interface'

// crypto.randomUUID is available in jsdom >= 19 / Node 18+.
// Guard so the suite fails loudly if the environment is missing it.
if (typeof crypto === 'undefined' || typeof crypto.randomUUID !== 'function') {
  throw new Error('crypto.randomUUID is not available in this test environment')
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a ReadableStream that:
 *   1. Emits `chunks` as Uint8Array values (simulating partial content).
 *   2. Then rejects with `error` — simulating a mid-stream network failure.
 */
function makeFaultingStream(chunks: string[], error: Error): ReadableStream<Uint8Array> {
  const enc = new TextEncoder()
  let idx = 0
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (idx < chunks.length) {
        controller.enqueue(enc.encode(chunks[idx++]))
      } else {
        // Simulate network failure after chunks have been emitted.
        controller.error(error)
      }
    },
  })
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

    // Mock fetch to return a 200 response whose body errors after "Hello".
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(makeFaultingStream(['Hello'], networkError), { status: 200 })
    )

    const { result } = renderHook(() => useStreamingChat('session-1', []))

    // Trigger a stream by appending a user message.
    act(() => {
      result.current.append({ role: 'user', content: 'Hi' })
    })

    // Wait until loading stops (stream errored out and finally block ran).
    await waitFor(() => expect(result.current.isLoading).toBe(false), { timeout: 3000 })

    // --- core assertion: zero assistant messages remain ---
    const assistantMessages = result.current.messages.filter((m) => m.role === 'assistant')
    expect(assistantMessages).toHaveLength(0)

    // The error should be set so the UI can show a retry prompt.
    expect(result.current.error).not.toBeNull()
    expect(result.current.error?.message).toMatch(/Network failure mid-stream/)
  })

  it('keeps the user message after stream error', async () => {
    const networkError = new Error('Network failure mid-stream')

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(makeFaultingStream(['Partial'], networkError), { status: 200 })
    )

    const { result } = renderHook(() => useStreamingChat('session-2', []))

    act(() => {
      result.current.append({ role: 'user', content: 'Hello there' })
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false), { timeout: 3000 })

    // The original user message must survive — only the assistant placeholder is removed.
    const userMessages = result.current.messages.filter((m) => m.role === 'user')
    expect(userMessages).toHaveLength(1)
    expect(userMessages[0].content).toBe('Hello there')
  })
})
