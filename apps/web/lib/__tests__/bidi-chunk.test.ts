// apps/web/lib/__tests__/bidi-chunk.test.ts
import { describe, it, expect } from 'vitest'
import { chunkForReveal } from '@/lib/bidi-chunk'

const AR_WORD = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/
const LAT_WORD = /[A-Za-z]/

describe('chunkForReveal', () => {
  it('reconstructs the original text exactly (whitespace preserved)', () => {
    const t = 'Thinking about what you said today.\nOne more line.'
    expect(chunkForReveal(t).join('')).toBe(t)
  })
  it('never puts more than 2 word-tokens in a chunk', () => {
    const chunks = chunkForReveal('one two three four five six')
    for (const c of chunks) {
      const words = c.trim().split(/\s+/).filter(Boolean)
      expect(words.length).toBeLessThanOrEqual(2)
    }
  })
  it('never straddles a direction change (code-switched text — C-2 eval shape)', () => {
    const t = 'أحس بضغط كبير and my boss keeps calling'
    const chunks = chunkForReveal(t)
    expect(chunks.join('')).toBe(t)
    for (const c of chunks) {
      const hasAr = AR_WORD.test(c)
      const hasLat = LAT_WORD.test(c)
      expect(hasAr && hasLat).toBe(false) // no chunk mixes an Arabic word and a Latin word
    }
  })
  it('handles empty and single-word input', () => {
    expect(chunkForReveal('')).toEqual([])
    expect(chunkForReveal('hello').join('')).toBe('hello')
  })
})
