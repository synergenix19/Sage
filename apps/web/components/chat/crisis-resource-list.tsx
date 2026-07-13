'use client'
import { useState } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import {
  CRISIS_RESOURCES,
  selectCrisisResources,
  leadingResources,
  type CrisisResource,
} from '@/lib/crisis-config'

// Localized hours chip. "24/7" is spelled out in Arabic; a daily window (e.g. "8am-8pm") is Latin so
// it is wrapped dir="ltr" inside the RTL flow. Numbers/labels come only from crisis-config.ts.
function hoursLabel(resource: CrisisResource, isAr: boolean) {
  if (resource.hours.includes('24/7')) {
    return <span>{isAr ? 'على مدار الساعة' : '24/7'}</span>
  }
  return <span dir="ltr">{resource.hours}</span>
}

function CrisisResourceRow({ resource, isAr }: { resource: CrisisResource; isAr: boolean }) {
  const label = isAr ? resource.labelAr : resource.labelEn
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-[var(--color-crisis)]/30 bg-[var(--color-surface)] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-[var(--color-text-primary)]" dir="auto">
          {label}
        </span>
        <span className="shrink-0 rounded-full bg-[var(--color-crisis)]/10 px-2 py-0.5 text-xs font-medium text-[var(--color-crisis)]">
          {hoursLabel(resource, isAr)}
        </span>
      </div>
      <a
        href={resource.tel}
        aria-label={
          isAr
            ? `اتصل بـ ${resource.number} — ${resource.labelAr}`
            : `Call ${resource.number} — ${resource.labelEn}`
        }
        className="inline-flex min-h-[44px] items-center justify-center rounded-full bg-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-white"
      >
        {isAr ? (
          <>
            اتصل بـ <span dir="ltr">{resource.number}</span>
          </>
        ) : (
          <>Call {resource.number}</>
        )}
      </a>
    </li>
  )
}

/**
 * Ordered, hours-aware crisis resource list rendered ENTIRELY client-side from the static array
 * (or an explicit `resources` prop). No network, no server round-trip — deterministic and
 * offline-capable, so the persistent "Get help now" affordance still yields dialable numbers when
 * the backend is slow or down. Shared by CrisisCard (pinned, role=alert wrapper) and CrisisHelpPanel.
 * Shows the top `inlineCount` (lead-logic) inline; the rest sit behind a "More options" expander.
 * The 999 + 24/7 anchors are guaranteed inline by `leadingResources`, never hidden by the expander.
 */
export function CrisisResourceList({
  resources = CRISIS_RESOURCES,
  inlineCount = 3,
}: {
  resources?: readonly CrisisResource[]
  inlineCount?: number
}) {
  const locale = useLocaleStore((s) => s.locale)
  const isAr = locale === 'ar'
  const [expanded, setExpanded] = useState(false)

  const ordered = selectCrisisResources({ resources })
  const lead = leadingResources(ordered, inlineCount)
  const more = ordered.filter((r) => !lead.includes(r))
  const shown = expanded ? [...lead, ...more] : lead

  return (
    <div className="flex flex-col gap-2">
      <ol className="flex flex-col gap-2">
        {shown.map((r) => (
          <CrisisResourceRow key={`${r.scope}-${r.tel}`} resource={r} isAr={isAr} />
        ))}
      </ol>
      {more.length > 0 && !expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="min-h-[44px] self-start text-sm font-medium text-[var(--color-crisis)] underline"
        >
          {isAr ? `خيارات أخرى (${more.length})` : `More options (${more.length})`}
        </button>
      )}
    </div>
  )
}
