'use client'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'
import type { Locale } from '@cdai/types'

const OPTIONS: { label: string; value: Locale }[] = [
  { label: 'English', value: 'en' },
  { label: 'العربية', value: 'ar' },
]

export function Language() {
  const { setAnswer, setStep } = useOnboardingStore()
  const setLocale = useLocaleStore((s) => s.setLocale)

  function choose(locale: Locale) {
    setAnswer('locale', locale)
    setLocale(locale)
    document.cookie = `cdai-locale=${locale};path=/;max-age=31536000;SameSite=Lax;Secure`
    setStep(3)
    // Reload to flip dir immediately, then navigate
    window.location.href = '/step-3'
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold text-center">Choose your language</h2>
      {OPTIONS.map((opt) => (
        <Button key={opt.value} variant="outline" size="lg" className="w-full" onClick={() => choose(opt.value)}>
          {opt.label}
        </Button>
      ))}
    </div>
  )
}
