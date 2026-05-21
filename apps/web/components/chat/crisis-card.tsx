'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'

// CRISIS HOTLINE NUMBERS — confirm with CDA before production deploy.
// Counselling: 800 46342 (MoHAP UAE, free 24/7)
// Emergency:   999       (Dubai Police, immediate danger)
const UAE_COUNSELLING_LINE = '800 46342'
const UAE_COUNSELLING_HREF = 'tel:800-46342'
// tel: URI format — hyphens and spaces are equivalent per RFC 3966
const UAE_EMERGENCY_LINE   = '999'
const UAE_EMERGENCY_HREF   = 'tel:999'

export function CrisisCard({ content }: { content: string }) {
  const locale = useLocaleStore((s) => s.locale)
  const isAr = locale === 'ar'

  return (
    <div className="mx-4 rounded-xl border-2 border-[var(--color-crisis)] bg-[var(--color-crisis)]/10 p-4">
      <p className="mb-2 text-sm font-medium text-[var(--color-crisis)]">
        {isAr ? 'لست وحدك — الدعم متاح' : "You're not alone — support is available"}
      </p>
      <p className="mb-3 text-sm text-[var(--color-text-primary)]">{content}</p>
      <div className="flex flex-col gap-2">
        <a
          href={UAE_COUNSELLING_HREF}
          aria-label="Call 800 46342 – Talk to a counsellor / اتصل بـ 800 46342"
          className="inline-flex min-h-[44px] items-center justify-center rounded-full bg-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-white"
        >
          {isAr ? (
            <>اتصل بـ <span dir="ltr">{UAE_COUNSELLING_LINE}</span> — تحدث مع مستشار</>
          ) : (
            <>Call {UAE_COUNSELLING_LINE} — Talk to a counsellor</>
          )}
        </a>
        <a
          href={UAE_EMERGENCY_HREF}
          aria-label="Call 999 – Emergency services / اتصل بـ 999"
          className="inline-flex min-h-[44px] items-center justify-center rounded-full border-2 border-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-[var(--color-crisis)]"
        >
          {isAr ? (
            <>اتصل بـ <span dir="ltr">{UAE_EMERGENCY_LINE}</span> — خدمات الطوارئ</>
          ) : (
            <>Call {UAE_EMERGENCY_LINE} — Emergency services</>
          )}
        </a>
      </div>
    </div>
  )
}
