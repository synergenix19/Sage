import { createClient } from '@/lib/supabase/server'
import { ROLE_KEYS, can } from './permissions'
import type { RoleKey } from './permissions'
import { notFound, redirect } from 'next/navigation'

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID

export async function getSessionRoles(): Promise<RoleKey[]> {
  if (!TENANT_ID) throw new Error('[auth] NEXT_PUBLIC_TENANT_ID is not set')
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  const { data, error } = await supabase
    .from('v_user_roles_for_tenant')
    .select('roles')
    .eq('user_id', user.id)
    .eq('tenant_id', TENANT_ID)
    .maybeSingle()

  if (error) throw new Error(`[auth] role lookup failed: ${error.message}`)

  const raw: unknown[] = Array.isArray(data?.roles) ? data.roles : []
  const roles = raw.filter((r): r is RoleKey =>
    typeof r === 'string' && (ROLE_KEYS as readonly string[]).includes(r)
  )
  return roles.length > 0 ? roles : ['member']
}

export async function requireCapability(capability: string): Promise<RoleKey[]> {
  const roles = await getSessionRoles()
  // notFound() → 404 avoids capability disclosure.
  if (!can(roles, capability)) notFound()
  return roles
}
