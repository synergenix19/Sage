'use client'
import { createContext, useContext } from 'react'
import type { RoleKey } from './permissions'

const RolesContext = createContext<RoleKey[]>([])

export function RolesProvider({ roles, children }: { roles: RoleKey[], children: React.ReactNode }) {
  return <RolesContext.Provider value={roles}>{children}</RolesContext.Provider>
}

export function useRoles(): RoleKey[] {
  return useContext(RolesContext)
}
