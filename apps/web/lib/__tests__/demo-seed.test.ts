import { describe, it, expect } from 'vitest'
import { getUserDemoData } from '../demo-seed'

describe('getUserDemoData', () => {
  const data = getUserDemoData('user-abc-123')

  it('returns 21 mood scores', () => {
    expect(data.moodScores).toHaveLength(21)
  })

  it('all scores are between 1 and 5', () => {
    data.moodScores.forEach((s) => {
      expect(s.score).toBeGreaterThanOrEqual(1)
      expect(s.score).toBeLessThanOrEqual(5)
    })
  })

  it('is deterministic — same input gives same output', () => {
    const data2 = getUserDemoData('user-abc-123')
    expect(data.moodScores[0].score).toBe(data2.moodScores[0].score)
  })

  it('different user IDs produce different data', () => {
    const data2 = getUserDemoData('user-xyz-999')
    expect(data.moodScores[0].score).not.toBe(data2.moodScores[0].score)
  })
})
