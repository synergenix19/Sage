'use client'
import { useState, useCallback } from 'react'
import { cn } from '@cdai/ui'
import { MetricCard } from './metric-card'
import { MoodTrendChart, TopTopicsChart, DistrictStressChart } from './charts'
import { AlertsPanel } from './alerts-panel'
import { SystemPerformancePanel } from './system-performance'
import { ClinicalSafetyPanel } from './clinical-safety'
import { ResponseQualityPanel } from './response-quality'
import { ConversationIntelligencePanel } from './conversation-intelligence'
import { getAdminDemoData } from '@/lib/admin-seed'
import type { AdminData } from '@/lib/admin-queries'
import { SchemaConformancePanel } from './schema-conformance-panel'
import type { ConformanceReport } from './schema-conformance-panel'

interface Props {
  data: AdminData
  conformance: ConformanceReport | null
}

export function AdminDashboard({ data, conformance }: Props) {
  const [highlightSection, setHighlightSection] = useState<string | null>(null)
  const demo = getAdminDemoData()

  const handleAlertClick = useCallback((targetSection: string) => {
    setHighlightSection(targetSection)
    setTimeout(() => {
      document.getElementById(targetSection)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
    setTimeout(() => setHighlightSection(null), 4000)
  }, [])

  function sectionClass(id: string) {
    if (highlightSection === null) return ''
    return highlightSection === id ? '' : 'opacity-20 transition-opacity duration-300'
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">Admin Dashboard</h1>
        <p className="text-xs text-[var(--color-text-secondary)]">Live data, last 7 days unless noted</p>
      </div>

      {data.clinicalSafety.crisisThisWeek > 0 && (
        <div className="rounded-2xl border border-[var(--color-crisis)] bg-[var(--color-crisis)]/10 px-5 py-4">
          <p className="text-sm font-semibold text-[var(--color-crisis)]">
            {data.clinicalSafety.crisisThisWeek} crisis event{data.clinicalSafety.crisisThisWeek !== 1 ? 's' : ''} this week
          </p>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            Review the Clinical Safety section below for details.
          </p>
        </div>
      )}

      <section id="clinical-safety" className={sectionClass('clinical-safety')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">Clinical Safety</h2>
        <ClinicalSafetyPanel data={data.clinicalSafety} />
      </section>

      <section id="system-performance" className={sectionClass('system-performance')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">System Performance</h2>
        <SystemPerformancePanel overview={data.overview} data={data.systemPerformance} />
      </section>

      <section id="response-quality" className={sectionClass('response-quality')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">Response Quality</h2>
        <ResponseQualityPanel data={data.responseQuality} />
      </section>

      <section id="intelligence" className={sectionClass('intelligence')}>
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">Conversation Intelligence</h2>
        <ConversationIntelligencePanel data={data.intelligence} />
      </section>

      <section id="population">
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">
          Population Wellness
          <span className="ml-2 text-xs font-normal text-[var(--color-text-secondary)]">(demo data, location signals pending)</span>
        </h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-4">
          <MetricCard label="Avg Mood Score" value={demo.avgMoodScore} subtext="Out of 5.0 this week (demo)" />
          <MetricCard label="Crisis Alerts" value={demo.crisisAlertsThisWeek} subtext="This week (demo)" />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 mb-4">
          <MoodTrendChart data={demo.moodTrend} />
          <TopTopicsChart data={demo.topTopics} />
        </div>
        <DistrictStressChart data={demo.districtStress} />
        <div className="mt-4">
          <AlertsPanel alerts={demo.recentAlerts} onAlertClick={handleAlertClick} />
        </div>
      </section>

      <section id="schema-conformance">
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">
          Schema Conformance
          <span className="ml-2 text-xs font-normal text-[var(--color-text-secondary)]">
            which clinician-authored fields are enforced at runtime
          </span>
        </h2>
        <SchemaConformancePanel report={conformance} />
      </section>
    </div>
  )
}
