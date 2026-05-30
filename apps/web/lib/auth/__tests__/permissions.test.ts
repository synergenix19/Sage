import { describe, it, expect } from 'vitest'
import { can } from '../edge-permissions'

describe('can()', () => {
  it('grants capability when role holds it', () => {
    expect(can(['clinical_reviewer'], 'live:read')).toBe(true)
  })
  it('denies capability when role lacks it', () => {
    expect(can(['member'], 'live:read')).toBe(false)
  })
  it('super_admin wildcard grants any capability', () => {
    expect(can(['super_admin'], 'any:thing')).toBe(true)
  })
  it('union of roles grants union of capabilities', () => {
    expect(can(['clinical_reviewer', 'operations_admin'], 'live:read')).toBe(true)
    expect(can(['clinical_reviewer', 'operations_admin'], 'admin:read')).toBe(true)
  })
  it('empty roles denies everything', () => {
    expect(can([], 'chat:use')).toBe(false)
  })
  it('member cannot access staff surfaces', () => {
    expect(can(['member'], 'staff:access')).toBe(false)
    expect(can(['member'], 'live:read')).toBe(false)
    expect(can(['member'], 'admin:read')).toBe(false)
  })
  it('clinical_reviewer cannot access admin', () => {
    expect(can(['clinical_reviewer'], 'admin:read')).toBe(false)
  })
  it('operations_admin cannot access live', () => {
    expect(can(['operations_admin'], 'live:read')).toBe(false)
  })
  it('clinical_approver holds review:action', () => {
    expect(can(['clinical_approver'], 'review:action')).toBe(true)
  })
  it('clinician_author cannot approve', () => {
    expect(can(['clinician_author'], 'cms:approve')).toBe(false)
  })
})
