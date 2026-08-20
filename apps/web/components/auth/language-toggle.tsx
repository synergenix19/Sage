'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'
import { t } from '@/lib/copy'

export function LanguageToggle() {
  const { locale, setLocale } = useLocaleStore()

  function toggle() {
    const next = locale === 'en' ? 'ar' : 'en'
    // setLocale writes the cookie and reloads so layout.tsx re-reads it and flips dir
    setLocale(next)
  }

  return (
    <Button variant="ghost" size="sm" onClick={toggle}>
      {t('languageToggle.label', locale)}
    </Button>
  )
}
