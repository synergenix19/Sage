'use client'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'
import { tenant } from '@cdai/tenant'

const COPY = {
  en: {
    heading: 'Before you begin',
    lines: [
      'Sage is an experimental wellbeing tool, not a substitute for professional mental health care.',
      'Conversations are stored and may be reviewed by our clinical team.',
      'If you are in crisis, contact LifeLine Arabia: 4673 (free, 24/7).',
    ],
    cta: 'I understand, continue',
  },
  ar: {
    heading: 'قبل أن تبدأ',
    lines: [
      'سيج أداة تجريبية للعافية، وليست بديلاً عن الرعاية النفسية المتخصصة.',
      'يتم تخزين المحادثات وقد تراجعها فريقنا السريري.',
      'إذا كنت في أزمة، تواصل مع لايف لاين أرابيا: 4673 (مجاني، على مدار الساعة).',
    ],
    cta: 'أفهم وأوافق، متابعة',
  },
} as const

export function Welcome() {
  const { setStep } = useOnboardingStore()
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)
  const copy = COPY[locale] ?? COPY.en

  function next() {
    setStep(2)
    router.push('/step-2')
  }

  return (
    <div className="flex flex-col items-center gap-8 text-center">
      <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-16 w-16" />
      <h1 className="text-2xl font-semibold">{copy.heading}</h1>
      <ul className="flex flex-col gap-3 text-start">
        {copy.lines.map((line, i) => (
          <li key={i} className="flex gap-3 text-sm text-[var(--color-text-secondary)]">
            <span className="mt-0.5 shrink-0 text-[var(--color-primary)]">•</span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
      <Button onClick={next} size="lg" className="w-full">{copy.cta}</Button>
    </div>
  )
}
