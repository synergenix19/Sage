'use client'
import { useRouter } from 'next/navigation'
import { ResponsivePanel } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { createClient } from '@/lib/supabase/client'

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { locale, setLocale } = useLocaleStore()
  const router = useRouter()

  function toggleLocale() {
    const next = locale === 'en' ? 'ar' : 'en'
    setLocale(next)
    document.cookie = `cdai-locale=${next};path=/;max-age=31536000;SameSite=Lax;Secure`
    window.location.reload()
  }

  async function signOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/sign-in')
  }

  return (
    <ResponsivePanel open={open} onClose={onClose} title="Settings">
      <div className="flex flex-col gap-3">
        <button
          onClick={toggleLocale}
          className="min-h-[44px] rounded-xl border border-[var(--color-border)] px-4 py-3 text-start text-sm"
        >
          Language: {locale === 'en' ? 'English → العربية' : 'العربية → English'}
        </button>
        <button
          onClick={signOut}
          className="min-h-[44px] rounded-xl border border-[var(--color-crisis)] px-4 py-3 text-start text-sm text-[var(--color-crisis)]"
        >
          Sign out
        </button>
      </div>
    </ResponsivePanel>
  )
}
