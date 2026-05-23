import { describe, it, expect } from 'vitest'

describe('CRISIS_SIGNAL', () => {
  it('is importable from lib/constants', async () => {
    const { CRISIS_SIGNAL } = await import('../constants')
    expect(CRISIS_SIGNAL).toBe('[[CRISIS_DETECTED]]')
  })
})
