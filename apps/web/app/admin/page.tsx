'use client'
import { useState, useCallback } from 'react'
import { MetricCard } from '@/components/admin/metric-card'
import { MoodTrendChart, TopTopicsChart, DistrictStressChart } from '@/components/admin/charts'
import { AlertsPanel } from '@/components/admin/alerts-panel'
import { getAdminDemoData } from '@/lib/admin-seed'
import { cn } from '@cdai/ui'

export default function AdminPage() {
  const data = getAdminDemoData()
  const [highlightSection, setHighlightSection] = useState<string | null>(null)

  const handleAlertClick = useCallback((targetSection: string) => {
    setHighlightSection(targetSection)
    setTimeout(() => {
      const el = document.getElementById(targetSection)
      el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
    setTimeout(() => setHighlightSection(null), 4000)
  }, [])

  function sectionClass(id: string) {
    if (highlightSection === null) return ''
    return highlightSection === id ? '' : 'opacity-20 transition-opacity duration-300'
  }

  return (
    <div className="space-y-6">
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
            title="Export available in full release"
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] opacity-50 cursor-not-allowed"
          >
            Export CSV
          </button>
        </div>
      </div>

      <div id="overview" className={cn('grid grid-cols-2 gap-4 lg:grid-cols-4', sectionClass('overview'))}>
        <MetricCard label="Total Users"    value={data.totalUsers}           subtext="All registered accounts" />
        <MetricCard label="Active Today"   value={data.activeToday}          subtext="Sessions in last 24 h" />
        <MetricCard label="Avg Mood Score" value={data.avgMoodScore}         subtext="Out of 5.0 this week" />
        <MetricCard label="Crisis Alerts"  value={data.crisisAlertsThisWeek} subtext="This week" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div id="mood-trend" className={sectionClass('mood-trend')}>
          <MoodTrendChart data={data.moodTrend} />
        </div>
        <div id="top-topics" className={sectionClass('top-topics')}>
          <TopTopicsChart data={data.topTopics} />
        </div>
      </div>

      <div id="district-stress" className={cn('grid grid-cols-1 gap-4', sectionClass('district-stress'))}>
        <DistrictStressChart data={data.districtStress} />
      </div>

      <div id="alerts" className={sectionClass('alerts')}>
        <AlertsPanel alerts={data.recentAlerts} onAlertClick={handleAlertClick} />
      </div>
    </div>
  )
}
