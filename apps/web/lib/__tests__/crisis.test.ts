import { describe, it, expect } from 'vitest'
import { hasCrisisSignal, stripCrisisSignal } from '@/lib/crisis'
import { CRISIS_SIGNAL } from '@/lib/constants'

describe('crisis sentinel helpers', () => {
  const body = 'You are not alone — support is available.'

  it('detects the in-band sentinel prefix', () => {
    expect(hasCrisisSignal(`${CRISIS_SIGNAL}${body}`)).toBe(true)
    expect(hasCrisisSignal(body)).toBe(false)
  })

  it('strips the sentinel (and its leading whitespace) — the pinned "never store/render the sentinel" invariant', () => {
    expect(stripCrisisSignal(`${CRISIS_SIGNAL}\n${body}`)).toBe(body)
    expect(stripCrisisSignal(`${CRISIS_SIGNAL}${body}`)).toBe(body)
    // stripped output must never still contain the sentinel
    expect(stripCrisisSignal(`${CRISIS_SIGNAL}${body}`)).not.toContain('CRISIS_DETECTED')
  })

  it('is a no-op on already-clean content and idempotent', () => {
    expect(stripCrisisSignal(body)).toBe(body)
    expect(stripCrisisSignal(stripCrisisSignal(`${CRISIS_SIGNAL}${body}`))).toBe(body)
  })
})
