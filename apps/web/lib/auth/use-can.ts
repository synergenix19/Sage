// Context-based — no arguments. Call useCan() inside RolesProvider tree.
import { useCallback } from 'react'
import { can } from './permissions'
import { useRoles } from './roles-context'

export function useCan() {
  const roles = useRoles()
  return useCallback((capability: string) => can(roles, capability), [roles])
}
