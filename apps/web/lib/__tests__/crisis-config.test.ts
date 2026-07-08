import { describe, it, expect } from 'vitest'
import { CRISIS_CONFIG } from '../crisis-config'

// Single source for every crisis surface (crisis card, onboarding). This test checks the source is
// INTERNALLY COHERENT — it does NOT pin which number is correct (the dial-test owns that verdict;
// pinning "800 46342" would red the build for inserting a dial-test-confirmed 800 4673). If the
// number changes, it changes in this file + the backend config, nowhere else.
describe('CRISIS_CONFIG — single source, internal consistency', () => {
  it('exposes non-empty contacts and tel: URIs that mirror the displayed numbers', () => {
    expect(CRISIS_CONFIG.number.trim()).not.toBe('')
    expect(CRISIS_CONFIG.emergency.trim()).not.toBe('')
    // tel: must dial exactly what is displayed — guards against a call button dialing a stale number.
    expect(CRISIS_CONFIG.tel).toBe('tel:' + CRISIS_CONFIG.number.replace(/\s+/g, '-'))
    expect(CRISIS_CONFIG.emergencyTel).toBe('tel:' + CRISIS_CONFIG.emergency.replace(/\s+/g, '-'))
  })
})
