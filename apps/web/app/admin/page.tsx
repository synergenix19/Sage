import { MetricCard } from '@/components/admin/metric-card'
import { MoodTrendChart, TopTopicsChart, DistrictStressChart } from '@/components/admin/charts'
import { AlertsPanel } from '@/components/admin/alerts-panel'
import { getAdminDemoData } from '@/lib/admin-seed'

export default function AdminPage() {
  // POST-PILOT: Replace with real Supabase query
  const data = getAdminDemoData()

  return (
    <div className="space-y-6">
      {/* Header with disabled pilot controls */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Admin Dashboard</h1>
        <div className="flex items-center gap-2">
          <select
            disabled
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] opacity-50 cursor-not-allowed"
          >
            <option>Last 30 days</option>
          </select>
          <button
            disabled
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] opacity-50 cursor-not-allowed"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Metric cards — 2 cols on mobile, 4 on desktop */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Total Users"    value={data.totalUsers}           subtext="All registered accounts" />
        <MetricCard label="Active Today"   value={data.activeToday}          subtext="Sessions in last 24 h" />
        <MetricCard label="Avg Mood Score" value={data.avgMoodScore}         subtext="Out of 5.0 this week" />
        <MetricCard label="Crisis Alerts"  value={data.crisisAlertsThisWeek} subtext="This week" />
      </div>

      {/* Trend + topics charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MoodTrendChart data={data.moodTrend} />
        <TopTopicsChart data={data.topTopics} />
      </div>

      {/* District stress index — full width */}
      <div className="grid grid-cols-1 gap-4">
        <DistrictStressChart data={data.districtStress} />
      </div>

      {/* Alerts panel */}
      <AlertsPanel alerts={data.recentAlerts} />
    </div>
  )
}
