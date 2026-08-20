'use client'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'
import { tenant } from '@cdai/tenant'
import { CRISIS_CONFIG } from '@/lib/crisis-config'
import { t } from '@/lib/copy'

// Crisis line uses the SAME source as the crisis card (PO 2026-07-08: onboarding must show the
// crisis number, not a separate service). Number/label/hours from crisis-config.ts — no literal
// here. Composed locally (not in lib/copy.ts) so it can never drift from CRISIS_CONFIG — the
// copy registry extraction (P4 Task 2) deliberately does not freeze this line as a static string.
function crisisLine(locale: 'en' | 'ar'): string {
  return locale === 'ar'
    ? `إذا كنت في أزمة، تواصل مع ${CRISIS_CONFIG.labelAr}: ${CRISIS_CONFIG.number} (مجاني، على مدار الساعة).`
    : `If you are in crisis, contact ${CRISIS_CONFIG.labelEn}: ${CRISIS_CONFIG.number} (free, ${CRISIS_CONFIG.hours}).`
}

export function Welcome() {
  const { setStep } = useOnboardingStore()
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)
  const lines = [t('welcome.line1', locale), t('welcome.line2', locale), crisisLine(locale)]

  function next() {
    setStep(2)
    router.push('/step-2')
  }

  return (
    <div className="flex flex-col items-center gap-8 text-center">
      <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-16 w-16" />
      <h1 className="text-2xl font-semibold">{t('welcome.heading', locale)}</h1>
      <ul className="flex flex-col gap-3 text-start">
        {lines.map((line, i) => (
          <li key={i} className="flex gap-3 text-sm text-[var(--color-text-secondary)]">
            <span className="mt-0.5 shrink-0 text-[var(--color-primary)]">•</span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
      <Button onClick={next} size="lg" className="w-full">{t('welcome.cta', locale)}</Button>
    </div>
  )
}
