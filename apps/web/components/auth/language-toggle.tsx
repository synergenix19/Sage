'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'

export function LanguageToggle() {
  const { locale, setLocale } = useLocaleStore()

  function toggle() {
    const next = locale === 'en' ? 'ar' : 'en'
    setLocale(next)
    document.cookie = `cdai-locale=${next};path=/;max-age=31536000;SameSite=Lax;Secure`
    // Reload so layout.tsx re-reads the cookie and flips dir
    window.location.reload()
  }

  return (
    <Button variant="ghost" size="sm" onClick={toggle}>
      {locale === 'en' ? 'عربي' : 'EN'}
    </Button>
  )
}
