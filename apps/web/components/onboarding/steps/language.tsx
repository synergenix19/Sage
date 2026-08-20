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
    setStep(3)
    // setLocale writes the cookie, then navigates to step-3 (instead of
    // reloading in place) so the dir flip and the step advance happen in the
    // same hard navigation.
    setLocale(locale, { redirectTo: '/step-3' })
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
