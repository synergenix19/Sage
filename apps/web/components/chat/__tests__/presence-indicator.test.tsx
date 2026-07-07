import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { PresenceIndicator } from '@/components/chat/presence-indicator'
import { PRESENCE_POOL, PRESENCE_SLOW, PRESENCE_DEGRADED, seedPresenceBag } from '@/lib/presence-phrases'

vi.mock('@/lib/stores/locale-store', () => ({
  useLocaleStore: vi.fn((selector: any) => selector({ locale: 'en' })),
}))

describe('PresenceIndicator', () => {
  beforeEach(() => { vi.useFakeTimers(); seedPresenceBag(() => 0) }) // deterministic first index = 0
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  it('shows the breathing dot with no phrase before 600ms', () => {
    render(<PresenceIndicator />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    for (const p of PRESENCE_POOL.en) expect(screen.queryByText(p)).toBeNull()
  })

  it('holds one pool phrase after 600ms, swaps to slow at 9s, degraded at 25s', () => {
    render(<PresenceIndicator />)
    act(() => { vi.advanceTimersByTime(650) })
    expect(screen.getByText(PRESENCE_POOL.en[0])).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(9_000) })
    expect(screen.getByText(PRESENCE_SLOW.en)).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(16_000) })
    expect(screen.getByText(PRESENCE_DEGRADED.en)).toBeInTheDocument()
  })

  it('fires onPhrase once with the chosen index (client-only analytics)', () => {
    const onPhrase = vi.fn()
    render(<PresenceIndicator onPhrase={onPhrase} />)
    act(() => { vi.advanceTimersByTime(650) })
    expect(onPhrase).toHaveBeenCalledWith(0)
  })

  it('does NOT repeat the phrase across sequential turns (Bug 1 — no-repeat spans unmount)', () => {
    // rng always 0 would repeat index 0 on the second mount if the bag were per-mount.
    // With the module singleton, the second turn's phrase must differ.
    seedPresenceBag(() => 0)
    const seen: number[] = []
    const capture = (id: number) => seen.push(id)

    const t1 = render(<PresenceIndicator onPhrase={capture} />)
    act(() => { vi.advanceTimersByTime(650) })
    t1.unmount()

    const t2 = render(<PresenceIndicator onPhrase={capture} />)
    act(() => { vi.advanceTimersByTime(650) })
    t2.unmount()

    expect(seen).toHaveLength(2)
    expect(seen[1]).not.toBe(seen[0])
  })
})
