import { createAdminClient } from '@/lib/supabase/admin'
import { createClient } from '@/lib/supabase/server'
import { fetchAllAdminData } from '@/lib/admin-queries'
import { AdminDashboard } from '@/components/admin/admin-dashboard'
import type { ConformanceReport } from '@/components/admin/schema-conformance-panel'
import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  const { data: profile, error: profileError } = await supabase
    .from('user_profiles')
    .select('is_admin')
    .eq('id', user.id)
    .single()

  if (profileError && profileError.code !== 'PGRST116') {
    console.error('[admin] profile fetch error:', profileError)
  }
  if (!profile?.is_admin) redirect('/chat')

  let data: Awaited<ReturnType<typeof fetchAllAdminData>>
  try {
    const admin = createAdminClient()
    data = await fetchAllAdminData(admin)
  } catch (err) {
    console.error('[admin] data fetch failed:', err)
    return (
      <div className="p-6">
        <p className="text-sm text-[var(--color-crisis)]">
          Admin data temporarily unavailable. Contact the platform team.
        </p>
      </div>
    )
  }

  const sageUrl = process.env.SAGE_API_URL ?? 'http://localhost:8000'
  let conformance: ConformanceReport | null = null
  try {
    const res = await fetch(`${sageUrl}/health/schema-conformance`, {
      next: { revalidate: 3600 },
    })
    if (res.ok) conformance = (await res.json()) as ConformanceReport
  } catch {
    // sage-poc offline — panel shows fallback state
  }

  return <AdminDashboard data={data} conformance={conformance} />
}
