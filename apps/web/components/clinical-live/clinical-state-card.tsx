'use client'

import type { AuditRow } from '@/lib/types/session-audit'

const CRISIS_COLORS: Record<string, string> = {
  none:       'bg-green-500',
  monitoring: 'bg-amber-500',
  active:     'bg-red-500',
  resolved:   'bg-slate-500',
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-slate-400 w-20 flex-shrink-0">{label}</span>
      <span className="text-slate-100 font-mono">{value ?? '—'}</span>
    </div>
  )
}

function MeterBar({ value, max = 10 }: { value: number | null; max?: number }) {
  const pct = value != null ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full bg-teal-400 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-300 font-mono">{value ?? '—'}/10</span>
    </div>
  )
}

type Props = { row: AuditRow }

export function ClinicalStateCard({ row }: Props) {
  const crisisColor = CRISIS_COLORS[row.crisis_state ?? 'none'] ?? 'bg-slate-500'
  const hasKnowledge = Boolean(row.knowledge_source)

  return (
    <div className={`grid gap-4 ${hasKnowledge ? 'grid-cols-3' : 'grid-cols-2'}`}>
      {/* Left column — mental state */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Clinical State</p>
        <Field label="Intent" value={row.primary_intent} />
        <div className="flex gap-2 text-xs items-center">
          <span className="text-slate-400 w-20 flex-shrink-0">Crisis</span>
          <span
            data-crisis={row.crisis_state ?? 'none'}
            className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${crisisColor}`}
          />
          <span className="text-slate-100 font-mono">{row.crisis_state ?? 'none'}</span>
        </div>
        {row.crisis_flags && row.crisis_flags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {row.crisis_flags.map(f => (
              <span key={f} className="text-[10px] bg-red-900 text-red-200 px-1.5 py-0.5 rounded">{f}</span>
            ))}
          </div>
        )}
        <div className="flex gap-2 text-xs items-center">
          <span className="text-slate-400 w-20 flex-shrink-0">Engage</span>
          <MeterBar value={row.engagement} />
        </div>
        <div className="flex gap-2 text-xs items-center">
          <span className="text-slate-400 w-20 flex-shrink-0">Intensity</span>
          <MeterBar value={row.emotional_intensity} />
        </div>
        {row.clinical_flags && row.clinical_flags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {row.clinical_flags.map(f => (
              <span key={f} className="text-[10px] bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">{f}</span>
            ))}
          </div>
        )}
        {(!row.clinical_flags || row.clinical_flags.length === 0) && (
          <Field label="Flags" value="—" />
        )}
      </div>

      {/* Right column — turn detail */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Turn Detail</p>
        <Field label="Skill" value={row.active_skill_id} />
        <Field label="Step" value={row.active_step_id} />
        <Field label="Match" value={
          row.skill_match_method
            ? `${row.skill_match_method}${row.intent_confidence != null ? ` (${row.intent_confidence.toFixed(2)})` : ''}`
            : null
        } />
        <Field label="Gate" value={null} />
        <Field label="Model" value={row.model_version} />
        <Field label="Latency" value={row.latency_ms != null ? `${row.latency_ms}ms` : null} />
      </div>

      {/* Conditional knowledge column */}
      {hasKnowledge && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Knowledge</p>
          <Field label="Source" value={row.knowledge_source} />
          <div className="flex gap-2 text-xs">
            <span className="text-slate-400 w-20 flex-shrink-0">Passages</span>
            <div className="flex flex-col gap-0.5">
              {row.knowledge_passage_ids?.length
                ? row.knowledge_passage_ids.map(p => (
                    <span key={p} className="text-teal-300 font-mono">{p}</span>
                  ))
                : <span className="text-slate-100 font-mono">—</span>
              }
            </div>
          </div>
          <Field label="Abstain" value={row.knowledge_abstain != null ? String(row.knowledge_abstain) : null} />
        </div>
      )}
    </div>
  )
}
