import { describe, it, expect } from 'vitest'

describe('lib/constants', () => {
  it('exports correct sentinel values', async () => {
    const { CRISIS_SIGNAL, SERVER_ERROR_SIGNAL } = await import('../constants')
    expect(CRISIS_SIGNAL).toBe('[[CRISIS_DETECTED]]')
    expect(SERVER_ERROR_SIGNAL).toBe('[[SERVER_ERROR]]')
  })
})
