// SINGLE SOURCE OF TRUTH — imported by both middleware and application code.
// No external imports. Pure const + function. Edge Runtime compatible.
// Invariant: no other file may define or copy this map.

export const ROLE_KEYS = [
  'member',
  'clinical_reviewer',
  'clinician_author',
  'clinical_approver',
  'operations_admin',
  'dpo',
  'super_admin',
] as const

export type RoleKey = typeof ROLE_KEYS[number]

const PERMISSIONS: Record<RoleKey, readonly string[]> = {
  member:             ['chat:use', 'progress:read', 'biomarker:read'],
  clinical_reviewer:  ['staff:access', 'live:read', 'flags:read', 'review:action'],
  clinician_author:   ['staff:access', 'cms:draft'],
  clinical_approver:  ['staff:access', 'cms:approve', 'flags:read', 'review:action'],
  operations_admin:   ['staff:access', 'admin:read', 'analytics:read'],
  dpo:                ['staff:access', 'audit:read', 'dsr:action'],
  super_admin:        ['*'],
} as const

export function can(roles: RoleKey[], capability: string): boolean {
  return roles.some((r) => {
    const perms = PERMISSIONS[r as RoleKey]
    if (!perms) return false
    return perms.includes('*') || perms.includes(capability)
  })
}
