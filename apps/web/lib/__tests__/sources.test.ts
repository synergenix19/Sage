import { describe, it, expect } from 'vitest'
import { hydrateSources } from '../sources'

// Lane 2 Item 1.5 (c): malformed-data safety. Hydration must render through the
// same source-card guard: stored jsonb of an unexpected shape (older schema
// version, hand-edited row, empty array) degrades to no card, never a crash.
describe('hydrateSources', () => {
  it('hydrates a valid stored sources array onto the message', () => {
    const src = [{ type: 'article', title: 'T', url: 'https://kb/a', citation: 'c' }]
    expect(hydrateSources(src)).toEqual(src)
  })

  it('degrades a non-array object to undefined (no card, no crash)', () => {
    expect(hydrateSources({ not: 'an array' })).toBeUndefined()
  })

  it('degrades null to undefined', () => {
    expect(hydrateSources(null)).toBeUndefined()
  })

  it('degrades an empty array to undefined', () => {
    expect(hydrateSources([])).toBeUndefined()
  })

  it('degrades undefined to undefined', () => {
    expect(hydrateSources(undefined)).toBeUndefined()
  })

  it('degrades a scalar (string) to undefined', () => {
    expect(hydrateSources('not an array')).toBeUndefined()
  })
})
