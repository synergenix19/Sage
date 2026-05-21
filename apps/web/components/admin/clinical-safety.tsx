import { MetricCard } from './metric-card'
import { FlagBarChart } from './charts'
import type { ClinicalSafetyData } from '@/lib/admin-queries'

export function ClinicalSafetyPanel({ data }: { data: ClinicalSafetyData }) {
  return (
    <div className="space-y-4">
      {data.crisisThisWeek === 0 && (
        <div className="flex items-center gap-2.5 rounded-2xl border border-[var(--color-primary)] bg-[var(--color-surface-tinted)] px-4 py-3">
          <div className="h-2 w-2 flex-shrink-0 rounded-full bg-[var(--color-primary)]" />
          <p className="text-sm font-medium text-[var(--color-primary)]">No crisis events this week</p>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="Crisis Events (7d)"
          value={data.crisisThisWeek}
          subtext="Messages flagged as crisis"
          variant={data.crisisThisWeek > 0 ? 'alert' : 'ok'}
        />
        <MetricCard
          label="Clinical Escalations (7d)"
          value={data.escalationsThisWeek}
          subtext="Turns with clinical flags"
          variant={data.escalationsThisWeek > 0 ? 'alert' : 'default'}
        />
      </div>
      <FlagBarChart data={data.flagDistribution} />
    </div>
  )
}
