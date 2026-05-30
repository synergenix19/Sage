'use client'
import type { ReactNode } from 'react'
import { RolesProvider } from '@/lib/auth/roles-context'
import { StaffNav } from './staff-nav'
import type { RoleKey } from '@/lib/auth/permissions'

interface Props {
  roles: RoleKey[]
  children: ReactNode
}

export function StaffShell({ roles, children }: Props) {
  return (
    <RolesProvider roles={roles}>
      <div className="flex h-dvh flex-col bg-[var(--color-surface)]">
        <StaffNav />
        <main id="main-content" className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </RolesProvider>
  )
}
