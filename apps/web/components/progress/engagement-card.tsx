import { Card } from '@cdai/ui'
import type { EngagementStats } from '@/lib/progress-queries'

export function EngagementCard({ stats }: { stats: EngagementStats }) {
  return (
    <Card className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-2xl font-semibold">{stats.sessionCount}</p>
        <p className="text-xs text-[var(--color-text-secondary)]">conversations</p>
      </div>
      <div>
        <p className="text-2xl font-semibold">{stats.skillsUsedCount}</p>
        <p className="text-xs text-[var(--color-text-secondary)]">
          {stats.skillsUsedCount === 1 ? 'technique explored' : 'techniques explored'}
        </p>
      </div>
    </Card>
  )
}
