import { describe, it, expect } from 'vitest'
import {
  CRISIS_RESOURCES,
  CRISIS_CONFIG,
  selectCrisisResources,
  leadingResources,
  is247,
  type CrisisResource,
} from '../crisis-config'

// Single source for every crisis surface (crisis card, "Get help now" affordance, onboarding). These
// tests check the source is INTERNALLY COHERENT + the lead-logic mirrors the backend. They do NOT
// pin which numbers are correct (the dial-test/PO ruling owns that); the cross-stack parity test
// (sage-poc) pins that the array MATCHES the backend CRISIS_RESOURCES. If a value changes it changes
// in this file + the backend config, nowhere else.
describe('CRISIS_RESOURCES — array shape + internal consistency', () => {
  it('is a non-empty ordered array of well-formed resources', () => {
    expect(Array.isArray(CRISIS_RESOURCES)).toBe(true)
    expect(CRISIS_RESOURCES.length).toBeGreaterThanOrEqual(2)
    for (const r of CRISIS_RESOURCES) {
      expect(r.labelEn.trim()).not.toBe('')
      expect(r.labelAr.trim()).not.toBe('')
      expect(r.number.trim()).not.toBe('')
      expect(r.hours.trim()).not.toBe('')
      expect(r.scope.trim()).not.toBe('')
    }
  })

  it('every tel: URI dials exactly the displayed number (guards a stale/mismatched dial target)', () => {
    for (const r of CRISIS_RESOURCES) {
      expect(r.tel).toBe('tel:' + r.number.replace(/\s+/g, '-'))
    }
  })

  it('always contains an emergency line and at least one 24/7 line', () => {
    expect(CRISIS_RESOURCES.some((r) => r.scope === 'emergency')).toBe(true)
    expect(CRISIS_RESOURCES.some((r) => is247(r))).toBe(true)
  })

  it('contains the current verified values (MoHAP national + 999 emergency) — Phase 1 unchanged', () => {
    const national = CRISIS_RESOURCES.find((r) => r.scope === 'national')
    const emergency = CRISIS_RESOURCES.find((r) => r.scope === 'emergency')
    expect(national?.number).toBe('800 46342')
    expect(national?.hours).toBe('24/7')
    expect(emergency?.number).toBe('999')
  })
})

describe('CRISIS_CONFIG — derived back-compat object', () => {
  it('derives from the national + emergency entries and stays tel-coherent', () => {
    expect(CRISIS_CONFIG.tel).toBe('tel:' + CRISIS_CONFIG.number.replace(/\s+/g, '-'))
    expect(CRISIS_CONFIG.emergencyTel).toBe('tel:' + CRISIS_CONFIG.emergency.replace(/\s+/g, '-'))
    const national = CRISIS_RESOURCES.find((r) => r.scope === 'national')
    expect(CRISIS_CONFIG.number).toBe(national?.number)
    expect(CRISIS_CONFIG.labelEn).toBe(national?.labelEn)
  })
})

// Synthetic multi-resource set used ONLY to exercise the hours-aware lead-logic + top-3 invariant
// with a richer composition than the current 2-entry production array (both current entries are
// 24/7, so day/night ordering is not observable on them). Mirrors the shape the doc's 5-entry
// composition will take when the clinician-gated value flip lands.
const SYNTH: CrisisResource[] = [
  { labelEn: 'National (8-8)', labelAr: 'وطني', number: '800 1', tel: 'tel:800-1', hours: '8am-8pm', scope: 'national' },
  { labelEn: 'SAKINA 24/7', labelAr: 'سكينة', number: '800 2', tel: 'tel:800-2', hours: '24/7', scope: 'support' },
  { labelEn: 'DHA 24/7', labelAr: 'دبي', number: '800 3', tel: 'tel:800-3', hours: '24/7', scope: 'support' },
  { labelEn: 'Sharjah (8-8)', labelAr: 'الشارقة', number: '800 4', tel: 'tel:800-4', hours: '8am-8pm', scope: 'support' },
  { labelEn: 'Emergency', labelAr: 'طوارئ', number: '999', tel: 'tel:999', hours: '24/7', scope: 'emergency' },
]

describe('selectCrisisResources — hours-aware lead-logic (mirrors backend)', () => {
  it('by day (national open) → the national line leads', () => {
    const day = new Date(2026, 6, 13, 12, 0) // 12:00 local
    const ordered = selectCrisisResources({ resources: SYNTH, now: day })
    expect(ordered[0].scope).toBe('national')
  })

  it('at night (national closed) → a 24/7 line leads, never the closed national line', () => {
    const night = new Date(2026, 6, 13, 3, 0) // 03:00 local — outside 8am-8pm
    const ordered = selectCrisisResources({ resources: SYNTH, now: night })
    expect(is247(ordered[0])).toBe(true)
    expect(ordered[0].scope).not.toBe('national')
  })

  it('immediateDanger → emergency (999) leads', () => {
    const day = new Date(2026, 6, 13, 12, 0)
    const ordered = selectCrisisResources({ resources: SYNTH, now: day, immediateDanger: true })
    expect(ordered[0].scope).toBe('emergency')
  })

  it('always yields at least one 24/7 line regardless of the clock', () => {
    for (const hour of [0, 3, 9, 15, 21, 23]) {
      const ordered = selectCrisisResources({ resources: SYNTH, now: new Date(2026, 6, 13, hour, 0) })
      expect(ordered.some((r) => is247(r) || r.scope === 'emergency')).toBe(true)
    }
  })
})

describe('leadingResources — top-3 hard safety invariant', () => {
  it('999 AND a 24/7 line are ALWAYS in the top 3, at any hour (expander never hides them)', () => {
    for (const hour of [0, 3, 9, 15, 21, 23]) {
      const ordered = selectCrisisResources({ resources: SYNTH, now: new Date(2026, 6, 13, hour, 0) })
      const top = leadingResources(ordered, 3)
      expect(top.length).toBeLessThanOrEqual(3)
      expect(top.some((r) => r.scope === 'emergency')).toBe(true) // 999 present
      expect(top.some((r) => is247(r))).toBe(true) // a line that answers at 3am present
    }
  })

  it('on the current 2-entry production array, both entries are inline (nothing hidden)', () => {
    const ordered = selectCrisisResources()
    const top = leadingResources(ordered, 3)
    expect(top.length).toBe(CRISIS_RESOURCES.length)
    expect(top.some((r) => r.scope === 'emergency')).toBe(true)
    expect(top.some((r) => r.scope === 'national')).toBe(true)
  })
})
