import { Card } from '@cdai/ui'
import type { SessionInsight } from '@cdai/types'

export function InsightsList({ insights }: { insights: SessionInsight[] }) {
  return (
    <div className="flex flex-col gap-3">
      {insights.map((insight) => (
        <Card key={insight.id} className="flex flex-col gap-1">
          <span className="text-xs font-medium text-[var(--color-primary)]">{insight.topicTag}</span>
          <p className="text-sm text-[var(--color-text-primary)]">{insight.content}</p>
        </Card>
      ))}
    </div>
  )
}
