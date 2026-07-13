'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CrisisResourceList } from './crisis-resource-list'

// Pinned-until-resolved crisis card. Renders an ORDERED, multi-resource list (crisis-resource-list)
// instead of two fixed buttons — hours-aware lead-logic + a "More options" expander, with 999 and a
// 24/7 line always inline. Numbers/labels come only from crisis-config.ts (no literals here).
// role="alert" + aria-atomic + bilingual heading preserved. The pinned lifecycle (dismiss on
// backend X-Sage-Crisis-State === 'resolved') lives in chat-interface.tsx and is unchanged.
export function CrisisCard({ content }: { content: string }) {
  const locale = useLocaleStore((s) => s.locale)
  const isAr = locale === 'ar'

  return (
    <div
      role="alert"
      aria-atomic="true"
      className="mx-4 rounded-xl border-2 border-[var(--color-crisis)] bg-[var(--color-crisis)]/10 p-4"
    >
      <p className="mb-2 text-sm font-medium text-[var(--color-crisis)]">
        {isAr ? 'لست وحدك — الدعم متاح' : "You're not alone — support is available"}
      </p>
      <p className="mb-3 text-sm text-[var(--color-text-primary)]" dir="auto">
        {content}
      </p>
      <CrisisResourceList />
    </div>
  )
}
