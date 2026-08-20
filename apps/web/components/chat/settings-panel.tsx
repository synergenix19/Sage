'use client'
import { useRouter } from 'next/navigation'
import { ResponsivePanel, cn } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { useTextSizeStore, type TextSize } from '@/lib/stores/text-size-store'
import { signOutUser } from '@/lib/auth-actions'
import { t } from '@/lib/copy'

// label/labelAr moved to lib/copy.ts under settingsPanel.textSize.<value>
const TEXT_SIZES: { value: TextSize }[] = [
  { value: 'sm' },
  { value: 'md' },
  { value: 'lg' },
]

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { locale, setLocale } = useLocaleStore()
  const { size, setSize } = useTextSizeStore()
  const router = useRouter()

  function toggleLocale() {
    const next = locale === 'en' ? 'ar' : 'en'
    setLocale(next)
  }

  async function signOut() {
    await signOutUser(router.push)
  }

  return (
    <ResponsivePanel open={open} onClose={onClose} title="Settings">
      <div className="flex flex-col gap-4">
        <button
          onClick={toggleLocale}
          className="min-h-[44px] rounded-xl border border-[var(--color-border)] px-4 py-3 text-start text-sm"
        >
          {t('settingsPanel.toggleLocale', locale)}
        </button>

        <div>
          <p className="mb-2 text-xs text-[var(--color-text-secondary)]">
            {t('settingsPanel.textSizeLabel', locale)}
          </p>
          <div className="flex gap-2">
            {TEXT_SIZES.map(({ value }) => (
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
                {t(`settingsPanel.textSize.${value}`, locale)}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={signOut}
          className="min-h-[44px] rounded-xl border border-[var(--color-crisis)] px-4 py-3 text-start text-sm text-[var(--color-crisis)]"
        >
          {t('settingsPanel.signOut', locale)}
        </button>
      </div>
    </ResponsivePanel>
  )
}
