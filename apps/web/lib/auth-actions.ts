import { createClient } from '@/lib/supabase/client'

export async function signOutUser(push: (href: string) => void): Promise<void> {
  const supabase = createClient()
  await supabase.auth.signOut()
  push('/sign-in')
}
