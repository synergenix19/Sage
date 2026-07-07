import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTypewriter } from '@/hooks/use-typewriter'

describe('useTypewriter', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('reveals nothing-to-all over time and completes', () => {
    const text = 'one two three four five six seven eight'
    const { result } = renderHook(() => useTypewriter(text, { enabled: true }))
    expect(result.current.displayed.length).toBeLessThan(text.length)
    act(() => { vi.advanceTimersByTime(3_000) }) // past the 2.5s cap
    expect(result.current.displayed).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it('when disabled, shows full text immediately (crisis / reduced-motion / history)', () => {
    const text = 'helpline text renders instantly'
    const { result } = renderHook(() => useTypewriter(text, { enabled: false }))
    expect(result.current.displayed).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it('complete() reveals everything at once (skip affordance)', () => {
    const text = 'a fairly long sentence to reveal word by word here'
    const { result } = renderHook(() => useTypewriter(text, { enabled: true }))
    act(() => { vi.advanceTimersByTime(200) })
    act(() => { result.current.complete() })
    expect(result.current.displayed).toBe(text)
    expect(result.current.done).toBe(true)
  })

  it('displayed is always a real prefix of the chunk-joined text (no reorder/garble)', () => {
    const text = 'أحس بضغط كبير and my boss keeps calling'
    const { result } = renderHook(() => useTypewriter(text, { enabled: true }))
    act(() => { vi.advanceTimersByTime(500) })
    expect(text.startsWith(result.current.displayed)).toBe(true)
  })
})
