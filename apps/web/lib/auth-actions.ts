import { createClient } from '@/lib/supabase/client'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export async function signOutUser(push: (href: string) => void): Promise<void> {
  useOnboardingStore.getState().reset()
  const supabase = createClient()
  try {
    await supabase.auth.signOut()
  } catch (err) {
    console.error('[auth] signOut failed, forcing redirect:', err)
  } finally {
    push('/sign-in')
  }
}
