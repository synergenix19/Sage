import { createClient } from '@/lib/supabase/server'
import { can } from './permissions'
import type { RoleKey } from './permissions'
import { notFound, redirect } from 'next/navigation'

const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID

export async function getSessionRoles(): Promise<RoleKey[]> {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  if (!TENANT_ID) throw new Error('[auth] NEXT_PUBLIC_TENANT_ID is not set')

  const { data } = await supabase
    .from('v_user_roles_for_tenant')
    .select('roles')
    .eq('user_id', user.id)
    .eq('tenant_id', TENANT_ID)
    .maybeSingle()

  return (data?.roles as RoleKey[]) ?? ['member']
}

export async function requireCapability(capability: string): Promise<RoleKey[]> {
  const roles = await getSessionRoles()
  // notFound() → 404 avoids capability disclosure.
  if (!can(roles, capability)) notFound()
  return roles
}
