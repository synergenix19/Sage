'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSessionAudit } from '@/components/clinical-live/use-session-audit'
import { NodePathVisualizer } from '@/components/clinical-live/node-path-visualizer'
import { ClinicalStateCard } from '@/components/clinical-live/clinical-state-card'
import { AuditLog } from '@/components/clinical-live/audit-log'

const STATUS_DOT: Record<string, string> = {
  live:         'bg-teal-400 animate-pulse',
  locked:       'bg-blue-400',
  reconnecting: 'bg-amber-400 animate-pulse',
  waiting:      'bg-slate-500',
}

const STATUS_LABEL: Record<string, string> = {
  live:         'LIVE',
  locked:       'LOCKED',
  reconnecting: 'RECONNECTING',
  waiting:      'WAITING',
}

function LivePanel() {
  const params = useSearchParams()
  const lockedSessionId = params.get('session')
  const { rows, latestRow, activeSessionId, status } = useSessionAudit(lockedSessionId)

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700 bg-slate-900 flex-shrink-0">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[status]}`} />
        <span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
          {STATUS_LABEL[status]}
        </span>
        <span className="text-sm font-semibold text-slate-100">SAGE Clinical Intelligence</span>
        {activeSessionId && (
          <span className="ml-auto text-xs text-slate-500 font-mono truncate max-w-[20ch]">
            {activeSessionId}
          </span>
        )}
      </div>

      {/* Node path */}
      <div className="px-4 py-3 border-b border-slate-700 flex-shrink-0">
        <NodePathVisualizer
          firedNodes={latestRow?.node_path ?? []}
          turnNumber={latestRow?.turn_number ?? 0}
        />
      </div>

      {/* Clinical state card */}
      <div className="px-4 py-3 border-b border-slate-700 flex-shrink-0">
        {latestRow ? (
          <ClinicalStateCard row={latestRow} />
        ) : (
          <p className="text-xs text-slate-500">
            Waiting for session — start a conversation in the chat window.
          </p>
        )}
      </div>

      {/* Audit log */}
      <div className="px-4 py-3 flex-1 overflow-hidden">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Audit Log</p>
        <AuditLog rows={rows} />
      </div>
    </div>
  )
}

export default function LivePage() {
  return (
    <Suspense fallback={<div className="p-4 text-slate-500 text-sm">Loading...</div>}>
      <LivePanel />
    </Suspense>
  )
}
