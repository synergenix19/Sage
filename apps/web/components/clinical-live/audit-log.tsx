'use client'

import type { AuditRow } from '@/lib/types/session-audit'

const COLS = ['Turn', 'Intent', 'Skill', 'Step', 'Crisis', 'Eng', 'Int', 'ms']

type Props = { rows: AuditRow[] }

export function AuditLog({ rows }: Props) {
  if (rows.length === 0) {
    return (
      <p className="text-xs text-slate-500 text-center py-4">
        Waiting for turns...
      </p>
    )
  }

  const sorted = [...rows].sort((a, b) => b.turn_number - a.turn_number)

  return (
    <div className="overflow-auto max-h-48">
      <table className="min-w-max text-xs font-mono border-collapse">
        <thead>
          <tr>
            {COLS.map(c => (
              <th key={c} className="text-left text-slate-500 pb-1 pr-3 font-normal">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(row => (
            <tr
              key={row.id}
              data-turn={String(row.turn_number)}
              className="border-t border-slate-800 hover:bg-slate-800/40"
            >
              <td className="py-1.5 pr-3 text-slate-300">T{row.turn_number}</td>
              <td className="py-1.5 pr-3 text-slate-300">{row.primary_intent ?? '—'}</td>
              <td className="py-1.5 pr-3 text-teal-400">{row.active_skill_id ?? '—'}</td>
              <td className="py-1.5 pr-3 text-slate-400">{row.active_step_id ?? '—'}</td>
              <td className="py-1.5 pr-3 text-slate-300">{row.crisis_state ?? '—'}</td>
              <td className="py-1.5 pr-3 text-slate-400">{row.engagement ?? '—'}</td>
              <td className="py-1.5 pr-3 text-slate-400">{row.emotional_intensity ?? '—'}</td>
              <td className="py-1.5 text-slate-500">{row.latency_ms != null ? `${row.latency_ms}` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
