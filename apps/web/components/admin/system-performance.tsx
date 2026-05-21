import { MetricCard } from './metric-card'
import { LatencyLineChart, IntentBarChart } from './charts'
import type { OverviewMetrics, SystemPerformanceData } from '@/lib/admin-queries'

interface Props {
  overview: OverviewMetrics
  data: SystemPerformanceData
}

export function SystemPerformancePanel({ overview, data }: Props) {
  const avgLatency = data.latencyByDay.length
    ? Math.round(data.latencyByDay.reduce((s, d) => s + d.avgMs, 0) / data.latencyByDay.length)
    : null
  const totalTurns = data.latencyByDay.reduce((s, d) => s + d.turnCount, 0)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <MetricCard label="Total Users" value={overview.totalUsers} subtext="All registered accounts" />
        <MetricCard label="Active Today" value={overview.activeToday} subtext="Distinct users with sessions today" />
        <MetricCard
          label="Avg Latency (14d)"
          value={avgLatency !== null ? `${avgLatency}ms` : 'No data'}
          subtext={`${totalTurns} AI turns recorded`}
        />
      </div>
      <LatencyLineChart data={data.latencyByDay} />
      <IntentBarChart data={data.intentDistribution} />
    </div>
  )
}
