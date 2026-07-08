import { describe, it, expect } from 'vitest'
import { CRISIS_CONFIG } from '../crisis-config'

// The ONE place the approved crisis-contact values are pinned (PO 2026-07-08). Every crisis
// surface (crisis card, onboarding) reads from CRISIS_CONFIG — nothing re-embeds a literal.
// If the approved number changes, it changes HERE (and the backend config), nowhere else.
describe('CRISIS_CONFIG — approved single source of truth', () => {
  it('pins the PO-approved number, hours, emergency, tel', () => {
    expect(CRISIS_CONFIG.number).toBe('800 46342')
    expect(CRISIS_CONFIG.hours).toBe('24/7')
    expect(CRISIS_CONFIG.emergency).toBe('999')
    expect(CRISIS_CONFIG.tel).toBe('tel:800-46342')
    expect(CRISIS_CONFIG.emergencyTel).toBe('tel:999')
  })
})
