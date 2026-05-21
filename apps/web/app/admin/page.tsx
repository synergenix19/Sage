import { createAdminClient } from '@/lib/supabase/admin'
import { fetchAllAdminData } from '@/lib/admin-queries'
import { AdminDashboard } from '@/components/admin/admin-dashboard'

export const revalidate = 60

export default async function AdminPage() {
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
