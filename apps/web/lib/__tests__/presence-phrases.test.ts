import { describe, it, expect } from 'vitest'
import { PRESENCE_POOL, PRESENCE_SLOW, PRESENCE_DEGRADED, createShuffleBag, nextPresencePhraseIndex, seedPresenceBag } from '@/lib/presence-phrases'

describe('presence copy pool', () => {
  it('EN and AR pools are the same length and non-empty', () => {
    expect(PRESENCE_POOL.en.length).toBeGreaterThan(0)
    expect(PRESENCE_POOL.en.length).toBe(PRESENCE_POOL.ar.length)
  })
  it('contains none of the banned word-classes (process/promise/whimsy)', () => {
    const banned = /analy|check|assess|process|solv|find the answer|ponder|brew/i
    for (const s of [...PRESENCE_POOL.en, PRESENCE_SLOW.en, PRESENCE_DEGRADED.en]) {
      expect(s).not.toMatch(banned)
    }
  })
  it('holds out the gendered self-reference pair (persona-gender open item, spec §2.2)', () => {
    expect(PRESENCE_POOL.ar.join(' ')).not.toContain('موجود')
  })
})

describe('createShuffleBag', () => {
  it('never returns the same index twice in a row', () => {
    // Deterministic rng cycling through a fixed sequence.
    const seq = [0.0, 0.0, 0.99, 0.5, 0.0, 0.0]
    let i = 0
    const rng = () => seq[i++ % seq.length]
    const bag = createShuffleBag(4, rng)
    let prev = bag.next()
    for (let n = 0; n < 20; n++) {
      const cur = bag.next()
      expect(cur).not.toBe(prev)
      expect(cur).toBeGreaterThanOrEqual(0)
      expect(cur).toBeLessThan(4)
      prev = cur
    }
  })
  it('is deterministic under a seeded rng (enables the indistinguishability test)', () => {
    const mk = () => { let i = 0; const s = [0.1, 0.7, 0.3, 0.9]; return createShuffleBag(4, () => s[i++ % s.length]) }
    const a = mk(); const b = mk()
    expect([a.next(), a.next(), a.next()]).toEqual([b.next(), b.next(), b.next()])
  })
})

describe('singleton presence bag (no-repeat survives across turns)', () => {
  it('nextPresencePhraseIndex does not repeat even across separate calls (module state persists)', () => {
    // rng always 0 would repeat index 0 every draw WITHOUT cross-call memory;
    // the singleton remembers `prev`, so the second draw is forced to differ.
    seedPresenceBag(() => 0)
    const first = nextPresencePhraseIndex()
    const second = nextPresencePhraseIndex()
    expect(second).not.toBe(first)
  })
})
