import { createClient } from '@/lib/supabase/client'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export async function signOutUser(push: (href: string) => void): Promise<void> {
  useOnboardingStore.getState().reset()
  const supabase = createClient()
  await supabase.auth.signOut()
  push('/sign-in')
}
