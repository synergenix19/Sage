'use client'
import { useRouter } from 'next/navigation'
import { ResponsivePanel, cn } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { useTextSizeStore, type TextSize } from '@/lib/stores/text-size-store'
import { createClient } from '@/lib/supabase/client'

const TEXT_SIZES: { value: TextSize; label: string; labelAr: string }[] = [
  { value: 'sm', label: 'Small',  labelAr: 'صغير'  },
  { value: 'md', label: 'Medium', labelAr: 'متوسط' },
  { value: 'lg', label: 'Large',  labelAr: 'كبير'  },
]

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { locale, setLocale } = useLocaleStore()
  const { size, setSize } = useTextSizeStore()
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
      <div className="flex flex-col gap-4">
        <button
          onClick={toggleLocale}
          className="min-h-[44px] rounded-xl border border-[var(--color-border)] px-4 py-3 text-start text-sm"
        >
          {locale === 'en' ? 'Language: English → العربية' : 'اللغة: العربية → English'}
        </button>

        <div>
          <p className="mb-2 text-xs text-[var(--color-text-secondary)]">
            {locale === 'en' ? 'Text size' : 'حجم النص'}
          </p>
          <div className="flex gap-2">
            {TEXT_SIZES.map(({ value, label, labelAr }) => (
              <button
                key={value}
                onClick={() => setSize(value)}
                className={cn(
                  'min-h-[44px] flex-1 rounded-xl border py-3 text-sm transition-colors duration-200',
                  size === value
                    ? 'border-[var(--color-primary)] bg-[var(--color-surface-tinted)] text-[var(--color-primary)]'
                    : 'border-[var(--color-border)] text-[var(--color-text-secondary)]'
                )}
              >
                {locale === 'en' ? label : labelAr}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={signOut}
          className="min-h-[44px] rounded-xl border border-[var(--color-crisis)] px-4 py-3 text-start text-sm text-[var(--color-crisis)]"
        >
          {locale === 'en' ? 'Sign out' : 'تسجيل الخروج'}
        </button>
      </div>
    </ResponsivePanel>
  )
}
