'use client'
import { createContext, useContext } from 'react'
import type { RoleKey } from './permissions'

const RolesContext = createContext<RoleKey[] | undefined>(undefined)

export function RolesProvider({ roles, children }: { roles: RoleKey[], children: React.ReactNode }) {
  return <RolesContext.Provider value={roles}>{children}</RolesContext.Provider>
}

export function useRoles(): RoleKey[] {
  const ctx = useContext(RolesContext)
  if (ctx === undefined) {
    throw new Error('useRoles() must be called inside a <RolesProvider>.')
  }
  return ctx
}
