'use client'

import { useSearchParams } from 'next/navigation'
import { useSessionAudit } from './use-session-audit'
import { NodePathVisualizer } from './node-path-visualizer'
import { ClinicalStateCard } from './clinical-state-card'
import { AuditLog } from './audit-log'

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

export function LivePanel() {
  const params = useSearchParams()
  const lockedSessionId = params.get('session')
  const { rows, latestRow, activeSessionId, status } = useSessionAudit(lockedSessionId)

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <h1 className="sr-only">SAGE Clinical Intelligence — Live Monitor</h1>

      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3 border-b flex-shrink-0"
        style={{
          background: 'var(--color-clinical-surface)',
          borderColor: 'var(--color-clinical-border)',
        }}
      >
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[status]}`} />
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'var(--color-clinical-text)', opacity: 0.6 }}>
          {STATUS_LABEL[status]}
        </span>
        <span className="text-sm font-semibold" style={{ color: 'var(--color-clinical-text)' }}>
          SAGE Clinical Intelligence
        </span>
        {activeSessionId && (
          <span className="ml-auto text-xs font-mono truncate max-w-[20ch]" style={{ color: 'var(--color-clinical-text)', opacity: 0.4 }}>
            {activeSessionId}
          </span>
        )}
      </div>

      {/* Node path */}
      <div className="px-4 py-3 border-b flex-shrink-0" style={{ borderColor: 'var(--color-clinical-border)' }}>
        <NodePathVisualizer
          firedNodes={latestRow?.node_path ?? []}
          turnNumber={latestRow?.turn_number ?? 0}
        />
      </div>

      {/* Clinical state card */}
      <div className="px-4 py-3 border-b flex-shrink-0" style={{ borderColor: 'var(--color-clinical-border)' }}>
        {latestRow ? (
          <ClinicalStateCard row={latestRow} />
        ) : (
          <p className="text-xs" style={{ color: 'var(--color-clinical-text)', opacity: 0.5 }}>
            Waiting for session — start a conversation in the chat window.
          </p>
        )}
      </div>

      {/* Audit log */}
      <div className="px-4 py-3 flex-1 overflow-hidden">
        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-clinical-text)', opacity: 0.6 }}>
          Audit Log
        </p>
        <AuditLog rows={rows} />
      </div>
    </div>
  )
}
