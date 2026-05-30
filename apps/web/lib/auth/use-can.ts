// Context-based — no arguments. Call useCan() inside RolesProvider tree.
import { can } from './permissions'
import { useRoles } from './roles-context'

export function useCan() {
  const roles = useRoles()
  return (capability: string) => can(roles, capability)
}
