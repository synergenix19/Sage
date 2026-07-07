import { describe, it, expect } from 'vitest'
import {
  PRESENCE_PHRASE_MS, PRESENCE_SLOW_MS, PRESENCE_DEGRADED_MS,
  TYPEWRITER_WPS, TYPEWRITER_MAX_MS,
} from '@/lib/presence-constants'

describe('presence-constants', () => {
  it('matches the spec §6 envelope', () => {
    expect(PRESENCE_PHRASE_MS).toBe(600)
    expect(PRESENCE_SLOW_MS).toBe(9_000)
    expect(PRESENCE_DEGRADED_MS).toBe(25_000)
    expect(TYPEWRITER_WPS).toBe(30)
    expect(TYPEWRITER_MAX_MS).toBe(2_500)
  })
  it('phases are strictly increasing (envelope is well-ordered)', () => {
    expect(PRESENCE_PHRASE_MS).toBeLessThan(PRESENCE_SLOW_MS)
    expect(PRESENCE_SLOW_MS).toBeLessThan(PRESENCE_DEGRADED_MS)
  })
})
