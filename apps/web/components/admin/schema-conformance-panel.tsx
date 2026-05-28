import { MetricCard } from './metric-card'

export interface FieldInfo {
  status: 'USED' | 'STORED_ONLY' | 'PARTIAL'
  injected_by: string | null
  note: string
}

export interface ConformanceReport {
  summary: {
    used: number
    partial: number
    stored_only: number
    total: number
  }
  fields: Record<string, FieldInfo>
}

interface Props {
  report: ConformanceReport | null
}

const STATUS_LABEL: Record<string, string> = {
  USED: 'USED',
  PARTIAL: 'PARTIAL',
  STORED_ONLY: 'STORED ONLY',
}

const STATUS_CLASS: Record<string, string> = {
  USED: 'bg-emerald-100 text-emerald-800',
  PARTIAL: 'bg-amber-100 text-amber-800',
  STORED_ONLY: 'bg-red-100 text-red-800',
}

export function SchemaConformancePanel({ report }: Props) {
  if (!report) {
    return (
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-5 py-4">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Schema conformance data unavailable — sage-poc health endpoint did not respond.
        </p>
      </div>
    )
  }

  const { summary, fields } = report

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Fields Used"
          value={summary.used}
          subtext={`of ${summary.total} schema fields`}
        />
        <MetricCard
          label="Partial"
          value={summary.partial}
          subtext="LLM criteria (4/20 skills only)"
        />
        <MetricCard
          label="Stored Only"
          value={summary.stored_only}
          subtext="Not evaluated at runtime"
        />
        <MetricCard
          label="Total Fields"
          value={summary.total}
          subtext="Across Skill + SkillStep"
        />
      </div>

      <div className="rounded-2xl border border-[var(--color-border)] overflow-x-auto">
        <table className="w-full text-xs min-w-[600px]">
          <thead>
            <tr className="bg-[var(--color-bg-secondary)]">
              <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-secondary)] w-52">
                Schema Field
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-secondary)] w-28">
                Status
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-secondary)]">
                Runtime Note
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {Object.entries(fields).map(([field, info]) => (
              <tr key={field} className="bg-[var(--color-bg-primary)] hover:bg-[var(--color-bg-secondary)] transition-colors">
                <td className="px-4 py-2.5 font-mono text-[var(--color-text-primary)]">
                  {field}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
                      STATUS_CLASS[info.status] ?? 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {STATUS_LABEL[info.status] ?? info.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-[var(--color-text-secondary)] leading-relaxed">
                  {info.note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-[var(--color-text-secondary)]">
        STORED ONLY fields are parsed and validated by Pydantic but not evaluated at runtime.
        Clinicians who author these fields should be informed their content is not yet enforced.
      </p>
    </div>
  )
}
