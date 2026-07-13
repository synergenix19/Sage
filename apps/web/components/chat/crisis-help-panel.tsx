'use client'
import { ResponsivePanel } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { CrisisResourceList } from './crisis-resource-list'

// Persistent "Get help now" affordance (spec §Persistent affordance). Available EVERY turn from the
// chat header — not only on crisis detection. It renders the SAME resource list ENTIRELY
// client-side from the static array (CrisisResourceList → crisis-config.ts): no /chat call, no
// server round-trip, so a user reaching for help while the backend is slow/down still gets dialable
// numbers (deterministic + offline-capable). Bilingual from day one (no EN-only F3 regression).
export function CrisisHelpPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const locale = useLocaleStore((s) => s.locale)
  const isAr = locale === 'ar'

  return (
    <ResponsivePanel open={open} onClose={onClose} title={isAr ? 'احصل على المساعدة الآن' : 'Get help now'}>
      <div className="flex flex-col gap-3">
        <p className="text-sm text-[var(--color-text-secondary)]" dir="auto">
          {isAr
            ? 'لست وحدك. إذا كنت بحاجة إلى التحدث مع شخص ما الآن، تواصل مع أحد هذه الخطوط.'
            : "You're not alone. If you need to talk to someone now, reach one of these lines."}
        </p>
        <CrisisResourceList />
      </div>
    </ResponsivePanel>
  )
}
