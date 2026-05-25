import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { fetchAllProgressData } from '@/lib/progress-queries'
import { ProgressView } from '@/components/progress/progress-view'

export default async function ProgressPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')
  const data = await fetchAllProgressData(supabase, user.id)
  return <ProgressView data={data} />
}
