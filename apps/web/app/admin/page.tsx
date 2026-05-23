import { createAdminClient } from '@/lib/supabase/admin'
import { createClient } from '@/lib/supabase/server'
import { fetchAllAdminData } from '@/lib/admin-queries'
import { AdminDashboard } from '@/components/admin/admin-dashboard'
import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  const { data: profile } = await supabase
    .from('user_profiles')
    .select('is_admin')
    .eq('id', user.id)
    .single()

  if (!profile?.is_admin) redirect('/chat')

  let data
  try {
    const admin = createAdminClient()
    data = await fetchAllAdminData(admin)
  } catch (err) {
    console.error('[admin] data fetch failed:', err)
    return (
      <div className="p-6">
        <p className="text-sm text-[var(--color-crisis)]">
          Admin data unavailable. Check SUPABASE_SERVICE_ROLE_KEY in .env.local.
        </p>
      </div>
    )
  }

  return <AdminDashboard data={data} />
}
