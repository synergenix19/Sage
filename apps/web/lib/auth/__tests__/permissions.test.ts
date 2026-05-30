import { describe, it, expect } from 'vitest'
import { can, ROLE_KEYS } from '../permissions'

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
  it('unknown role string is denied and does not throw', () => {
    expect(can(['unknown_role' as any], 'chat:use')).toBe(false)
  })
  it('super_admin with an unknown co-role still grants capabilities', () => {
    expect(can(['super_admin', 'unknown_role' as any], 'any:thing')).toBe(true)
  })
  it('empty capability string is denied for non-wildcard roles', () => {
    expect(can(['member'], '')).toBe(false)
  })

  // Separation-of-duties: author cannot approve, approver cannot draft
  it('clinical_approver cannot draft CMS content', () => {
    expect(can(['clinical_approver'], 'cms:draft')).toBe(false)
  })

  // DPO is audit-only — must not see clinical or ops surfaces
  it('dpo cannot access live session data', () => {
    expect(can(['dpo'], 'live:read')).toBe(false)
  })
  it('dpo cannot access admin analytics', () => {
    expect(can(['dpo'], 'admin:read')).toBe(false)
  })

  // Union grant: two roles combined must not grant a capability neither holds
  it('union of roles does not grant a capability neither role holds', () => {
    // clinical_reviewer + operations_admin: neither holds cms:approve
    expect(can(['clinical_reviewer', 'operations_admin'], 'cms:approve')).toBe(false)
  })

  // Wildcard integrity: only super_admin may hold '*' — catches accidental '*' in any other role
  it('no role except super_admin holds the wildcard', () => {
    for (const role of ROLE_KEYS) {
      if (role === 'super_admin') continue
      expect(can([role], 'totally:made-up-capability')).toBe(false)
    }
  })
})
