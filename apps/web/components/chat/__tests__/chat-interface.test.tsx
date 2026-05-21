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

    const { result } = renderHook(() => useStreamingChat('session-1', []))

    // Trigger a stream by appending a user message.
    act(() => {
      result.current.append({ role: 'user', content: 'Hi' })
    })

    // Wait for both isLoading:false AND error:non-null together.
    // Waiting on isLoading alone is racy: append() uses queueMicrotask, so
    // isLoading may still be false when waitFor first polls (stream not started
    // yet). The compound condition only passes after the stream has fully errored.
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

    const { result } = renderHook(() => useStreamingChat('session-2', []))

    act(() => {
      result.current.append({ role: 'user', content: 'Hello there' })
    })

    // Same compound wait: proves the stream ran and errored before checking survivors.
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).not.toBeNull()
    }, { timeout: 3000 })

    // The original user message must survive — only the assistant placeholder is removed.
    const userMessages = result.current.messages.filter((m) => m.role === 'user')
    expect(userMessages).toHaveLength(1)
    expect(userMessages[0].content).toBe('Hello there')
  })
})
