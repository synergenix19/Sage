// RSC — reads roles server-side. requireCapability() is the authoritative gate.
// If a user lacks staff:access, notFound() fires here before any page renders.
import type { ReactNode } from 'react'
import { requireCapability } from '@/lib/auth/get-session-roles'
import { StaffShell } from '@/components/staff/staff-shell'

export default async function StaffLayout({ children }: { children: ReactNode }) {
  const roles = await requireCapability('staff:access')
  return <StaffShell roles={roles}>{children}</StaffShell>
}
