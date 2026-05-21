import { MetricCard } from './metric-card'
import { SkillUsageChart } from './charts'
import type { ConversationIntelligenceData } from '@/lib/admin-queries'

export function ConversationIntelligencePanel({ data }: { data: ConversationIntelligenceData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Semantic Match Rate"
          value={data.semanticMatchRate !== null ? `${Math.round(data.semanticMatchRate * 100)}%` : 'No data'}
          subtext="Turns matched via semantic skill search"
        />
        <MetricCard
          label="Avg Input Tokens"
          value={data.avgTokenUsageInput ?? 'No data'}
          subtext="Per AI turn (7 days)"
        />
        <MetricCard
          label="Avg Output Tokens"
          value={data.avgTokenUsageOutput ?? 'No data'}
          subtext="Per AI turn (7 days)"
        />
        <MetricCard
          label="Skills Active"
          value={data.skillUsage.length}
          subtext="Distinct skills used this week"
        />
      </div>
      <SkillUsageChart data={data.skillUsage} />
    </div>
  )
}
