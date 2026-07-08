'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CRISIS_CONFIG } from '@/lib/crisis-config'

// Crisis numbers come from the single source (crisis-config.ts) — no literals in this file.
export function CrisisCard({ content }: { content: string }) {
  const locale = useLocaleStore((s) => s.locale)
  const isAr = locale === 'ar'

  return (
    <div role="alert" aria-atomic="true" className="mx-4 rounded-xl border-2 border-[var(--color-crisis)] bg-[var(--color-crisis)]/10 p-4">
      <p className="mb-2 text-sm font-medium text-[var(--color-crisis)]">
        {isAr ? 'لست وحدك — الدعم متاح' : "You're not alone — support is available"}
      </p>
      <p className="mb-3 text-sm text-[var(--color-text-primary)]" dir="auto">{content}</p>
      <div className="flex flex-col gap-2">
        <a
          href={CRISIS_CONFIG.tel}
          aria-label={`Call ${CRISIS_CONFIG.number} – Talk to a counsellor / اتصل بـ ${CRISIS_CONFIG.number}`}
          className="inline-flex min-h-[44px] items-center justify-center rounded-full bg-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-white"
        >
          {isAr ? (
            <>اتصل بـ <span dir="ltr">{CRISIS_CONFIG.number}</span> — تحدث مع مستشار</>
          ) : (
            <>Call {CRISIS_CONFIG.number} — Talk to a counsellor</>
          )}
        </a>
        <a
          href={CRISIS_CONFIG.emergencyTel}
          aria-label={`Call ${CRISIS_CONFIG.emergency} – Emergency services / اتصل بـ ${CRISIS_CONFIG.emergency}`}
          className="inline-flex min-h-[44px] items-center justify-center rounded-full border-2 border-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-[var(--color-crisis)]"
        >
          {isAr ? (
            <>اتصل بـ <span dir="ltr">{CRISIS_CONFIG.emergency}</span> — خدمات الطوارئ</>
          ) : (
            <>Call {CRISIS_CONFIG.emergency} — Emergency services</>
          )}
        </a>
      </div>
    </div>
  )
}
